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

CREATE_FOCUS_SESSIONS = """
CREATE TABLE IF NOT EXISTS focus_sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    mode                TEXT    NOT NULL,
    planned_s           REAL    NOT NULL DEFAULT 0,
    actual_s            REAL    NOT NULL DEFAULT 0,
    started_at          TEXT    NOT NULL,
    ended_at            TEXT,
    was_completed       INTEGER NOT NULL DEFAULT 0,
    strict              INTEGER NOT NULL DEFAULT 0,
    lockout             INTEGER NOT NULL DEFAULT 0,
    blocked_apps        INTEGER NOT NULL DEFAULT 0,
    blocked_sites       INTEGER NOT NULL DEFAULT 0,
    interruptions       INTEGER NOT NULL DEFAULT 0,
    auto_started        INTEGER NOT NULL DEFAULT 0,
    schedule_id         TEXT    NOT NULL DEFAULT '',
    blocked_apps_json   TEXT    NOT NULL DEFAULT '{}',
    blocked_sites_json  TEXT    NOT NULL DEFAULT '{}',
    recap_json          TEXT    NOT NULL DEFAULT '{}'
);
"""

CREATE_SMART_TASKS = """
CREATE TABLE IF NOT EXISTS smart_tasks (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT    NOT NULL,
    description         TEXT    DEFAULT '',
    priority            INTEGER DEFAULT 2,
    estimated_minutes   INTEGER DEFAULT 25,
    actual_active_s     REAL    DEFAULT 0.0,
    status              TEXT    DEFAULT 'pending',
    target_processes    TEXT    DEFAULT '[]',
    target_domains      TEXT    DEFAULT '[]',
    due_date            TEXT,
    scheduled_time      TEXT    DEFAULT '',
    start_time          TEXT    DEFAULT '',
    end_time            TEXT    DEFAULT '',
    repeat_days         TEXT    DEFAULT '[]',
    day_notes_json      TEXT    DEFAULT '{}',
    category            TEXT    DEFAULT 'General',
    is_template         INTEGER DEFAULT 0,
    created_at          TEXT    NOT NULL,
    completed_at        TEXT
);
"""

CREATE_DAILY_WATER_LOGS = """
CREATE TABLE IF NOT EXISTS daily_water_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date            TEXT    NOT NULL UNIQUE,
    target_ml           INTEGER NOT NULL DEFAULT 3000,
    current_ml          INTEGER NOT NULL DEFAULT 0,
    checkpoints_json    TEXT    NOT NULL DEFAULT '[]'
);
"""


CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_start      ON app_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_process    ON app_sessions(process_name);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_category   ON app_sessions(category);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_end        ON app_sessions(end_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_open       ON app_sessions(end_time) WHERE end_time IS NULL;",
    # Composite indexes for the hot analytics paths. Plain single-column
    # indexes force SQLite to fetch every matching row before applying the
    # second predicate; these let it seek straight into a process/domain and
    # then range-scan the requested date window.
    "CREATE INDEX IF NOT EXISTS idx_sessions_process_start ON app_sessions(process_name, start_time);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_category_start ON app_sessions(category, start_time);",
    "CREATE INDEX IF NOT EXISTS idx_event_log_time      ON event_log(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_event_log_type      ON event_log(event_type);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_start ON website_sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_website_sessions_domain ON website_sessions(domain);",
    "CREATE INDEX IF NOT EXISTS idx_website_domain_start ON website_sessions(domain, start_time);",
    "CREATE INDEX IF NOT EXISTS idx_website_browser_start ON website_sessions(browser_process, start_time);",
    "CREATE INDEX IF NOT EXISTS idx_focus_sessions_start ON focus_sessions(started_at);",
    "CREATE INDEX IF NOT EXISTS idx_smart_tasks_status   ON smart_tasks(status);",
    "CREATE INDEX IF NOT EXISTS idx_smart_tasks_created  ON smart_tasks(created_at);",
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

MIGRATE_ADD_SMART_TASKS_SCHEDULED_TIME = """
ALTER TABLE smart_tasks ADD COLUMN scheduled_time TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_SMART_TASKS_START_TIME = """
ALTER TABLE smart_tasks ADD COLUMN start_time TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_SMART_TASKS_END_TIME = """
ALTER TABLE smart_tasks ADD COLUMN end_time TEXT NOT NULL DEFAULT '';
"""

MIGRATE_ADD_SMART_TASKS_REPEAT_DAYS = """
ALTER TABLE smart_tasks ADD COLUMN repeat_days TEXT NOT NULL DEFAULT '[]';
"""

MIGRATE_ADD_SMART_TASKS_DAY_NOTES = """
ALTER TABLE smart_tasks ADD COLUMN day_notes_json TEXT NOT NULL DEFAULT '{}';
"""

MIGRATE_ADD_SMART_TASKS_CATEGORY = """
ALTER TABLE smart_tasks ADD COLUMN category TEXT NOT NULL DEFAULT 'General';
"""

MIGRATE_ADD_SMART_TASKS_IS_TEMPLATE = """
ALTER TABLE smart_tasks ADD COLUMN is_template INTEGER NOT NULL DEFAULT 0;
"""

ALL_DDL = [
    CREATE_APP_SESSIONS,
    CREATE_APP_INFO,
    CREATE_DAILY_STATS,
    CREATE_SETTINGS,
    CREATE_EVENT_LOG,
    CREATE_WEBSITE_SESSIONS,
    CREATE_APP_LOCKER_APPS,
    CREATE_FOCUS_SESSIONS,
    CREATE_SMART_TASKS,
    CREATE_DAILY_WATER_LOGS,
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
    ("scheduled_time", "smart_tasks", MIGRATE_ADD_SMART_TASKS_SCHEDULED_TIME),
    ("start_time", "smart_tasks", MIGRATE_ADD_SMART_TASKS_START_TIME),
    ("end_time", "smart_tasks", MIGRATE_ADD_SMART_TASKS_END_TIME),
    ("repeat_days", "smart_tasks", MIGRATE_ADD_SMART_TASKS_REPEAT_DAYS),
    ("day_notes_json", "smart_tasks", MIGRATE_ADD_SMART_TASKS_DAY_NOTES),
    ("category", "smart_tasks", MIGRATE_ADD_SMART_TASKS_CATEGORY),
    ("is_template", "smart_tasks", MIGRATE_ADD_SMART_TASKS_IS_TEMPLATE),
]

DEFAULT_SETTINGS = {
    "idle_threshold_s": "300",
    "autostart": "false",
    "dark_mode": "true",
    "minimize_to_tray": "true",
    "notifications_enabled": "true",
    "daily_limit_minutes": "480",
    "export_path": "",
    "fragmentation_nudge_enabled": "true",
    "ui_density": "comfortable",
    # App Locker defaults
    "app_locker_enabled": "false",
    "app_locker_auth_method": "hello_pin",  # hello | pin | hello_pin
    "app_locker_auth_duration": "15_min",   # every_launch | 5_min | 15_min | until_close
}
