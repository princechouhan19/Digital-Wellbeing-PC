from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from core.constants import AppCategory, MAX_SESSION_GAP_S, POLL_INTERVAL_MS
from core.logger import logger
from database.models import AppInfo, AppSession
from database.repository import Repository
from settings.manager import SettingsManager
from tracker.auditor import TrackingAuditor
from tracker.categorizer import categorize, categorize_with_reason, display_name
from tracker.debug_logger import debug_logger
from tracker.foreground import ForegroundApp, apps_are_same, get_foreground_app, is_window_fullscreen
from tracker.idle import get_idle_seconds, is_idle
from tracker.media import MediaDetectionEngine
from tracker.session import SessionEvent, SessionMonitor

_MIN_SESSION_DURATION_S = 1.0
_HEARTBEAT_INTERVAL_S = 10.0


class TrackingManager:
    def __init__(self) -> None:
        self._repo = Repository()
        self._sm = SettingsManager()
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._session_monitor = SessionMonitor(self._on_session_event)
        self._media_engine = MediaDetectionEngine(poll_interval=5.0)
        self._state_lock = threading.Lock()

        self._current_app: Optional[ForegroundApp] = None
        self._session_start: Optional[datetime] = None
        self._current_session_id: Optional[int] = None
        self._current_is_idle: bool = False
        self._current_category: Optional[AppCategory] = None
        self._current_is_fullscreen: bool = False
        self._current_game_reason: str = ""
        self._current_launcher_reason: str = ""
        self._current_transition_reason: str = ""
        self._debug_enabled: bool = self._sm.debug_tracking
        
        self._current_website_url: str = ""
        self._current_website_session_id: Optional[int] = None
        self._current_website_start: Optional[datetime] = None

        self._last_heartbeat: float = 0.0
        self._last_tick_time: Optional[datetime] = None
        self._consecutive_errors: int = 0

        # Debounce grace buffer for momentary focus loss / transitions
        self._grace_app: Optional[ForegroundApp] = None
        self._grace_timer: Optional[datetime] = None

        self._idle_threshold_s: float = float(
            self._repo.get_setting("idle_threshold_s") or 300
        )
        self._shutdown_mode: str = self._sm.shutdown_mode
        self._media_idle_timeout_s: float = self._sm.media_idle_timeout_minutes * 60.0
        self._data_changed_callbacks: list[Callable[[], None]] = []
        self._on_active_tick_callbacks: list[Callable[[str, float, str], None]] = []

    # ─── Public API ───────────────────────────────────────────────────────────

    def add_data_changed_callback(self, cb: Callable[[], None]) -> None:
        self._data_changed_callbacks.append(cb)

    def add_active_tick_callback(self, cb: Callable[[str, float, str], None]) -> None:
        self._on_active_tick_callbacks.append(cb)

    def start(self) -> None:
        with self._state_lock:
            if self._running:
                logger.info("[LIFECYCLE] TrackingManager.start() called but already running")
                return
            self._running = True
            self._paused = False

        logger.info("[LIFECYCLE] Starting SessionMonitor and TrackingManager thread...")
        self._session_monitor.start()
        self._media_engine.start()
        self._thread = threading.Thread(
            target=self._tracking_loop,
            daemon=True,
            name="TrackingManager",
        )
        self._thread.start()
        logger.info("[LIFECYCLE] TrackingManager thread started (ident=%s, daemon=%s)", self._thread.ident, self._thread.daemon)
        
        self._repo.log_event("tracker_start", "Tracking started")
        logger.info("Tracking started")

    def stop(self) -> None:
        with self._state_lock:
            if not self._running:
                logger.info("[LIFECYCLE] TrackingManager.stop() called but not running")
                return
            self._running = False

        logger.info("[LIFECYCLE] Stopping TrackingManager and SessionMonitor...")
        thread = self._thread

        self._session_monitor.stop()
        self._media_engine.stop()
        self._end_current_session(reason="stop")
        self._end_website_session(datetime.now())
        
        self._repo.log_event("tracker_stop", "Tracking stopped")
        logger.info("[LIFECYCLE] Tracking stopped — waiting for tracking thread to exit...")

        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning("[LIFECYCLE] Tracking thread did not exit within 5 seconds (ident=%s).", thread.ident)
            else:
                logger.info("[LIFECYCLE] Tracking thread exited cleanly.")

        self._thread = None

    def reload_settings(self) -> None:
        self._idle_threshold_s = float(
            self._repo.get_setting("idle_threshold_s") or 300
        )
        self._shutdown_mode = self._sm.shutdown_mode
        self._media_idle_timeout_s = self._sm.media_idle_timeout_minutes * 60.0
        self._debug_enabled = self._sm.debug_tracking
        logger.debug("Settings reloaded: idle=%.0fs, debug=%s", self._idle_threshold_s, self._debug_enabled)

    def get_debug_state(self) -> dict[str, Any]:
        with self._state_lock:
            now = datetime.now()
            timer_s = (now - self._session_start).total_seconds() if self._session_start else 0.0
            cat_str = str(self._current_category.value if hasattr(self._current_category, "value") else (self._current_category or "None"))
            return {
                "process_name": self._current_app.process_name if self._current_app else "None",
                "exe_path": self._current_app.exe_path if self._current_app else "",
                "window_title": self._current_app.window_title if self._current_app else "",
                "category": cat_str,
                "session_timer_s": timer_s,
                "is_idle": self._current_is_idle,
                "is_fullscreen": self._current_is_fullscreen,
                "game_reason": self._current_game_reason,
                "launcher_reason": self._current_launcher_reason,
                "session_id": self._current_session_id,
                "last_reason": self._current_transition_reason,
                "debug_enabled": self._debug_enabled,
            }

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def current_app(self) -> Optional[ForegroundApp]:
        return self._current_app

    @property
    def idle_seconds(self) -> float:
        return get_idle_seconds()

    # ─── Tracking loop ────────────────────────────────────────────────────────

    def _tracking_loop(self) -> None:
        poll_s = POLL_INTERVAL_MS / 1000.0

        try:
            while self._running:
                try:
                    if not self._paused:
                        self._tick(poll_s)
                        self._consecutive_errors = 0
                except Exception as exc:
                    self._consecutive_errors += 1
                    logger.error(
                        "Tracking loop error #%d: %s",
                        self._consecutive_errors,
                        exc,
                        exc_info=True,
                    )
                    if self._consecutive_errors >= 10:
                        logger.critical("Too many consecutive errors, pausing tracking for 60s")
                        time.sleep(60.0)
                        self._consecutive_errors = 0
                time.sleep(poll_s)
        finally:
            # Ensure the thread's DB connection is closed before thread exit
            try:
                self._repo.close()
                logger.info("TrackingManager thread closed its DB connection")
            except Exception as exc:
                logger.warning("Failed to close repository connection in tracking thread: %s", exc)

    def _tick(self, delta_s: float) -> None:
        now = datetime.now()

        # Pre-sleep time-skip guard (e.g. system hibernate/suspend without event firing)
        if self._last_tick_time is not None:
            gap_s = (now - self._last_tick_time).total_seconds()
            if gap_s > 10.0:
                logger.warning("[SLEEPGUARD] Time skip detected (%.1fs gap). Ending pre-sleep session.", gap_s)
                self._end_current_session(reason="sleep_gap", capped_end_time=self._last_tick_time)
                self._end_website_session(self._last_tick_time)
        self._last_tick_time = now

        fg = get_foreground_app(self._current_app)
        from core.constants import AppCategory as _Cat
        
        media_engine_active = False
        if self._media_engine.is_playing and fg:
            app_n = fg.process_name.lower()
            m_app = self._media_engine.current.app_name.lower()
            # Match direct process name or AUMID
            if app_n.replace(".exe", "") in m_app or m_app in app_n:
                media_engine_active = True
            # Match if both foreground and media source are browsers
            elif app_n in {"chrome.exe", "brave.exe", "msedge.exe", "firefox.exe"} and any(b in m_app for b in {"chrome", "brave", "msedge", "firefox", "chromium"}):
                media_engine_active = True
                
        # For tracking purposes, decouple from SleepGuard's mode.
        # Treat media playing and fullscreen apps as highly active to prevent premature session splits.
        is_media = (self._current_category == _Cat.ENTERTAINMENT) or media_engine_active or (fg and getattr(fg, "is_fullscreen", False))
        
        tracking_idle_threshold = self._idle_threshold_s
        if is_media:
            tracking_idle_threshold = max(tracking_idle_threshold, 7200.0)  # 2 hours for media/fullscreen
        elif self._current_category == _Cat.GAMING:
            tracking_idle_threshold = max(tracking_idle_threshold, 3600.0)  # 1 hour for gaming
            
        idle = get_idle_seconds() >= tracking_idle_threshold

        if fg is None:
            if self._current_app is not None:
                # Use longer grace period for fullscreen apps (5s vs 2.5s)
                _grace_limit = 5.0 if self._current_is_fullscreen else 2.5
                if self._grace_app is None:
                    self._grace_app = self._current_app
                    self._grace_timer = now
                elif self._grace_timer is not None and (now - self._grace_timer).total_seconds() >= _grace_limit:
                    TrackingAuditor.log_poll_event(None, "EndSession", reason="No foreground window")
                    self._end_current_session(reason="no_foreground", capped_end_time=self._grace_timer)
                    self._end_website_session(self._grace_timer)
                    self._grace_app = None
                    self._grace_timer = None
            return

        # Foreground window is present — clear grace buffer
        self._grace_app = None
        self._grace_timer = None
        self._current_is_fullscreen = fg.is_fullscreen
        
        # Dispatch active tick for limits/timers and adult content shield
        if not idle:
            for cb in self._on_active_tick_callbacks:
                try:
                    cb(fg.process_name, delta_s, getattr(fg, "url", ""), fg.window_title, fg.hwnd)
                except TypeError:
                    try:
                        cb(fg.process_name, delta_s, getattr(fg, "url", ""))
                    except Exception as exc:
                        logger.warning(f"Active tick callback failed: {exc}")
                except Exception as exc:
                    logger.warning(f"Active tick callback failed: {exc}")

        same_process = self._current_app is not None and fg.process_name == self._current_app.process_name
        title_changed = self._current_app is not None and fg.window_title != self._current_app.window_title
        idle_changed = idle != self._current_is_idle
        is_fullscreen_game = self._current_is_fullscreen and self._current_category == AppCategory.GAMING

        # If process changed or idle state changed: transition to new session
        if self._current_app is None or not same_process or idle_changed:
            if self._current_app is not None:
                reason = "app_switch" if not same_process else "idle_switch"
                TrackingAuditor.log_poll_event(self._current_app, "EndSession", reason=reason, session_id=self._current_session_id)
                self._end_current_session(reason=reason)
                self._end_website_session(now)

            TrackingAuditor.log_poll_event(fg, "StartSession", reason="new_foreground")
            self._start_session(fg, now, idle, reason="new_foreground" if self._current_app is None else reason)
            
            url = getattr(fg, "url", "")
            if url and not idle:
                self._start_website_session(fg.process_name, url, now)
            return
            
        url = getattr(fg, "url", "")
        if url != self._current_website_url:
            self._end_website_session(now)
            if url and not idle:
                self._start_website_session(fg.process_name, url, now)

        # Same process, same idle state, but window title changed
        if title_changed:
            # For fullscreen games, NEVER split the session on title change.
            # Games frequently change titles during gameplay (loading screens,
            # round transitions, etc.) and splitting creates cumulative time gaps.
            if is_fullscreen_game:
                # Just update the title in-place without splitting
                logger.debug(
                    "[TRACKING] Fullscreen game title change suppressed (no split). "
                    "process=%s, old_title=%r, new_title=%r",
                    fg.process_name,
                    self._current_app.window_title if self._current_app else "?",
                    fg.window_title,
                )
                TrackingAuditor.log_poll_event(fg, "UpdateTitle", reason="fullscreen_game_title_change", session_id=self._current_session_id)
                self._current_app = fg
                if self._current_session_id:
                    try:
                        self._repo.update_session_title(self._current_session_id, fg.window_title)
                    except Exception as exc:
                        logger.warning("Failed to update session title in DB: %s", exc)
            # For non-games: split into contiguous sub-session if previous session ran for at least 2 seconds
            elif self._session_start and (now - self._session_start).total_seconds() >= 2.0:
                TrackingAuditor.log_poll_event(self._current_app, "EndSession", reason="title_split", session_id=self._current_session_id)
                self._end_current_session(reason="title_split", capped_end_time=now)
                TrackingAuditor.log_poll_event(fg, "StartSession", reason="title_split")
                self._start_session(fg, now, idle, reason="title_split")
            else:
                TrackingAuditor.log_poll_event(fg, "UpdateTitle", reason="title_change", session_id=self._current_session_id)
                self._current_app = fg
                if self._debug_enabled:
                    debug_logger.log_event(
                        "UPDATE_TITLE",
                        pid=fg.pid,
                        process_name=fg.process_name,
                        exe_path=fg.exe_path,
                        window_title=fg.window_title,
                        category=str(self._current_category.value if hasattr(self._current_category, "value") else self._current_category),
                        session_id=self._current_session_id,
                        start_time=self._session_start.isoformat() if self._session_start else "N/A",
                        end_time="N/A",
                        is_idle=idle,
                        is_fullscreen=self._current_is_fullscreen,
                        reason="title_change",
                        game_reason=self._current_game_reason,
                        launcher_reason=self._current_launcher_reason,
                    )
                if self._current_session_id:
                    try:
                        self._repo.update_session_title(self._current_session_id, fg.window_title)
                    except Exception as exc:
                        logger.warning("Failed to update session title in DB: %s", exc)

        self._maybe_heartbeat(now)

    def _maybe_heartbeat(self, now: datetime) -> None:
        ts = now.timestamp()
        if ts - self._last_heartbeat >= _HEARTBEAT_INTERVAL_S:
            self._last_heartbeat = ts
            if self._current_session_id and self._session_start:
                duration = (now - self._session_start).total_seconds()
                try:
                    self._repo.update_session_end(
                        self._current_session_id,
                        now,
                        duration,
                        was_closed=False,
                    )
                except Exception as exc:
                    logger.warning("Heartbeat update failed: %s", exc)
                    
            if self._current_website_session_id and self._current_website_start:
                w_duration = (now - self._current_website_start).total_seconds()
                try:
                    self._repo.update_website_session_end(
                        self._current_website_session_id,
                        now,
                        w_duration,
                        was_closed=False
                    )
                except Exception as exc:
                    logger.warning("Website heartbeat update failed: %s", exc)

    # ─── Session lifecycle ────────────────────────────────────────────────────

    def _start_session(
        self, fg: ForegroundApp, start_time: datetime, idle: bool, reason: str = "app_switch"
    ) -> None:
        try:
            category, game_reason, launcher_reason = categorize_with_reason(fg.process_name, fg.exe_path)
            self._current_category = category
            self._current_game_reason = game_reason
            self._current_launcher_reason = launcher_reason
            self._current_transition_reason = reason

            session = AppSession(
                process_name=fg.process_name,
                exe_path=fg.exe_path,
                window_title=fg.window_title,
                start_time=start_time,
                end_time=None,
                duration_s=0.0,
                category=category,
                is_idle=idle,
                was_closed=False,
            )
            session_id = self._repo.insert_session(session)

            info = AppInfo(
                process_name=fg.process_name,
                display_name=display_name(fg.process_name),
                category=category,
                exe_path=fg.exe_path,
                icon_path=None,
                first_seen=start_time,
                last_seen=start_time,
            )
            self._repo.upsert_app_info(info)

            self._current_app = fg
            self._session_start = start_time
            self._current_session_id = session_id
            self._current_is_idle = idle
            self._last_heartbeat = start_time.timestamp()

            if self._debug_enabled:
                debug_logger.log_event(
                    "START_SESSION",
                    pid=fg.pid,
                    process_name=fg.process_name,
                    exe_path=fg.exe_path,
                    window_title=fg.window_title,
                    category=str(category.value if hasattr(category, "value") else category),
                    session_id=session_id,
                    start_time=start_time.isoformat(),
                    end_time="N/A",
                    is_idle=idle,
                    is_fullscreen=self._current_is_fullscreen,
                    reason=reason,
                    game_reason=game_reason,
                    launcher_reason=launcher_reason,
                )

        except Exception as exc:
            logger.error("Failed to start session for %s: %s", fg.process_name, exc)

    def _end_current_session(
        self, reason: str = "", capped_end_time: Optional[datetime] = None
    ) -> None:
        session_id = self._current_session_id
        session_start = self._session_start
        app = self._current_app
        is_idle_val = self._current_is_idle
        is_fs_val = self._current_is_fullscreen
        cat_val = self._current_category
        game_r = self._current_game_reason
        launcher_r = self._current_launcher_reason

        self._current_app = None
        self._session_start = None
        self._current_session_id = None
        self._current_is_idle = False
        self._current_category = None
        self._last_heartbeat = 0.0

        if session_id is None or session_start is None:
            return

        end_time = capped_end_time if capped_end_time is not None else datetime.now()
        duration = max(0.0, (end_time - session_start).total_seconds())

        if reason != "title_split":
            self._end_website_session(end_time)

        if self._debug_enabled and app:
            cat_str = str(cat_val.value if hasattr(cat_val, "value") else (cat_val or "None"))
            debug_logger.log_event(
                "END_SESSION",
                pid=app.pid,
                process_name=app.process_name,
                exe_path=app.exe_path,
                window_title=app.window_title,
                category=cat_str,
                session_id=session_id,
                start_time=session_start.isoformat(),
                end_time=end_time.isoformat(),
                is_idle=is_idle_val,
                is_fullscreen=is_fs_val,
                reason=reason,
                game_reason=game_r,
                launcher_reason=launcher_r,
            )

        if duration < _MIN_SESSION_DURATION_S:
            try:
                self._repo.delete_session(session_id)
            except Exception:
                pass
            return

        try:
            self._repo.update_session_end(
                session_id,
                end_time,
                duration,
                was_closed=True,
            )
            self._notify_data_changed()
        except Exception as exc:
            logger.error("Failed to end session %d: %s", session_id, exc)

    def _start_website_session(self, process_name: str, domain: str, start_time: datetime) -> None:
        try:
            from database.models import WebsiteSession
            ws = WebsiteSession(
                domain=domain,
                browser_process=process_name,
                start_time=start_time,
                end_time=None,
                duration_s=0.0,
                was_closed=False
            )
            session_id = self._repo.insert_website_session(ws)
            self._current_website_url = domain
            self._current_website_start = start_time
            self._current_website_session_id = session_id
        except Exception as exc:
            logger.error("Failed to start website session for %s: %s", domain, exc)

    def _end_website_session(self, capped_end_time: datetime) -> None:
        session_id = self._current_website_session_id
        start_time = self._current_website_start

        self._current_website_url = ""
        self._current_website_session_id = None
        self._current_website_start = None

        if session_id is None or start_time is None:
            return

        duration = max(0.0, (capped_end_time - start_time).total_seconds())
        if duration < _MIN_SESSION_DURATION_S:
            # We don't have a delete_website_session, but we could add one if needed.
            # For now, it will just end up with 0s.
            pass

        try:
            self._repo.update_website_session_end(
                session_id,
                capped_end_time,
                duration,
                was_closed=True
            )
            self._notify_data_changed()
        except Exception as exc:
            logger.error("Failed to end website session %d: %s", session_id, exc)

    # ─── Session events ───────────────────────────────────────────────────────

    def _on_session_event(self, event: SessionEvent) -> None:
        logger.info("System event: %s", event.name)
        self._repo.log_event(event.name.lower(), "")

        if event in (SessionEvent.LOCK, SessionEvent.SLEEP, SessionEvent.LOGOFF):
            self._paused = True
            self._end_current_session(reason=event.name.lower())

        elif event == SessionEvent.SHUTDOWN:
            self._end_current_session(reason="shutdown")
            self._running = False

        elif event in (SessionEvent.UNLOCK, SessionEvent.RESUME):
            self._paused = False

    # ─── Callbacks ────────────────────────────────────────────────────────────

    def _notify_data_changed(self) -> None:
        for cb in self._data_changed_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.warning("Data changed callback error: %s", exc)
