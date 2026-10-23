import sys
sys.path.insert(0, ".")

print("=== TESTING ALL MODULES ===")

# ─── Core ──────────────────────────────────────────────
from core.constants import AppCategory, CATEGORY_COLORS, APP_NAME, APP_VERSION
assert APP_NAME == "Digital Wellbeing"
assert len(list(AppCategory)) == 12
assert len(CATEGORY_COLORS) == 12
print(f"[OK] core.constants — {len(list(AppCategory))} categories")

from core.logger import logger, get_log_path
assert get_log_path().parent.exists()
print(f"[OK] core.logger — log at {get_log_path()}")

# ─── Database ──────────────────────────────────────────
import tempfile
from pathlib import Path
from database.repository import Repository

temp_db = Path(tempfile.gettempdir()) / "digital_wellbeing_test_all.db"
if temp_db.exists():
    try:
        temp_db.unlink()
    except Exception:
        pass
Repository.set_db_path_override(temp_db)

from database.models import AppSession, AppInfo
from datetime import datetime, date

repo = Repository()

session = AppSession(
    process_name="chrome.exe",
    window_title="GitHub - Test",
    start_time=datetime.now(),
    end_time=datetime.now(),
    duration_s=120.0,
    category=AppCategory.BROWSER,
    is_idle=False,
)
sid = repo.insert_session(session)
assert sid > 0
print(f"[OK] database.repository.insert_session — session_id={sid}")

sessions = repo.get_sessions_for_date(date.today())
assert any(s.process_name == "chrome.exe" for s in sessions)
print(f"[OK] database.repository.get_sessions_for_date — {len(sessions)} sessions today")

top = repo.get_top_apps_for_range(date.today(), date.today())
assert len(top) >= 1
print(f"[OK] database.repository.get_top_apps_for_range — {len(top)} apps")

breakdown = repo.get_category_breakdown_for_range(date.today(), date.today())
assert len(breakdown) >= 1
print(f"[OK] database.repository.get_category_breakdown — {len(breakdown)} categories")

hourly_db = repo.get_hourly_breakdown_for_date(date.today())
assert isinstance(hourly_db, list)
print(f"[OK] database.repository.hourly_breakdown — {len(hourly_db)} hours with data")

# ─── Settings ──────────────────────────────────────────
from settings.manager import SettingsManager
sm = SettingsManager()
sm.set_int("idle_threshold_s", 120)
assert sm.get_int("idle_threshold_s") == 120
sm.set_int("idle_threshold_s", 300)
sm.set_bool("notifications_enabled", True)
assert sm.get_bool("notifications_enabled") == True
print("[OK] settings.manager — read/write verified")

# ─── Tracker / Categorizer ─────────────────────────────
from tracker.categorizer import categorize, display_name
tests = [
    ("chrome.exe", AppCategory.BROWSER),
    ("firefox.exe", AppCategory.BROWSER),
    ("code.exe", AppCategory.PROGRAMMING),
    ("pycharm64.exe", AppCategory.PROGRAMMING),
    ("steam.exe", AppCategory.GAMING),
    ("discord.exe", AppCategory.COMMUNICATION),
    ("teams.exe", AppCategory.COMMUNICATION),
    ("slack.exe", AppCategory.COMMUNICATION),
    ("excel.exe", AppCategory.PRODUCTIVITY),
    ("vlc.exe", AppCategory.ENTERTAINMENT),
    ("explorer.exe", AppCategory.SYSTEM),
]
for exe, expected_cat in tests:
    result = categorize(exe)
    assert result == expected_cat, f"{exe}: expected {expected_cat}, got {result}"
print(f"[OK] tracker.categorizer — {len(tests)} categorizations correct")

assert display_name("chrome.exe") == "Google Chrome"
assert display_name("code.exe") == "Visual Studio Code"
assert display_name("pycharm64.exe") == "PyCharm"
print("[OK] tracker.categorizer.display_name — overrides working")

from tracker.idle import get_idle_seconds
idle_s = get_idle_seconds()
assert isinstance(idle_s, float) and idle_s >= 0
print(f"[OK] tracker.idle — idle for {idle_s:.1f}s")

from tracker.foreground import get_foreground_app
fg = get_foreground_app()
fg_name = fg.process_name if fg else "None"
print(f"[OK] tracker.foreground — foreground: {fg_name}")

# ─── Analytics ─────────────────────────────────────────
from analytics.engine import AnalyticsEngine
engine = AnalyticsEngine()
today_sum = engine.get_today_summary()
assert today_sum.active_time_s >= 120
assert len(today_sum.top_apps) >= 1
print(f"[OK] analytics.engine.get_today_summary — active={engine.format_duration(today_sum.active_time_s)}")

week_sum = engine.get_week_summary()
assert week_sum is not None
print(f"[OK] analytics.engine.get_week_summary — avg={engine.format_duration(week_sum.average_daily_s)}")

hourly_chart = engine.get_hourly_chart_data(date.today())
assert len(hourly_chart) == 24
assert all("hour" in h and "total_s" in h for h in hourly_chart)
print("[OK] analytics.engine.get_hourly_chart_data — 24 hours")

from datetime import timedelta
daily_pts = engine.get_daily_chart_data(date.today() - timedelta(days=6), date.today())
assert len(daily_pts) == 7
print("[OK] analytics.engine.get_daily_chart_data — 7 points")

# ─── CSV Export ────────────────────────────────────────
from utils.csv_exporter import CSVExporter
import tempfile, pathlib
exporter = CSVExporter()
tmp = pathlib.Path(tempfile.gettempdir()) / "dw_test.csv"
out = exporter.export_sessions(date.today(), date.today(), tmp)
assert out.exists()
lines = out.read_text(encoding="utf-8").splitlines()
assert len(lines) >= 2
content = out.read_text(encoding="utf-8")
assert "chrome.exe" in content
print(f"[OK] utils.csv_exporter — exported {len(lines)-1} rows")

# ─── Autostart ─────────────────────────────────────────
from utils.autostart import is_autostart_enabled
result = is_autostart_enabled()
assert isinstance(result, bool)
print(f"[OK] utils.autostart.is_autostart_enabled — {result}")

# ─── Windows Utils ─────────────────────────────────────
from utils.win_utils import get_windows_version, is_admin
ver = get_windows_version()
assert len(ver) == 3 and ver[0] >= 10
print(f"[OK] utils.win_utils — Windows {ver[0]}.{ver[1]} build {ver[2]}, admin={is_admin()}")

# ─── Longest Session ───────────────────────────────────
longest = repo.get_longest_session_for_range(date.today(), date.today())
assert longest is not None
print(f"[OK] repository.get_longest_session — {longest.process_name} ({longest.duration_formatted})")

# ─── Search ────────────────────────────────────────────
search_results = repo.search_sessions("chrome", None, date.today(), date.today())
assert len(search_results) >= 1
print(f"[OK] repository.search_sessions — {len(search_results)} result(s) for 'chrome'")
# Cleanup override
Repository.set_db_path_override(None)
if temp_db.exists():
    try:
        temp_db.unlink()
    except Exception:
        pass

print()
print("=== ALL TESTS PASSED ===")
