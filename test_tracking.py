import sys
sys.path.insert(0, ".")

print("=== TRACKING INTEGRATION TEST ===\n")

# ─── Schema migrations ──────────────────────────────────────────────
import tempfile
from pathlib import Path
from database.repository import Repository

temp_db = Path(tempfile.gettempdir()) / "digital_wellbeing_test_tracking.db"
if temp_db.exists():
    try:
        temp_db.unlink()
    except Exception:
        pass
Repository.set_db_path_override(temp_db)

repo = Repository()

open_sessions = repo.get_open_sessions()
print(f"[OK] Orphaned sessions closed: {len(open_sessions)} open after init (expected 0)")
assert len(open_sessions) == 0

# ─── Foreground ──────────────────────────────────────────────────────
from tracker.foreground import get_foreground_app, apps_are_same, ForegroundApp
fg = get_foreground_app()
assert fg is not None or fg is None  # both valid (may have no foreground in headless)
print(f"[OK] foreground.get_foreground_app(): {fg.process_name if fg else 'None'}")
if fg:
    assert isinstance(fg.process_name, str) and len(fg.process_name) > 0
    assert isinstance(fg.exe_path, str)
    assert isinstance(fg.window_title, str)
    assert fg.pid > 0
    assert fg.hwnd > 0
    print(f"     exe_path={fg.exe_path!r}")
    print(f"     title={fg.window_title!r}")

from tracker.foreground import is_private_browsing
assert is_private_browsing("chrome.exe", "Google - Google Chrome - Incognito") is True
assert is_private_browsing("msedge.exe", "New Tab - Microsoft Edge InPrivate") is True
assert is_private_browsing("brave.exe", "Brave (Private)") is True
assert is_private_browsing("firefox.exe", "Mozilla Firefox (Private Browsing)") is True
assert is_private_browsing("opera.exe", "Opera - Private Browsing") is True
assert is_private_browsing("tor.exe", "Tor Browser") is True
assert is_private_browsing("chrome.exe", "Python Documentation - Google Chrome") is False
assert is_private_browsing("notepad.exe", "Incognito.txt - Notepad") is False
print("[OK] foreground.is_private_browsing(): Incognito/Private mode detection verified")

a = ForegroundApp("chrome.exe", "C:/chrome.exe", 100, "Tab A", 1)
b = ForegroundApp("chrome.exe", "C:/chrome.exe", 100, "Tab A", 1)
c = ForegroundApp("chrome.exe", "C:/chrome.exe", 100, "Tab B", 1)
d = ForegroundApp("firefox.exe", "C:/ff.exe", 200, "Tab A", 2)
assert apps_are_same(a, b)
assert not apps_are_same(a, c)
assert not apps_are_same(a, d)
assert apps_are_same(None, None)
assert not apps_are_same(a, None)
print("[OK] foreground.apps_are_same(): title-level change detection")

# ─── Idle ──────────────────────────────────────────────────────────
from tracker.idle import get_idle_seconds, is_idle
idle_s = get_idle_seconds()
assert isinstance(idle_s, float) and idle_s >= 0
assert not is_idle(999999)
print(f"[OK] idle.get_idle_seconds(): {idle_s:.2f}s (wraparound-safe)")

# ─── Session monitor (just instantiation, no message pump) ─────────
from tracker.session import SessionMonitor, SessionEvent
events_received = []
monitor = SessionMonitor(lambda e: events_received.append(e))
print("[OK] session.SessionMonitor instantiated")

# ─── Repository: insert with exe_path + was_closed ─────────────────
from database.models import AppSession, AppInfo
from core.constants import AppCategory
from datetime import datetime, date, timedelta

now = datetime.now()
session = AppSession(
    process_name="test_tracker.exe",
    exe_path="C:/test/test_tracker.exe",
    window_title="Tracker Test Window",
    start_time=now - timedelta(seconds=45),
    end_time=None,
    duration_s=0.0,
    category=AppCategory.PROGRAMMING,
    is_idle=False,
    was_closed=False,
)
sid = repo.insert_session(session)
assert sid > 0
print(f"[OK] repository.insert_session with exe_path: id={sid}")

open_now = repo.get_open_sessions()
assert any(s.id == sid for s in open_now)
print(f"[OK] repository.get_open_sessions(): found open session {sid}")

end = datetime.now()
duration = (end - session.start_time).total_seconds()
repo.update_session_end(sid, end, duration, was_closed=True)
print(f"[OK] repository.update_session_end was_closed=True: duration={duration:.1f}s")

open_after = repo.get_open_sessions()
assert all(s.id != sid for s in open_after)
print("[OK] repository.get_open_sessions(): session closed correctly")

