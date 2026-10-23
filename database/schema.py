from __future__ import annotations

CREATE_APP_SESSIONS = """
CREATE TABLE IF NOT EXISTS app_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    process_name    TEXT    NOT NULL,
    exe_path        TEXT    NOT NULL DEFAULT '',
    window_title    TEXT    NOT NULL DEFAULT '',
    start_time      TEXT    NOT NULL,
    end_time        TEXT,
    duration_s      REAL    NOT NULL DEFAULT 0,
    category        TEXT    NOT NULL DEFAULT 'Other',
    is_idle         INTEGER NOT NULL DEFAULT 0,
    was_closed      INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_APP_INFO = """
CREATE TABLE IF NOT EXISTS app_info (
    process_name    TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    category        TEXT NOT NULL DEFAULT 'Other',
    exe_path        TEXT NOT NULL DEFAULT '',
    icon_path       TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL
);
"""

CREATE_DAILY_STATS = """
CREATE TABLE IF NOT EXISTS daily_stats (
    date                TEXT PRIMARY KEY,
    total_screen_time_s REAL NOT NULL DEFAULT 0,
    active_time_s       REAL NOT NULL DEFAULT 0,
    idle_time_s         REAL NOT NULL DEFAULT 0,
    top_app             TEXT,
    session_count       INTEGER NOT NULL DEFAULT 0,
    unlock_count        INTEGER NOT NULL DEFAULT 0,
    category_usage_json TEXT NOT NULL DEFAULT '{}',
    app_usage_json      TEXT NOT NULL DEFAULT '[]',
    timeline_json       TEXT NOT NULL DEFAULT '[]'
);
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);
"""

CREATE_EVENT_LOG = """
CREATE TABLE IF NOT EXISTS event_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    detail      TEXT    NOT NULL DEFAULT ''
);
"""

CREATE_WEBSITE_SESSIONS = """
CREATE TABLE IF NOT EXISTS website_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    domain          TEXT    NOT NULL,
    browser_process TEXT    NOT NULL,
    start_time      TEXT    NOT NULL,
    end_time        TEXT,
    duration_s      REAL    NOT NULL DEFAULT 0,
    was_closed      INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_APP_LOCKER_APPS = """
CREATE TABLE IF NOT EXISTS app_locker_apps (
    process_name    TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    exe_path        TEXT NOT NULL DEFAULT '',
    icon_path       TEXT,
    added_at        TEXT NOT NULL
);
"""


CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_start      ON app_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_process    ON app_sessions(process_name);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_category   ON app_sessions(category);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_end        ON app_sessions(end_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_open       ON app_sessions(end_time) WHERE end_time IS NULL;",
    "CREATE INDEX IF NOT EXISTS idx_event_log_time      ON event_log(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_event_log_type      ON event_log(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_start ON website_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_domain ON website_sessions(domain);",
]

MIGRATE_ADD_EXE_PATH = """
ALTER TABLE app_sessions ADD COLUMN exe_path TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_WAS_CLOSED = """
ALTER TABLE app_sessions ADD COLUMN was_closed INTEGER NOT NULL DEFAULT 0;
"""

MIGRATE_ADD_APP_INFO_LAST_SEEN = """
ALTER TABLE app_info ADD COLUMN last_seen TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_APP_INFO_EXE_PATH = """
ALTER TABLE app_info ADD COLUMN exe_path TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_DS_UNLOCK_COUNT = """
ALTER TABLE daily_stats ADD COLUMN unlock_count INTEGER NOT NULL DEFAULT 0;
"""

MIGRATE_ADD_DS_CATEGORY_JSON = """
ALTER TABLE daily_stats ADD COLUMN category_usage_json TEXT NOT NULL DEFAULT '{}';
"""

MIGRATE_ADD_DS_APP_JSON = """
ALTER TABLE daily_stats ADD COLUMN app_usage_json TEXT NOT NULL DEFAULT '[]';
"""

MIGRATE_ADD_DS_TIMELINE_JSON = """
ALTER TABLE daily_stats ADD COLUMN timeline_json TEXT NOT NULL DEFAULT '[]';
"""

ALL_DDL = [
    CREATE_APP_SESSIONS,
    CREATE_APP_INFO,
    CREATE_DAILY_STATS,
    CREATE_SETTINGS,
    CREATE_EVENT_LOG,
    CREATE_WEBSITE_SESSIONS,
    CREATE_APP_LOCKER_APPS,
    *CREATE_INDEXES,
]

MIGRATIONS = [
    ("exe_path",    "app_sessions",  MIGRATE_ADD_EXE_PATH),
    ("was_closed",  "app_sessions",  MIGRATE_ADD_WAS_CLOSED),
    ("last_seen",   "app_info",      MIGRATE_ADD_APP_INFO_LAST_SEEN),
    ("exe_path",    "app_info",      MIGRATE_ADD_APP_INFO_EXE_PATH),
    ("unlock_count", "daily_stats",  MIGRATE_ADD_DS_UNLOCK_COUNT),
    ("category_usage_json", "daily_stats", MIGRATE_ADD_DS_CATEGORY_JSON),
    ("app_usage_json", "daily_stats", MIGRATE_ADD_DS_APP_JSON),
    ("timeline_json", "daily_stats", MIGRATE_ADD_DS_TIMELINE_JSON),
]

DEFAULT_SETTINGS = {
    "idle_threshold_s": "300",
    "autostart": "false",
    "dark_mode": "true",
    "minimize_to_tray": "true",
    "notifications_enabled": "true",
    "daily_limit_minutes": "480",
    "export_path": "",
    # App Locker defaults
    "app_locker_enabled": "false",
    "app_locker_auth_method": "hello_pin",  # hello | pin | hello_pin
    "app_locker_auth_duration": "15_min",   # every_launch | 5_min | 15_min | until_close
}
