"""
focus_schedule.py — Recurring Focus sessions (weekday + time + mode).

Schedules are stored as JSON in the local settings table. The engine is
intentionally small: a QTimer checks once every 30 seconds, and a due schedule
starts a normal (non-lockout) Focus session through FocusManager. If the app is
opened partway through a scheduled window, it joins the remaining portion
instead of creating a short session.

The engine never starts a second session while one is active and records the
last fired date so a schedule cannot loop.
"""
from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time as dt_time, timedelta
from typing import List, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger

SETTING_KEY = "focus_schedules"
FIRED_KEY = "focus_schedule_fired"


@dataclass
class FocusSchedule:
    name: str
    mode: str = "work"
    start: str = "09:00"
    duration_min: int = 25
    weekdays: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])
    enabled: bool = True
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode,
            "start": self.start,
            "duration_min": int(self.duration_min),
            "weekdays": [int(d) for d in self.weekdays],
            "enabled": bool(self.enabled),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Optional["FocusSchedule"]:
        try:
            name = str(data.get("name", "")).strip()[:80] or "Focus block"
            mode = str(data.get("mode", "work"))
            if mode not in ("deep", "work", "study", "movie", "custom"):
                mode = "work"
            start = str(data.get("start", "09:00"))
            datetime.strptime(start, "%H:%M")
            duration = max(5, min(180, int(data.get("duration_min", 25))))
            weekdays = sorted({int(d) for d in data.get("weekdays", []) if 0 <= int(d) <= 6})
            if not weekdays:
                return None
            return cls(
                id=str(data.get("id", "")) or uuid.uuid4().hex[:12],
                name=name,
                mode=mode,
                start=start,
                duration_min=duration,
                weekdays=weekdays,
                enabled=bool(data.get("enabled", True)),
            )
        except (TypeError, ValueError):
            return None


class FocusScheduleEngine(QObject):
    schedules_changed = Signal()
    schedule_started = Signal(object)  # FocusSchedule

    def __init__(self, manager=None, repo=None, clock=None, parent=None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._repo = repo
        self._clock = clock or datetime.now
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self.check_now)
        self._fired: dict[str, str] = {}
        self._load_fired()

    # ── storage ────────────────────────────────────────────────────────────

    def _repo_obj(self):
        if self._repo is None:
            from database.repository import Repository

            self._repo = Repository()
        return self._repo

    def load(self) -> List[FocusSchedule]:
        raw = self._repo_obj().get_setting(SETTING_KEY) or "[]"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        schedules = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    schedule = FocusSchedule.from_dict(item)
                    if schedule:
                        schedules.append(schedule)
        return schedules

    def save(self, schedules: List[FocusSchedule]) -> None:
        self._repo_obj().set_setting(
            SETTING_KEY,
            json.dumps([s.to_dict() for s in schedules], separators=(",", ":")),
        )
        self.schedules_changed.emit()

    def add(self, schedule: FocusSchedule) -> None:
        schedules = self.load()
        schedules.append(schedule)
        self.save(schedules)

    def update(self, schedule: FocusSchedule) -> None:
        schedules = [schedule if s.id == schedule.id else s for s in self.load()]
        self.save(schedules)

    def remove(self, schedule_id: str) -> None:
        self.save([s for s in self.load() if s.id != schedule_id])

    def _load_fired(self) -> None:
        raw = self._repo_obj().get_setting(FIRED_KEY) or "{}"
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                self._fired = {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            self._fired = {}

    def _mark_fired(self, schedule: FocusSchedule, now: datetime) -> None:
        self._fired[schedule.id] = now.date().isoformat()
        # Prune old entries.
        cutoff = (now.date() - timedelta(days=14)).isoformat()
        self._fired = {k: v for k, v in self._fired.items() if v >= cutoff}
        try:
            self._repo_obj().set_setting(FIRED_KEY, json.dumps(self._fired))
        except Exception:
            pass

    # ── runtime ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._timer.start()
        self.check_now()

    def stop(self) -> None:
        self._timer.stop()

    def due_schedule(self, now: Optional[datetime] = None) -> Optional[FocusSchedule]:
        now = now or self._clock()
        for schedule in self.load():
            if not schedule.enabled or now.weekday() not in schedule.weekdays:
                continue
            if self._fired.get(schedule.id) == now.date().isoformat():
                continue
            try:
                hour, minute = (int(part) for part in schedule.start.split(":")[:2])
            except (ValueError, TypeError):
                continue
            start_dt = datetime.combine(now.date(), dt_time(hour, minute))
            end_dt = start_dt + timedelta(minutes=schedule.duration_min)
            if start_dt <= now < end_dt:
                return schedule
        return None

    def check_now(self, now: Optional[datetime] = None) -> Optional[dict]:
        now = now or self._clock()
        if not self.load():
            return None
        if self._manager is None:
            from protection.focus_manager import FocusManager

            self._manager = FocusManager.instance()
        if self._manager.is_active:
            return None

        schedule = self.due_schedule(now)
        if schedule is None:
            return None

        hour, minute = (int(part) for part in schedule.start.split(":")[:2])
        end_dt = datetime.combine(now.date(), dt_time(hour, minute)) + timedelta(
            minutes=schedule.duration_min
        )
        remaining_min = max(1, int(math.ceil((end_dt - now).total_seconds() / 60)))
        started = self._manager.start_focus(
            remaining_min,
            mode=schedule.mode,
            auto_started=True,
            schedule_id=schedule.id,
        )
        if started:
            self._mark_fired(schedule, now)
            logger.info(
                "[FOCUS_SCHEDULE] Started '%s' (%s) for %d min.",
                schedule.name,
                schedule.mode,
                remaining_min,
            )
            self.schedule_started.emit(schedule)
            return {"schedule": schedule, "minutes": remaining_min}
        return None