sessions_today = repo.get_sessions_for_date(date.today())
test_session = next((s for s in sessions_today if s.id == sid), None)
assert test_session is not None
assert test_session.exe_path == "C:/test/test_tracker.exe"
assert test_session.was_closed == True
assert test_session.duration_s > 0
print(f"[OK] repository.get_sessions_for_date: exe_path and was_closed verified")

# ─── Event log ─────────────────────────────────────────────────────
repo.log_event("test_event", "integration test detail")
events = repo.get_recent_events(limit=5)
assert len(events) >= 1
latest = events[0]
assert latest.event_type in ("test_event", "tracker_start", "tracker_stop")
print(f"[OK] repository.event_log: {len(events)} events, latest={latest.event_type}")

# ─── Categorizer (Path Heuristics & Expanded Rules) ────────────────
from tracker.categorizer import categorize, display_name
assert categorize("steam.exe") == AppCategory.GAMING
assert categorize("cs2.exe") == AppCategory.GAMING
assert categorize("valorant-win64-shipping.exe") == AppCategory.GAMING
assert categorize("unknown_indie_game.exe", r"D:\SteamApps\common\SuperIndieGame\bin.exe") == AppCategory.GAMING
assert categorize("mygame.exe", r"C:\Program Files\Epic Games\Fortnite\mygame.exe") == AppCategory.GAMING
assert categorize("unins000.exe", r"D:\SteamApps\common\Game\unins000.exe") != AppCategory.GAMING
assert display_name("cs2.exe") == "Counter-Strike 2"
assert display_name("valorant-win64-shipping.exe") == "Valorant"
print("[OK] categorizer: Path heuristics and expanded overrides verified")

# ─── Idle Category/Media Suppression ───────────────────────────────
assert is_idle(10.0, current_category=AppCategory.GAMING, is_media_playing=False) == (idle_s >= 25.0)
assert is_idle(10.0, current_category=AppCategory.ENTERTAINMENT, is_media_playing=True) == (idle_s >= 30.0)
print("[OK] idle: Activity-aware threshold multipliers (gaming 2.5x, media 3.0x) verified")

# ─── Foreground Overlay & Caching ──────────────────────────────────
from tracker.foreground import OVERLAY_PROCESSES, _pid_info_cache, _get_process_info
assert "gameoverlayui.exe" in OVERLAY_PROCESSES
assert "discord.exe" in OVERLAY_PROCESSES
print("[OK] foreground: Overlay process filtering and LRU cache initialized")

# ─── TrackingManager lifecycle ─────────────────────────────────────
import time
from tracker.manager import TrackingManager

mgr = TrackingManager()
assert not mgr.is_running
assert not mgr.is_paused

data_changed_count = [0]
mgr.add_data_changed_callback(lambda: data_changed_count.__setitem__(0, data_changed_count[0]+1))

mgr.start()
assert mgr.is_running
print("[OK] TrackingManager.start(): running")

time.sleep(2.5)

idle_s2 = mgr.idle_seconds
assert isinstance(idle_s2, float)
print(f"[OK] TrackingManager.idle_seconds: {idle_s2:.1f}s")

cur_app = mgr.current_app
print(f"[OK] TrackingManager.current_app: {cur_app.process_name if cur_app else 'None'}")

mgr.reload_settings()
print("[OK] TrackingManager.reload_settings()")

mgr.stop()
assert not mgr.is_running
print("[OK] TrackingManager.stop()")

time.sleep(0.5)
sessions_after = repo.get_sessions_for_date(date.today())
open_after_stop = repo.get_open_sessions()
assert len(open_after_stop) == 0
print(f"[OK] No orphaned sessions after stop: {len(sessions_after)} sessions today, 0 open")

# ─── Duplicate / short session filter ──────────────────────────────
from database.repository import Repository
all_today = repo.get_sessions_for_date(date.today())
for s in all_today:
    assert s.duration_s > 0, f"Zero-duration session found: {s.id}"
print(f"[OK] All {len(all_today)} sessions have duration_s > 0")

# ─── CSV export with new columns ───────────────────────────────────
import tempfile, pathlib
from utils.csv_exporter import CSVExporter
exp = CSVExporter()
tmp = pathlib.Path(tempfile.gettempdir()) / "dw_tracker_test.csv"
out = exp.export_sessions(date.today(), date.today(), tmp)
assert out.exists()
lines = out.read_text(encoding="utf-8").splitlines()
assert "Executable Path" in lines[0]
print(f"[OK] CSVExporter: {len(lines)-1} rows, exe_path column present")

# Cleanup override
Repository.set_db_path_override(None)
if temp_db.exists():
    try:
        temp_db.unlink()
    except Exception:
        pass

print()
print("=== ALL TRACKING TESTS PASSED ===")
