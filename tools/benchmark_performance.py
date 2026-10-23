"""
benchmark_performance.py — Reproducible performance measurements for v4.2.

Run with the project virtualenv:
    .\\venv\\Scripts\\python.exe tools\\benchmark_performance.py

It measures the startup path, hot-path microbenchmarks, SQLite analytics on a
synthetic multi-year database, and a simulated tracking tick. Numbers are
printed, not asserted, so the script is safe to run on any machine.
"""
from __future__ import annotations

import os
import statistics
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DW_TEST_MODE", "1")
os.environ.setdefault("DW_DISABLE_WINEVENT_HOOK", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psutil
from PySide6.QtWidgets import QApplication

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from tracker.browser_domain import (
    extract_domain_from_title,
    get_active_browser_domain,
    get_uia_cache_stats,
    reset_uia_cache,
)
from tracker.foreground import ForegroundApp, get_foreground_app
from tracker.idle import get_idle_seconds
from protection.adult_content_shield import AdultContentClassifier

APP = QApplication.instance() or QApplication([])
ROOT = Path(__file__).resolve().parent.parent


def _rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1024 / 1024


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def bench_ms(fn, iterations: int = 300, warmup: int = 10) -> float:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples) * 1000


# ── 1. Startup ───────────────────────────────────────────────────────────────
section("Startup / lazy pages")
from tracker.manager import TrackingManager
from ui.main_window import MainWindow

t0 = time.perf_counter()
tracker = TrackingManager()
t_manager = time.perf_counter() - t0
t0 = time.perf_counter()
win = MainWindow(tracker=tracker)
t_window = time.perf_counter() - t0
print(f"TrackingManager          : {t_manager*1000:8.1f} ms")
print(f"MainWindow (landing only): {t_window*1000:8.1f} ms")
print(f"pages instantiated       : {sorted(win._pages)}")
print(f"stack slots / widgets    : {win._stack.count()} / {len(APP.allWidgets())}")
print(f"process RSS              : {_rss_mb():8.1f} MB")
assert win.get_loaded_page("_settings_page") is None, "settings page should be lazy"

t0 = time.perf_counter()
win._navigate(8)
t_settings = time.perf_counter() - t0
print(f"first Settings navigation: {t_settings*1000:8.1f} ms")
win._navigate(0)

# ── 2. Hot paths ─────────────────────────────────────────────────────────────
section("Tracking hot paths (median)")
print(f"get_foreground_app       : {bench_ms(get_foreground_app):8.3f} ms")
print(f"get_idle_seconds         : {bench_ms(get_idle_seconds):8.3f} ms")
print(f"title -> domain (cached) : {bench_ms(lambda: extract_domain_from_title('YouTube - Google Chrome'), 2000):8.4f} ms")
print(f"adult classify (cached)  : {bench_ms(lambda: AdultContentClassifier.is_adult_title('Some harmless page - Google Chrome'), 2000):8.4f} ms")

reset_uia_cache()
_uia_calls = []
import tracker.browser_domain as bd

bd._UIA_SYNC_MODE = True
bd._query_uia_domain = lambda hwnd: _uia_calls.append(hwnd) or "example.com"
for _ in range(100):
    get_active_browser_domain("chrome.exe", "Unrecognized dashboard title", hwnd=1234)
print(f"UIA queries / 100 calls  : {len(_uia_calls)}  stats={get_uia_cache_stats()}")
bd._UIA_SYNC_MODE = False

# ── 3. Simulated tracking tick ───────────────────────────────────────────────
section("Tracking tick CPU (simulated, no DB writes)")
from tracker import manager as manager_mod
from protection.adult_content_shield import AdultContentShield

fake_app = ForegroundApp(
    process_name="chrome.exe",
    exe_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
    pid=4242,
    window_title="Some harmless page - Google Chrome",
    hwnd=123456,
    url="example.com",
    is_fullscreen=False,
)
manager_mod.get_foreground_app = lambda last=None: fake_app
manager_mod.get_idle_seconds = lambda: 0.0

tracker._current_app = fake_app
tracker._current_is_idle = False
tracker._current_category = __import__("core.constants", fromlist=["AppCategory"]).AppCategory.BROWSER
tracker._session_start = None
tracker._current_session_id = None
tracker._current_website_url = fake_app.url
tracker._current_website_session_id = None
tracker._watcher._available = True  # pretend hooks are installed
tracker._on_active_tick_callbacks.clear()

