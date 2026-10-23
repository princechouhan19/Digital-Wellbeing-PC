from __future__ import annotations

import threading
from datetime import date
from typing import Dict

from database.repository import Repository
from core.logger import logger

class TimerEngine:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._timers: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._current_date = date.today()
        self.sync_from_db()

    def sync_from_db(self) -> None:
        """Fetch today's active time for all applications from the database."""
        with self._lock:
            self._timers.clear()
            self._current_date = date.today()
            # We fetch all usage for today.
            top_apps = self._repo.get_top_apps_for_range(self._current_date, self._current_date, limit=1000)
            for app in top_apps:
                process_name = app["process_name"].lower()
                self._timers[process_name] = app["total_s"]
            logger.info(f"TimerEngine synced {len(self._timers)} applications from DB for {self._current_date}")

    def add_time(self, process_name: str, delta_s: float) -> None:
        """Increment the timer for the given application."""
        if delta_s <= 0:
            return
            
        process_name = process_name.lower()
        today = date.today()
        
        with self._lock:
            if today != self._current_date:
                # Midnight reset
                logger.info(f"TimerEngine detected date change from {self._current_date} to {today}. Resetting timers.")
                self._current_date = today
                self._timers.clear()
                
            current = self._timers.get(process_name, 0.0)
            self._timers[process_name] = current + delta_s

    def get_time(self, process_name: str) -> float:
        """Return today's active time for the application in seconds."""
        process_name = process_name.lower()
        with self._lock:
            today = date.today()
            if self._current_date != today:
                self._current_date = today
                self._timers.clear()
                return 0.0
            return self._timers.get(process_name, 0.0)

    def get_all_times(self) -> Dict[str, float]:
        with self._lock:
            today = date.today()
            if self._current_date != today:
                self._current_date = today
                self._timers.clear()
            return self._timers.copy()
