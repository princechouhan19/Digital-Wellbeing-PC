from __future__ import annotations

import json
import threading
from typing import Dict, Optional

from database.repository import Repository
from core.logger import logger

class LimitManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._limits: Dict[str, int] = {} # process_name (lower) -> limit_seconds
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            data = self._repo.get_setting("app_limits") or "{}"
            try:
                raw_limits = json.loads(data)
                self._limits = {}
                for k, v in raw_limits.items():
                    k = k.lower()
                    if isinstance(v, int):
                        # Migrate old int schema
                        self._limits[k] = {
                            "limit_seconds": v,
                            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
                            "notifications": [15, 10, 5, 1],
                            "on_expire": "lock"
                        }
                    else:
                        self._limits[k] = v
            except json.JSONDecodeError:
                logger.error("Failed to parse app_limits from DB")
                self._limits = {}

    def _save(self) -> None:
        try:
            data = json.dumps(self._limits)
            self._repo.set_setting("app_limits", data)
        except Exception as e:
            logger.error(f"Failed to save app_limits: {e}")

    def set_limit(self, process_name: str, limit_seconds: Optional[int]) -> None:
        """Backward compatibility: Set a basic limit in seconds for a process."""
        if limit_seconds is None or limit_seconds <= 0:
            self.set_limit_rule(process_name, None)
        else:
            self.set_limit_rule(process_name, {
                "limit_seconds": limit_seconds,
                "repeat_days": [0, 1, 2, 3, 4, 5, 6],
                "notifications": [15, 10, 5, 1],
                "on_expire": "lock"
            })

    def set_limit_rule(self, process_name: str, rule: Optional[dict]) -> None:
        """Set a complex limit rule for a process. Use None to remove."""
        process_name = process_name.lower()
        with self._lock:
            if not rule or rule.get("limit_seconds") is None or rule.get("limit_seconds") <= 0:
                if process_name in self._limits:
                    del self._limits[process_name]
            else:
                self._limits[process_name] = rule
            self._save()
            logger.info(f"Set limit rule for {process_name}: {rule}")

    def get_limit(self, process_name: str) -> Optional[int]:
        """Return the limit in seconds IF active today, else None."""
        process_name = process_name.lower()
        with self._lock:
            rule = self._limits.get(process_name)
            if not rule:
                return None
            
            # Check repeat days
            import datetime
            today = datetime.datetime.today().weekday()
            if today not in rule.get("repeat_days", [0, 1, 2, 3, 4, 5, 6]):
                return None
                
            return rule.get("limit_seconds")

    def get_limit_rule(self, process_name: str) -> Optional[dict]:
        """Return the raw limit rule dictionary."""
        process_name = process_name.lower()
        with self._lock:
            return self._limits.get(process_name)

    def get_all_limits(self) -> Dict[str, int]:
        with self._lock:
            return self._limits.copy()
