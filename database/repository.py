from __future__ import annotations

import sqlite3
import sys
import threading
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generator, List, Optional

from core.constants import AppCategory
from core.logger import logger
from database.models import AppInfo, AppSession, EventLogEntry, DailyStat, Setting, WebsiteSession
from database.schema import ALL_DDL, DEFAULT_SETTINGS, MIGRATIONS

# Upper bound for SQLite's memory-mapped I/O window (256 MB). The window is
# capped by the on-disk size of the database and disabled on 32-bit builds so
# a large mapping can never exhaust the process address space.
_MMAP_MAX_BYTES = 268435456
_MMAP_MIN_BYTES = 33554432


def _get_db_path() -> Path:
    app_data = Path.home() / "AppData" / "Local" / "DigitalWellbeing"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data / "digital_wellbeing.db"


def _mmap_size_for(db_path: Path) -> int:
    """Return a safe mmap window: min(256 MB, max(32 MB, database size))."""
    if sys.maxsize <= 2**32:
        # 32-bit interpreter: large mappings are not worth the address-space risk.
        return 0
    try:
        db_bytes = db_path.stat().st_size
    except OSError:
        db_bytes = 0
    return max(_MMAP_MIN_BYTES, min(_MMAP_MAX_BYTES, db_bytes))


class Repository:
    _instance: Optional["Repository"] = None
    _class_lock = threading.Lock()
    _db_path_override: Optional[Path] = None

    @classmethod
    def set_db_path_override(cls, path: Optional[Path]) -> None:
        with cls._class_lock:
            cls._db_path_override = path
            cls._instance = None

    def __new__(cls) -> "Repository":
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._db_path = Repository._db_path_override or _get_db_path()
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._initialize_schema()
        self._run_migrations()
        self._seed_default_settings()
        self._cleanup_test_data()
        self._close_orphaned_sessions()
        self._initialized = True
        logger.info("Repository initialized at %s", self._db_path)

    # ─── Connection management ─────────────────────────────────────────────────

    def _connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=10.0,
            )
            conn.row_factory = sqlite3.Row
            # WAL keeps readers non-blocking while the tracker commits sessions.
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            # Wait rather than immediately raising "database is locked" when a
            # UI analytics query overlaps a tracker write.
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA cache_size=-8000;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA wal_autocheckpoint=1000;")
            mmap_bytes = _mmap_size_for(self._db_path)
            if mmap_bytes:
                conn.execute(f"PRAGMA mmap_size={mmap_bytes};")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self._connection()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except sqlite3.OperationalError as exc:
            conn.rollback()
            logger.error("DB operational error: %s", exc)
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # ─── Schema ───────────────────────────────────────────────────────────────

    def _initialize_schema(self) -> None:
        with self._write_lock:
            conn = self._connection()
            cur = conn.cursor()
            try:
                for ddl in ALL_DDL:
                    cur.execute(ddl)
                conn.commit()
            finally:
                cur.close()

    def _run_migrations(self) -> None:
        with self._write_lock:
            conn = self._connection()
            cur = conn.cursor()
            try:
                for column, table, sql in MIGRATIONS:
                    cur.execute(f"PRAGMA table_info({table})")
                    cols = [row["name"] for row in cur.fetchall()]
                    if column not in cols:
                        cur.execute(sql)
                        logger.info("Migration applied: ADD %s.%s", table, column)
                conn.commit()
            finally:
                cur.close()

    def _seed_default_settings(self) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                for key, value in DEFAULT_SETTINGS.items():
                    cur.execute(
                        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                        (key, value),
                    )

    def _close_orphaned_sessions(self) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE app_sessions
                    SET end_time = COALESCE(end_time, start_time),
                        duration_s = CASE
                            WHEN end_time IS NOT NULL AND start_time IS NOT NULL THEN
                                MAX(0.0, (JULIANDAY(end_time) - JULIANDAY(start_time)) * 86400.0)
                            ELSE 0.0
                        END,
                        was_closed = 1
                    WHERE end_time IS NULL OR was_closed = 0
                    """,
                )
                
                cur.execute(
                    """
                    UPDATE website_sessions
                    SET end_time = COALESCE(end_time, start_time),
                        duration_s = CASE
                            WHEN end_time IS NOT NULL AND start_time IS NOT NULL THEN
                                MAX(0.0, (JULIANDAY(end_time) - JULIANDAY(start_time)) * 86400.0)
                            ELSE 0.0
                        END,
                        was_closed = 1
                    WHERE end_time IS NULL OR was_closed = 0
                    """,
                )
                count = cur.rowcount
                if count:
                    logger.warning("Closed %d orphaned sessions from previous run", count)

    # ─── Website Sessions ────────────────────────────────────────────────────
    
    def insert_website_session(self, session: WebsiteSession) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO website_sessions
                        (domain, browser_process, start_time, end_time, duration_s, was_closed)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.domain,
                        session.browser_process,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else None,
                        session.duration_s,
                        int(session.was_closed),
                    ),
                )
                return cur.lastrowid or 0

    def update_website_session_end(
        self,
        session_id: int,
        end_time: datetime,
        duration_s: float,
        was_closed: bool = True,
    ) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE website_sessions
                    SET end_time=?, duration_s=?, was_closed=?
                    WHERE id=?
                    """,
                    (end_time.isoformat(), duration_s, int(was_closed), session_id),
                )
                
    def get_website_usage_today(self, domain: str) -> float:
        today = date.today()
        start = datetime.combine(today, datetime.min.time()).isoformat()
        end = datetime.combine(today, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s
                FROM website_sessions
                WHERE domain=? AND start_time >= ? AND start_time <= ?
                """,
                (domain, start, end),
            )
            row = cur.fetchone()
            return row["total_s"] or 0.0

    def get_top_websites_for_browser_today(self, browser_process: str) -> List[dict]:
        today = date.today()
        return self.get_top_websites_for_browser(browser_process, today, today)

    def get_top_websites_for_browser(
        self, browser_process: str, start_date: date, end_date: date, limit: int = 50
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT domain, SUM(duration_s) AS total_s, COUNT(*) AS session_count
                FROM website_sessions
                WHERE browser_process=? AND start_time >= ? AND start_time <= ? AND duration_s > 0
                GROUP BY domain
                ORDER BY total_s DESC
                LIMIT ?
                """,
                (browser_process, start, end, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_top_websites_for_range(
        self, start_date: date, end_date: date, browser_process: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            if browser_process and browser_process.lower() not in {"*", "all"}:
                cur.execute(
                    """
                    SELECT domain, SUM(duration_s) AS total_s, COUNT(*) AS session_count,
                           browser_process AS browsers
                    FROM website_sessions
                    WHERE browser_process=? AND start_time >= ? AND start_time <= ? AND duration_s > 0
                    GROUP BY domain
                    ORDER BY total_s DESC
                    LIMIT ?
                    """,
                    (browser_process, start, end, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT domain, SUM(duration_s) AS total_s, COUNT(*) AS session_count,
                           GROUP_CONCAT(DISTINCT browser_process) AS browsers
                    FROM website_sessions
                    WHERE start_time >= ? AND start_time <= ? AND duration_s > 0
                    GROUP BY domain
                    ORDER BY total_s DESC
                    LIMIT ?
                    """,
                    (start, end, limit),
                )
            rows = [dict(row) for row in cur.fetchall()]
            for r in rows:
                b_str = r.get("browsers") or ""
                r["browser_list"] = [b.strip() for b in b_str.split(",") if b.strip()]
                r["browser_process"] = r["browser_list"][0] if r["browser_list"] else ""
            return rows

    def get_distinct_browsers_for_range(self, start_date: date, end_date: date) -> List[str]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT browser_process
                FROM website_sessions
                WHERE start_time >= ? AND start_time <= ? AND duration_s > 0
                ORDER BY browser_process
                """,
                (start, end),
            )
            return [row["browser_process"] for row in cur.fetchall() if row["browser_process"]]

    def get_total_website_time_for_range(
        self, start_date: date, end_date: date, browser_process: Optional[str] = None
    ) -> float:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            if browser_process:
                cur.execute(
                    """
                    SELECT SUM(duration_s) AS total_s
                    FROM website_sessions
                    WHERE browser_process=? AND start_time >= ? AND start_time <= ?
                    """,
                    (browser_process, start, end),
                )
            else:
                cur.execute(
                    """
                    SELECT SUM(duration_s) AS total_s
                    FROM website_sessions
                    WHERE start_time >= ? AND start_time <= ?
                    """,
                    (start, end),
                )
            row = cur.fetchone()
            return row["total_s"] or 0.0

    # ─── Sessions ────────────────────────────────────────────────────────────

    def insert_session(self, session: AppSession) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_sessions
                        (process_name, exe_path, window_title, start_time,
                         end_time, duration_s, category, is_idle, was_closed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.process_name,
                        session.exe_path,
                        session.window_title,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else None,
                        session.duration_s,
                        session.category.value,
                        int(session.is_idle),
                        int(session.was_closed),
                    ),
                )
                return cur.lastrowid or 0

    def update_session_end(
        self,
        session_id: int,
        end_time: datetime,
        duration_s: float,
        was_closed: bool = True,
    ) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE app_sessions
                    SET end_time=?, duration_s=?, was_closed=?
                    WHERE id=?
                    """,
                    (end_time.isoformat(), duration_s, int(was_closed), session_id),
                )

    def update_session_title(self, session_id: int, new_title: str) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE app_sessions SET window_title=? WHERE id=?",
                    (new_title[:512], session_id),
                )

    def delete_session(self, session_id: int) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions WHERE id=?", (session_id,))

    def clear_all_sessions(self) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions")
                return cur.rowcount

    def cleanup_old_sessions(self, retention_days: int) -> int:
        if retention_days < 0:
            return 0
            
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_sessions WHERE start_time < ?", (cutoff,))
                deleted = cur.rowcount
                cur.execute("DELETE FROM event_log WHERE timestamp < ?", (cutoff,))
                deleted += cur.rowcount
                return deleted

    def backup_database(self, dest_path: Path) -> Path:
        with self._write_lock:
            conn = self._connection()
            dest_conn = sqlite3.connect(str(dest_path))
            try:
                conn.backup(dest_conn)
            finally:
                dest_conn.close()
            return dest_path

    def restore_database(self, src_path: Path) -> None:
        with self._write_lock:
            src_conn = sqlite3.connect(str(src_path))
            conn = self._connection()
            try:
                src_conn.backup(conn)
            finally:
                src_conn.close()

    def get_open_sessions(self) -> List[AppSession]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM app_sessions WHERE end_time IS NULL ORDER BY start_time"
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_sessions_for_date(self, target_date: date) -> List[AppSession]:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_sessions_for_range(
        self, start_date: date, end_date: date
    ) -> List[AppSession]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_sessions_between(
        self, start: datetime, end: datetime
    ) -> List[AppSession]:
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time < ?
                  AND is_idle = 0 AND duration_s > 0
                ORDER BY start_time
                """,
                (start.isoformat(), end.isoformat()),
            )
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_top_apps_for_range(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT process_name, category,
                       SUM(duration_s) AS total_s,
                       COUNT(*) AS sessions
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY process_name
                ORDER BY total_s DESC
                LIMIT ?
                """,
                (start, end, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_category_breakdown_for_range(
        self, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT LOWER(category) AS raw_category, SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY LOWER(category)
                ORDER BY total_s DESC
                """,
                (start, end),
            )
            
            # Format back to title case to maintain expected format
            return [{"category": row["raw_category"].title() if row["raw_category"] else "Other", "total_s": row["total_s"]} for row in cur.fetchall()]

    def get_hourly_breakdown_for_date(self, target_date: date) -> List[dict]:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%H', start_time) AS hour,
                       SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle = 0
                  AND duration_s > 0
                GROUP BY hour
                ORDER BY hour
                """,
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_daily_totals_for_range(
        self, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day,
                       SUM(CASE WHEN is_idle=0 THEN duration_s ELSE 0 END) AS active_s,
                       SUM(CASE WHEN is_idle=1 THEN duration_s ELSE 0 END) AS idle_s
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND duration_s > 0
                GROUP BY day
                ORDER BY day
                """,
                (start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def search_sessions(
        self,
        query: str,
        category: Optional[AppCategory],
        start_date: Optional[date],
        end_date: Optional[date],
        limit: int = 200,
    ) -> List[AppSession]:
        conditions = ["duration_s > 0"]
        params: list = []

        if query:
            conditions.append("(process_name LIKE ? OR window_title LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("category = ?")
            params.append(category.value)
        if start_date:
            conditions.append("start_time >= ?")
            params.append(datetime.combine(start_date, datetime.min.time()).isoformat())
        if end_date:
            conditions.append("start_time <= ?")
            params.append(datetime.combine(end_date, datetime.max.time()).isoformat())

        sql = (
            f"SELECT * FROM app_sessions WHERE {' AND '.join(conditions)} "
            f"ORDER BY start_time DESC LIMIT ?"
        )
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return [self._row_to_session(row) for row in cur.fetchall()]

    def get_longest_session_for_range(
        self, start_date: date, end_date: date
    ) -> Optional[AppSession]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT * FROM app_sessions
                WHERE start_time >= ? AND start_time <= ?
                  AND is_idle=0 AND duration_s > 0
                ORDER BY duration_s DESC LIMIT 1
                """,
                (start, end),
            )
            row = cur.fetchone()
            return self._row_to_session(row) if row else None

    def get_total_screen_time_for_range(
        self, start_date: date, end_date: date
    ) -> float:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(duration_s), 0) AS total
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (start, end),
            )
            row = cur.fetchone()
            return float(row["total"]) if row else 0.0

    def get_app_usage_for_range(
        self, process_name: str, start_date: date, end_date: date
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day,
                       SUM(duration_s) AS total_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ?
                  AND is_idle=0 AND duration_s > 0
                GROUP BY day ORDER BY day
                """,
                (process_name, start, end),
            )
            return [dict(row) for row in cur.fetchall()]

    def export_sessions_csv_data(
        self, start_date: date, end_date: date
    ) -> List[tuple]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT process_name, exe_path, window_title, start_time, end_time,
                       duration_s, category, is_idle
                FROM app_sessions
                WHERE start_time >= ? AND start_time <= ? AND duration_s > 0
                ORDER BY start_time
                """,
                (start, end),
            )
            return cur.fetchall()

    # ─── App Info ─────────────────────────────────────────────────────────────

    def upsert_app_info(self, info: AppInfo) -> None:
        now = info.last_seen or datetime.now()
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO app_info
                        (process_name, display_name, category, exe_path, icon_path,
                         first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(process_name) DO UPDATE SET
                        display_name = excluded.display_name,
                        exe_path = COALESCE(NULLIF(excluded.exe_path,''), app_info.exe_path),
                        icon_path = COALESCE(excluded.icon_path, app_info.icon_path),
                        last_seen = excluded.last_seen
                    """,
                    (
                        info.process_name,
                        info.display_name,
                        info.category.value,
                        info.exe_path,
                        info.icon_path,
                        info.first_seen.isoformat(),
                        now.isoformat(),
                    ),
                )

    def get_app_info(self, process_name: str) -> Optional[AppInfo]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM app_info WHERE process_name=?", (process_name,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return self._row_to_app_info(row, cols)

    def update_app_category(self, process_name: str, category: AppCategory) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE app_info SET category=? WHERE process_name=?",
                    (category.value, process_name),
                )
                cur.execute(
                    "UPDATE app_sessions SET category=? WHERE process_name=?",
                    (category.value, process_name),
                )

    # ─── Event Log ────────────────────────────────────────────────────────────

    def log_event(self, event_type: str, detail: str = "") -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO event_log (timestamp, event_type, detail) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), event_type, detail),
                )

    def get_recent_events(self, limit: int = 100) -> List[EventLogEntry]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                EventLogEntry(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    event_type=row["event_type"],
                    detail=row["detail"],
                )
                for row in cur.fetchall()
            ]

    # ─── Settings ─────────────────────────────────────────────────────────────

    def get_setting(self, key: str) -> Optional[str]:
        with self._cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = cur.fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )

    def get_all_settings(self) -> dict[str, str]:
        with self._cursor() as cur:
            cur.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cur.fetchall()}

    # ─── Aggregation Methods for Digital Wellbeing Views ─────────────────────

    def get_aggregated_apps_for_range(
        self,
        start_date: date,
        end_date: date,
        query: str = "",
        category: Optional[AppCategory] = None,
        limit: int = 200,
    ) -> List[dict]:
        start = datetime.combine(start_date, datetime.min.time()).isoformat()
        end = datetime.combine(end_date, datetime.max.time()).isoformat()

        conditions = ["start_time >= ?", "start_time <= ?", "is_idle = 0", "duration_s > 0"]
        params: list[object] = [start, end]

        if query:
            conditions.append("(process_name LIKE ? OR window_title LIKE ?)")
            q = f"%{query}%"
            params.extend([q, q])

        if category:
            conditions.append("category = ?")
            params.append(category.value)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT process_name, category, exe_path,
                   SUM(duration_s) AS total_s,
                   COUNT(*) AS open_count,
                   MAX(duration_s) AS max_session_s,
                   AVG(duration_s) AS avg_session_s
            FROM app_sessions
            WHERE {where_clause}
            GROUP BY process_name
            ORDER BY total_s DESC
            LIMIT ?
        """
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append({
                    "process_name": r["process_name"],
                    "category": r["category"],
                    "exe_path": r["exe_path"] if "exe_path" in r.keys() else "",
                    "total_s": r["total_s"],
                    "open_count": r["open_count"],
                    "max_session_s": r["max_session_s"],
                    "avg_session_s": r["avg_session_s"],
                })
            return results

    def get_app_detail_stats(self, process_name: str) -> dict:
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time()).isoformat()
        today_end = datetime.combine(today, datetime.max.time()).isoformat()

        week_start_date = today - timedelta(days=today.weekday())
        week_start = datetime.combine(week_start_date, datetime.min.time()).isoformat()

        month_start_date = today.replace(day=1)
        month_start = datetime.combine(month_start_date, datetime.min.time()).isoformat()

        with self._cursor() as cur:
            # Today stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, today_start, today_end),
            )
            r_today = cur.fetchone()
            today_s = r_today["total_s"] or 0.0 if r_today else 0.0
            today_opens = r_today["open_count"] or 0 if r_today else 0

            # Week stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, week_start, today_end),
            )
            r_week = cur.fetchone()
            week_s = r_week["total_s"] or 0.0 if r_week else 0.0
            week_opens = r_week["open_count"] or 0 if r_week else 0

            # Month stats
            cur.execute(
                """
                SELECT SUM(duration_s) AS total_s, COUNT(*) AS open_count, MAX(duration_s) AS max_s, AVG(duration_s) AS avg_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                """,
                (process_name, month_start, today_end),
            )
            r_month = cur.fetchone()
            month_s = r_month["total_s"] or 0.0 if r_month else 0.0
            month_opens = r_month["open_count"] or 0 if r_month else 0
            max_session_s = r_month["max_s"] or 0.0 if r_month else 0.0
            avg_session_s = r_month["avg_s"] or 0.0 if r_month else 0.0

            # Past 7 days daily breakdown chart for this app
            start_7 = today - timedelta(days=6)
            s_7 = datetime.combine(start_7, datetime.min.time()).isoformat()
            cur.execute(
                """
                SELECT strftime('%Y-%m-%d', start_time) AS day, SUM(duration_s) AS daily_s
                FROM app_sessions
                WHERE process_name=? AND start_time >= ? AND start_time <= ? AND is_idle=0 AND duration_s > 0
                GROUP BY day
                """,
                (process_name, s_7, today_end),
            )
            daily_rows = {r["day"]: r["daily_s"] for r in cur.fetchall()}

            chart_data = []
            curr = start_7
            while curr <= today:
                k = curr.strftime("%Y-%m-%d")
                chart_data.append({"day": k, "duration_s": daily_rows.get(k, 0.0)})
                curr += timedelta(days=1)

            return {
                "process_name": process_name,
                "today_s": today_s,
                "today_opens": today_opens,
                "week_s": week_s,
                "week_opens": week_opens,
                "month_s": month_s,
                "month_opens": month_opens,
                "longest_session_s": max_session_s,
                "avg_session_s": avg_session_s,
                "daily_chart_data": chart_data,
            }

    # ─── Daily Stats & Snapshots ──────────────────────────────────────────────

    def upsert_daily_stat(self, stat: DailyStat) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO daily_stats
                        (date, total_screen_time_s, active_time_s, idle_time_s,
                         top_app, session_count, unlock_count, category_usage_json,
                         app_usage_json, timeline_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        total_screen_time_s = excluded.total_screen_time_s,
                        active_time_s = excluded.active_time_s,
                        idle_time_s = excluded.idle_time_s,
                        top_app = excluded.top_app,
                        session_count = excluded.session_count,
                        unlock_count = excluded.unlock_count,
                        category_usage_json = excluded.category_usage_json,
                        app_usage_json = excluded.app_usage_json,
                        timeline_json = excluded.timeline_json
                    """,
                    (
                        stat.date.isoformat(),
                        stat.total_screen_time_s,
                        stat.active_time_s,
                        stat.idle_time_s,
                        stat.top_app,
                        stat.session_count,
                        stat.unlock_count,
                        stat.category_usage_json,
                        stat.app_usage_json,
                        stat.timeline_json,
                    ),
                )

    def get_daily_stat(self, target_date: date) -> Optional[DailyStat]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM daily_stats WHERE date=?", (target_date.isoformat(),))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_daily_stat(row)

    def get_all_daily_stats(self, order_desc: bool = True) -> List[DailyStat]:
        with self._cursor() as cur:
            order = "DESC" if order_desc else "ASC"
            cur.execute(f"SELECT * FROM daily_stats ORDER BY date {order}")
            return [self._row_to_daily_stat(row) for row in cur.fetchall()]

    def get_unlock_count_for_date(self, target_date: date) -> int:
        start = datetime.combine(target_date, datetime.min.time()).isoformat()
        end = datetime.combine(target_date, datetime.max.time()).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) as unlocks
                FROM event_log
                WHERE event_type = 'unlock' AND timestamp >= ? AND timestamp <= ?
                """,
                (start, end),
            )
            row = cur.fetchone()
            return row["unlocks"] if row else 0

    # ─── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> AppSession:
        keys = row.keys()
        return AppSession(
            id=row["id"],
            process_name=row["process_name"],
            exe_path=row["exe_path"] if "exe_path" in keys else "",
            window_title=row["window_title"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            duration_s=row["duration_s"],
            category=AppCategory(row["category"]),
            is_idle=bool(row["is_idle"]),
            was_closed=bool(row["was_closed"]) if "was_closed" in keys else False,
        )

    @staticmethod
    def _row_to_app_info(row: sqlite3.Row, cols: list[str]) -> AppInfo:
        return AppInfo(
            process_name=row["process_name"],
            display_name=row["display_name"],
            category=AppCategory(row["category"]),
            exe_path=row["exe_path"] if "exe_path" in cols else "",
            icon_path=row["icon_path"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
        )

    @staticmethod
    def _row_to_daily_stat(row: sqlite3.Row) -> DailyStat:
        keys = row.keys()
        return DailyStat(
            date=date.fromisoformat(row["date"]),
            total_screen_time_s=row["total_screen_time_s"],
            active_time_s=row["active_time_s"],
            idle_time_s=row["idle_time_s"],
            top_app=row["top_app"],
            session_count=row["session_count"],
            unlock_count=row["unlock_count"] if "unlock_count" in keys else 0,
            category_usage_json=row["category_usage_json"] if "category_usage_json" in keys else "{}",
            app_usage_json=row["app_usage_json"] if "app_usage_json" in keys else "[]",
            timeline_json=row["timeline_json"] if "timeline_json" in keys else "[]",
        )

    def close(self) -> None:
        """Close the SQLite connection for the current thread if open.
        Repository uses thread-local connections; calling close() from the current
        thread will close that thread's connection.
        """
        try:
            if hasattr(self._local, "conn") and self._local.conn:
                try:
                    # Let SQLite refresh stale index statistics before the
                    # connection goes away (recommended by the SQLite docs).
                    self._local.conn.execute("PRAGMA optimize;")
                except Exception:
                    pass
                try:
                    self._local.conn.close()
                    logger.info("Closed repository DB connection for thread %s", threading.current_thread().name)
                except Exception as exc:
                    logger.warning("Error closing DB connection: %s", exc)
                finally:
                    try:
                        self._local.conn = None
                    except Exception:
                        pass
        except Exception:
            logger.exception("Unexpected error while closing DB connection")

    # Backwards-compatible alias
    def close_thread_connection(self) -> None:
        self.close()

    def _cleanup_test_data(self) -> None:
        if Repository._db_path_override is not None:
            return
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM app_sessions WHERE "
                    "(process_name = 'chrome.exe' AND window_title = 'GitHub - Test') OR "
                    "(process_name = 'test_tracker.exe') OR "
                    "(process_name = 'chrome.exe' AND window_title = 'Tracker Test Window')"
                )
        except Exception as e:
            logger.error("Failed to clean up test database data: %s", e)

    # ─── Focus Sessions & Recaps ──────────────────────────────────────────────

    def insert_focus_session(
        self,
        mode: str,
        planned_s: float,
        started_at: datetime,
        strict: bool = False,
        lockout: bool = False,
        auto_started: bool = False,
        schedule_id: str = "",
    ) -> int:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO focus_sessions
                        (mode, planned_s, started_at, strict, lockout,
                         auto_started, schedule_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mode,
                        float(planned_s),
                        started_at.isoformat(),
                        int(strict),
                        int(lockout),
                        int(auto_started),
                        schedule_id,
                    ),
                )
                return cur.lastrowid or 0

    def finish_focus_session(
        self,
        session_id: int,
        actual_s: float,
        ended_at: datetime,
        was_completed: bool,
        blocked_apps: int = 0,
        blocked_sites: int = 0,
        interruptions: int = 0,
        blocked_apps_json: str = "{}",
        blocked_sites_json: str = "{}",
        recap_json: str = "{}",
    ) -> None:
        with self._write_lock:
            with self._cursor() as cur:
                cur.execute(
                    """
                    UPDATE focus_sessions
                    SET actual_s=?, ended_at=?, was_completed=?,
                        blocked_apps=?, blocked_sites=?, interruptions=?,
                        blocked_apps_json=?, blocked_sites_json=?, recap_json=?
                    WHERE id=?
                    """,
                    (
                        float(actual_s),
                        ended_at.isoformat(),
                        int(was_completed),
                        int(blocked_apps),
                        int(blocked_sites),
                        int(interruptions),
                        blocked_apps_json,
                        blocked_sites_json,
                        recap_json,
                        int(session_id),
                    ),
                )

    def get_focus_sessions(
        self,
        limit: int = 20,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[dict]:
        conditions = ["1=1"]
        params: list[object] = []
        if start_date:
            conditions.append("started_at >= ?")
            params.append(datetime.combine(start_date, datetime.min.time()).isoformat())
        if end_date:
            conditions.append("started_at <= ?")
            params.append(datetime.combine(end_date, datetime.max.time()).isoformat())
        params.append(int(limit))
        sql = (
            "SELECT * FROM focus_sessions WHERE "
            + " AND ".join(conditions)
            + " ORDER BY started_at DESC LIMIT ?"
        )
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def get_focus_session(self, session_id: int) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM focus_sessions WHERE id=?", (int(session_id),))
            row = cur.fetchone()
            return dict(row) if row else None

    # ─── App Locker ───────────────────────────────────────────────────────────

    def get_locked_apps(self) -> List[dict]:
        """Return all locked apps as a list of dicts with keys:
        process_name, display_name, exe_path, icon_path, added_at."""
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT process_name, display_name, exe_path, icon_path, added_at "
                    "FROM app_locker_apps ORDER BY display_name COLLATE NOCASE"
                )
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("get_locked_apps failed: %s", e)
            return []

    def add_locked_app(self, process_name: str, display_name: str,
                       exe_path: str = "", icon_path: Optional[str] = None) -> bool:
        """Insert or replace a locked app entry. Returns True on success."""
        try:
            added_at = datetime.now(timezone.utc).isoformat()
            with self._cursor() as cur:
                cur.execute(
                    "INSERT OR REPLACE INTO app_locker_apps "
                    "(process_name, display_name, exe_path, icon_path, added_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (process_name.lower(), display_name, exe_path, icon_path, added_at),
                )
            return True
        except Exception as e:
            logger.error("add_locked_app failed for %s: %s", process_name, e)
            return False

    def remove_locked_app(self, process_name: str) -> bool:
        """Remove a locked app by process name. Returns True on success."""
        try:
            with self._cursor() as cur:
                cur.execute(
                    "DELETE FROM app_locker_apps WHERE process_name = ?",
                    (process_name.lower(),),
                )
            return True
        except Exception as e:
            logger.error("remove_locked_app failed for %s: %s", process_name, e)
            return False

    def clear_locked_apps(self) -> bool:
        """Remove ALL locked app entries. Returns True on success."""
        try:
            with self._cursor() as cur:
                cur.execute("DELETE FROM app_locker_apps")
            return True
        except Exception as e:
            logger.error("clear_locked_apps failed: %s", e)
            return False

