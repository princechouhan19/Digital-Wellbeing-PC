"""
event_monitor.py — Real-time Keyboard Lock Monitor (Caps Lock, Num Lock) for Dynamic Island.
"""
from __future__ import annotations

import ctypes
import time
from PySide6.QtCore import QThread, Signal


class KeyLockMonitor(QThread):
    lock_changed = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.last_caps = self.get_caps_lock()
        self.last_num = self.get_num_lock()

    @staticmethod
    def get_caps_lock() -> bool:
        # VK_CAPITAL = 0x14
        try:
            return (ctypes.windll.user32.GetKeyState(0x14) & 1) != 0
        except Exception:
            return False

    @staticmethod
    def get_num_lock() -> bool:
        # VK_NUMLOCK = 0x90
        try:
            return (ctypes.windll.user32.GetKeyState(0x90) & 1) != 0
        except Exception:
            return False

    def run(self):
        while self._is_running:
            caps = self.get_caps_lock()
            if caps != self.last_caps:
                self.last_caps = caps
                self.lock_changed.emit("Caps Lock", caps)

            num = self.get_num_lock()
            if num != self.last_num:
                self.last_num = num
                self.lock_changed.emit("Num Lock", num)

            time.sleep(0.04)

    def stop(self):
        self._is_running = False
        self.wait(500)
