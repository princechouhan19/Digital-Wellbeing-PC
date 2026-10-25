"""
attention_nudge.py — Gentle in-the-moment fragmentation interruption.

Checks once a minute for a burst of application switches in the last 30
minutes. When the threshold is crossed it emits a single nudge with a
one-click 10-minute Focus reset. Cooldown and focus-active checks keep it from
becoming noise.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger

DEFAULT_WINDOW_MINUTES = 30
DEFAULT_THRESHOLD = 12
DEFAULT_COOLDOWN_MINUTES = 90
STARTUP_GRACE_SECONDS = 300


class AttentionNudgeController(QObject):
    nudge_ready = Signal(int)  # switches in window

    def __init__(
        self,
        engine=None,
        manager=None,
        settings=None,
        clock=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._manager = manager
        self._settings = settings
        self._clock = clock or datetime.now
        self._last_nudge = 0.0
        self._started_at = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.check_now)

    def _get_engine(self):
        if self._engine is None:
            from analytics.engine import AnalyticsEngine

            self._engine = AnalyticsEngine()
        return self._engine

    def _get_manager(self):
        if self._manager is None:
            from protection.focus_manager import FocusManager

            self._manager = FocusManager.instance()
        return self._manager

    def _get_settings(self):
        if self._settings is None:
            from settings.manager import SettingsManager

            self._settings = SettingsManager()
        return self._settings

    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def check_now(self, now: Optional[datetime] = None) -> bool:
        if time.monotonic() - self._started_at < STARTUP_GRACE_SECONDS:
            return False
        try:
            if not self._get_settings().get_bool("fragmentation_nudge_enabled", True):
                return False
            if self._get_manager().is_active:
                return False
            if time.time() - self._last_nudge < DEFAULT_COOLDOWN_MINUTES * 60:
                return False
            from tracker.idle import get_idle_seconds

            if get_idle_seconds() > 120:
                return False
            switches = self._get_engine().get_switch_count_since(
                DEFAULT_WINDOW_MINUTES, now or self._clock()
            )
            if switches < DEFAULT_THRESHOLD:
                return False
            self._last_nudge = time.time()
            logger.info("[ATTENTION] Fragmentation nudge: %d switches in 30 min.", switches)
            self.nudge_ready.emit(switches)
            return True
        except Exception as exc:
            logger.debug("[ATTENTION] Nudge check failed: %s", exc)
            return False
