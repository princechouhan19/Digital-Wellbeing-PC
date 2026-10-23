from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from core.constants import AppCategory


@dataclass
class AppSession:
    process_name: str
    window_title: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_s: float
    category: AppCategory
    is_idle: bool
    exe_path: str = ""
    was_closed: bool = False
    id: Optional[int] = field(default=None)

    @property
    def duration_formatted(self) -> str:
        total = int(self.duration_s)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    @property
    def is_open(self) -> bool:
        return self.end_time is None


@dataclass
class WebsiteSession:
    domain: str
    browser_process: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_s: float
    was_closed: bool = False
    id: Optional[int] = field(default=None)

    @property
    def duration_formatted(self) -> str:
        total = int(self.duration_s)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

    @property
    def is_open(self) -> bool:
        return self.end_time is None



@dataclass
class AppInfo:
    process_name: str
    display_name: str
    category: AppCategory
    icon_path: Optional[str]
    first_seen: datetime
    exe_path: str = ""
    last_seen: Optional[datetime] = None
    total_time_s: float = 0.0
    session_count: int = 0


@dataclass
class DailyStat:
    date: date
    total_screen_time_s: float
    active_time_s: float
    idle_time_s: float
    top_app: Optional[str]
    session_count: int
    unlock_count: int = 0
    category_usage_json: str = "{}"
    app_usage_json: str = "[]"
    timeline_json: str = "[]"


@dataclass
class EventLogEntry:
    timestamp: datetime
    event_type: str
    detail: str
    id: Optional[int] = field(default=None)


@dataclass
class Setting:
    key: str
    value: str
