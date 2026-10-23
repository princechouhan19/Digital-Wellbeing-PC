"""
debug_logger.py — Asynchronous Buffered Diagnostic Logger for Activity Tracking.

Provides permanent developer-mode diagnostic logging with zero performance impact
by queueing log entries to a background daemon writer thread.
"""

from __future__ import annotations

import atexit
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class DebugLogger:
    _instance: Optional[DebugLogger] = None
    _lock = threading.Lock()

    def __new__(cls) -> DebugLogger:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_logger()
            return cls._instance

    def _init_logger(self) -> None:
        self._log_path = Path.cwd() / "tracking_debug.log"
        self._queue: queue.Queue[Optional[dict[str, Any]]] = queue.Queue(maxsize=10000)
        self._running = True
        self._thread = threading.Thread(
            target=self._writer_loop,
            name="TrackingDebugLoggerThread",
            daemon=True,
        )
        self._thread.start()
        atexit.register(self.shutdown)

    def shutdown(self) -> None:
        if self._running:
            self._running = False
            try:
                self._queue.put_nowait(None)
                if self._thread.is_alive():
                    self._thread.join(timeout=2.0)
            except queue.Full:
                pass

    def _writer_loop(self) -> None:
        buffer: list[str] = []
        while self._running or not self._queue.empty():
            try:
                item = self._queue.get(timeout=0.5)
                if item is None:
                    break
                line = self._format_item(item)
                buffer.append(line)
                self._queue.task_done()
                # Drain available items up to 50 for buffered batch writing
                while len(buffer) < 50 and not self._queue.empty():
                    next_item = self._queue.get_nowait()
                    if next_item is None:
                        self._running = False
                        break
                    buffer.append(self._format_item(next_item))
                    self._queue.task_done()
            except queue.Empty:
                pass

            if buffer:
                try:
                    with open(self._log_path, "a", encoding="utf-8") as f:
                        f.write("\n".join(buffer) + "\n")
                    buffer.clear()
                except Exception:
                    buffer.clear()

    def _format_item(self, item: dict[str, Any]) -> str:
        ts = item.get("timestamp", datetime.now().isoformat())
        event_type = item.get("event_type", "EVENT")
        pid = item.get("pid", 0)
        process_name = item.get("process_name", "None")
        exe_path = item.get("exe_path", "")
        window_title = item.get("window_title", "")
        category = item.get("category", "Other")
        session_id = item.get("session_id", "N/A")
        start_time = item.get("start_time", "N/A")
        end_time = item.get("end_time", "N/A")
        is_idle = item.get("is_idle", False)
        is_fullscreen = item.get("is_fullscreen", False)
        reason = item.get("reason", "")
        game_reason = item.get("game_reason", "")
        launcher_reason = item.get("launcher_reason", "")

        return (
            f"[{ts}] | EVENT: {event_type} | PID: {pid} | Process: {process_name} | "
            f"Exe: {exe_path} | Title: {window_title!r} | Category: {category} | "
            f"SessionID: {session_id} | Start: {start_time} | End: {end_time} | "
            f"Idle: {is_idle} | Fullscreen: {is_fullscreen} | Reason: {reason} | "
            f"GameDetectReason: {game_reason} | LauncherDetectReason: {launcher_reason}"
        )

    def log_event(
        self,
        event_type: str,
        pid: int = 0,
        process_name: str = "None",
        exe_path: str = "",
        window_title: str = "",
        category: str = "Other",
        session_id: Optional[int] = None,
        start_time: str = "N/A",
        end_time: str = "N/A",
        is_idle: bool = False,
        is_fullscreen: bool = False,
        reason: str = "",
        game_reason: str = "",
        launcher_reason: str = "",
    ) -> None:
        if not self._running:
            return
        item = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "pid": pid,
            "process_name": process_name,
            "exe_path": exe_path,
            "window_title": window_title,
            "category": str(category),
            "session_id": session_id if session_id is not None else "N/A",
            "start_time": start_time,
            "end_time": end_time,
            "is_idle": is_idle,
            "is_fullscreen": is_fullscreen,
            "reason": reason,
            "game_reason": game_reason,
            "launcher_reason": launcher_reason,
        }
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            pass


debug_logger = DebugLogger()