shield = AdultContentShield.instance()


def _callback(process_name, delta, url="", title="", hwnd=0):
    shield.inspect(process_name, title, url, hwnd)


tracker._on_active_tick_callbacks.append(_callback)


def tick(refresh: bool, n: int = 1500) -> float:
    samples = []
    for _ in range(n):
        now = time.monotonic()
        tracker._last_fg_query_mono = 0.0 if refresh else now
        tracker._fg_dirty = False
        tracker._last_tick_time = datetime.now()
        t0 = time.perf_counter()
        tracker._tick(1.0)
        samples.append(time.perf_counter() - t0)
    return statistics.median(samples) * 1000


tick_refresh = tick(True, 200)       # warm caches
tick_norefresh = tick(False, 200)
tick_refresh = tick(True)
tick_norefresh = tick(False)
print(f"tick WITH fresh foreground : {tick_refresh:8.4f} ms")
print(f"tick WITHOUT foreground    : {tick_norefresh:8.4f} ms")
# Legacy: 2 Hz, full query every tick.
legacy_cpu = tick_refresh / 500.0 * 100.0
# v4.2: 2 s loop, foreground re-read about every 2-3 ticks.
event_cpu = (tick_norefresh + (tick_refresh - tick_norefresh) / 2.5) / 2000.0 * 100.0
print(f"estimated legacy CPU       : {legacy_cpu:8.3f} % of one core")
print(f"estimated event-driven CPU : {event_cpu:8.3f} % of one core")
print(f"tracker counters           : {tracker.get_performance_stats()}")

# ── 4. SQLite analytics ──────────────────────────────────────────────────────
section("SQLite analytics (120k app sessions / 60k website sessions)")
tmp = Path(tempfile.gettempdir()) / "dw_bench_perf.db"
for suffix in ("", "-wal", "-shm"):
    candidate = Path(str(tmp) + suffix)
    if candidate.exists():
        candidate.unlink()
Repository.set_db_path_override(tmp)
repo = Repository()
repo.close()

import sqlite3

conn = sqlite3.connect(tmp)
base = datetime(2024, 1, 1, 8, 0, 0)
apps = ["chrome.exe", "code.exe", "discord.exe", "explorer.exe", "steam.exe"]
rows = [
    (
        apps[i % len(apps)],
        "C:/x.exe",
        "Title",
        (base + timedelta(minutes=i * 2)).isoformat(),
        (base + timedelta(minutes=i * 2, seconds=90)).isoformat(),
        90.0,
        "Other",
        0,
        1,
    )
    for i in range(120_000)
]
conn.executemany(
    "INSERT INTO app_sessions (process_name, exe_path, window_title, start_time, end_time, duration_s, category, is_idle, was_closed) VALUES (?,?,?,?,?,?,?,?,?)",
    rows,
)
wrows = [
    (
        "youtube.com",
        "chrome.exe",
        (base + timedelta(minutes=i * 3)).isoformat(),
        (base + timedelta(minutes=i * 3, seconds=60)).isoformat(),
        60.0,
        1,
    )
    for i in range(60_000)
]
conn.executemany(
    "INSERT INTO website_sessions (domain, browser_process, start_time, end_time, duration_s, was_closed) VALUES (?,?,?,?,?,?)",
    wrows,
)
conn.commit()
conn.close()
repo.close()  # reconnect so mmap/pragmas see the populated file

engine = AnalyticsEngine()
d0, d1 = date(2024, 1, 1), date(2024, 12, 31)


def db_bench(label: str, fn) -> None:
    fn()
    samples = []
    for _ in range(3):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    print(f"{label:26s}: {statistics.median(samples)*1000:8.1f} ms")


db_bench("top apps (year)", lambda: repo.get_top_apps_for_range(d0, d1, 20))
db_bench("category breakdown", lambda: repo.get_category_breakdown_for_range(d0, d1))
db_bench("daily totals", lambda: repo.get_daily_totals_for_range(d0, d1))
db_bench("top websites", lambda: repo.get_top_websites_for_range(d0, d1, None, 50))
db_bench("app detail stats", lambda: repo.get_app_detail_stats("chrome.exe"))
db_bench("today summary", lambda: engine.get_today_summary())
print(f"database size            : {tmp.stat().st_size/1024/1024:8.2f} MB")
repo.close()
Repository.set_db_path_override(None)
win.close()
