"""
perf_monitor.py — Real-time CPU, RAM, Disk, and Network Performance Monitor for Dynamic Island.
"""
from __future__ import annotations

import time
import psutil
from PySide6.QtCore import QThread, Signal


class PerfMonitor(QThread):
    metrics_updated = Signal(dict)

    def __init__(self, interval_sec: float = 1.0, parent=None):
        super().__init__(parent)
        self.interval_sec = interval_sec
        self._is_running = True
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def run(self):
        try:
            last_net = psutil.net_io_counters()
        except Exception:
            last_net = None
        last_time = time.time()

        while self._is_running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                try:
                    disk = psutil.disk_usage("C:\\").percent
                except Exception:
                    disk = 0.0

                cur_time = time.time()
                dt = cur_time - last_time
                down = 0.0
                up = 0.0
                if last_net:
                    try:
                        cur_net = psutil.net_io_counters()
                        down = (cur_net.bytes_recv - last_net.bytes_recv) / dt if dt > 0 else 0.0
                        up = (cur_net.bytes_sent - last_net.bytes_sent) / dt if dt > 0 else 0.0
                        last_net = cur_net
                    except Exception:
                        pass
                last_time = cur_time

                data = {
                    "cpu": cpu,
                    "ram": ram,
                    "disk": disk,
                    "down": down,
                    "up": up,
                }
                self.metrics_updated.emit(data)
            except Exception:
                pass

            for _ in range(int(self.interval_sec * 10)):
                if not self._is_running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._is_running = False
        self.wait(500)
