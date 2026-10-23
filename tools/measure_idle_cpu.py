"""
measure_idle_cpu.py — Measure real idle CPU of the tracking engine.

    .\\venv\\Scripts\\python.exe tools\\measure_idle_cpu.py --seconds 20
    .\\venv\\Scripts\\python.exe tools\\measure_idle_cpu.py --seconds 20 --include-media

The default isolates the tracking loop (media/session threads disabled). With
``--include-media`` the full headless service is measured, including the WinRT
media detector. Run it while the desktop is idle for meaningful numbers.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("DW_TEST_MODE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psutil

import tracker.manager as manager_mod


class _NullEngine:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    @property
    def is_playing(self) -> bool:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--include-media", action="store_true")
    args = parser.parse_args()

    if not args.include_media:
        manager_mod.MediaDetectionEngine = _NullEngine
        manager_mod.SessionMonitor = _NullEngine

    try:
        manager = manager_mod.TrackingManager()
        manager.start()
    except Exception as exc:
        print(f"Failed to start tracker: {exc}")
        return 1

    time.sleep(2)  # let schema/index work settle
    proc = psutil.Process()
    t0 = time.perf_counter()
    c0 = proc.cpu_times()
    time.sleep(args.seconds)
    c1 = proc.cpu_times()
    elapsed = time.perf_counter() - t0
    cpu = (c1.user - c0.user) + (c1.system - c0.system)
    print(f"elapsed={elapsed:.1f}s cpu={cpu*1000:.1f}ms avg={cpu/elapsed*100:.4f}% of one core")
    print("stats:", manager.get_performance_stats())
    manager.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
