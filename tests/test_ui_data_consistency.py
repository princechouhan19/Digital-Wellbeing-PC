"""
test_ui_data_consistency.py — Tests for Final UI + Data Consistency Fix Pass:
1. SleepGuard single warning dialog & safety recheck.
2. Category icon styling (no colored square tile backgrounds).
3. Usage & Trends date/range data consistency (Today matches Home, 7D, 30D).
4. Hourly Screen Time Intensity chart & empty states.
"""
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtWidgets import QApplication

from analytics.engine import AnalyticsEngine
from core.constants import AppCategory
from tracker.sleepguard import SleepGuardController
from ui.pages.activity import ActivityPage
from ui.widgets.charts import HourlyIntensityChart, DailyScreenTimeChart
from ui.widgets.countdown_dialog import ShutdownCountdownDialog
from ui.widgets.simple_category_row import ClickableCategoryCard
from utils.shutdown import ShutdownManager


@pytest.fixture(autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ============================================================================
# 1. SLEEPGUARD SINGLE WARNING DIALOG TESTS
# ============================================================================

@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows notification-state APIs")
def test_sleepguard_single_warning_dialog(monkeypatch):
    """Confirm only one dialog (ShutdownCountdownDialog) is created and no native MessageBox pops."""
    from ui.main_window import MainWindow
    from tracker.manager import TrackingManager
    
    # Mock subprocess to prevent any system commands
    monkeypatch.setattr("subprocess.run", MagicMock())
    
    # Track any ctypes MessageBoxW calls
    mock_msgbox = MagicMock()
    monkeypatch.setattr("ctypes.windll.user32.MessageBoxW", mock_msgbox, raising=False)
    
    mock_tracker = MagicMock()
    mock_tracker.get_debug_state.return_value = {
        "process_name": "notepad.exe",
        "category": "Utilities",
        "duration_s": "10s",
        "debug_enabled": False,
        "is_idle": False,
    }
    mock_tracker.get_current_state.return_value = {
        "process_name": "notepad.exe",
        "category": "Utilities",
        "duration_s": 10.0,
        "is_idle": False,
    }
    win = MainWindow(tracker=mock_tracker)
    win.show()
    
    # Trigger SleepGuard warning
    win._show_shutdown_warning_dialog(countdown_s=10, action="shutdown")
    
    # Find all visible top-level ShutdownCountdownDialogs
    top_dialogs = [w for w in QApplication.topLevelWidgets() if isinstance(w, ShutdownCountdownDialog) and w.isVisible()]
    assert len(top_dialogs) == 1, "Expected exactly one visible ShutdownCountdownDialog"
    
    dialog = top_dialogs[0]
    assert dialog.isVisible(), "Dialog should be visible"
    assert dialog._remaining_s == 10
    assert dialog._action == "shutdown"
    
    # Ensure no native MessageBoxW was called
    assert mock_msgbox.call_count == 0, "Native MessageBoxW should NOT be called"
    
    # Test cancellation
    dialog._on_cancel()
    assert dialog._cancelled is True
    assert not dialog.isVisible() or not dialog._timer.isActive()
    
    win.close()
    dialog.close()


def test_sleepguard_safety_recheck_preserved(monkeypatch):
    """Confirm the final safety recheck in execute_power_action remains intact."""
    mock_executor = MagicMock(spec=ShutdownManager)
    mock_executor.execute_action.return_value = True
    
    controller = SleepGuardController(power_executor=mock_executor)
    
    # If media is playing, execute_power_action must abort
    monkeypatch.setattr(type(controller._media_engine), "is_playing", property(lambda self: True))
    result = controller.execute_power_action("shutdown")
    assert result is False, "Power action must abort when media is playing"
    assert mock_executor.execute_action.call_count == 0
    
    # If media is NOT playing and not interrupted, it executes
    monkeypatch.setattr(type(controller._media_engine), "is_playing", property(lambda self: False))
    # Mock idle check in tracker.sleepguard namespace to return idle > required
    monkeypatch.setattr("tracker.sleepguard.get_idle_seconds", lambda: 1000.0)
    result = controller.execute_power_action("shutdown")
    assert result is True
    assert mock_executor.execute_action.call_count == 1


# ============================================================================
# 2. CATEGORY ICON STYLING (NO COLORED SQUARE TILES)
# ============================================================================

def test_category_icon_clean_styling():
    """Verify category icons do NOT have colored square tile backgrounds."""
    for cat in [
        AppCategory.BROWSER,
        AppCategory.COMMUNICATION,
        AppCategory.PROGRAMMING,
        AppCategory.GAMING,
        AppCategory.SYSTEM,
        AppCategory.OTHER,
    ]:
        card = ClickableCategoryCard(category=cat, duration_s=1800)
        card.show()
        
        # Verify icon label background is transparent and has no border
        ss = card.styleSheet()
        assert "background: transparent" in ss, f"Expected transparent background for {cat}"
        assert "border: none" in ss, f"Expected no border for {cat}"
        assert "border-radius: 8px" not in ss, f"Expected no tile border-radius for {cat}"
        
        # Verify pixmap exists and is properly sized
        pm = card._icon_lbl.pixmap()
        assert not pm.isNull(), f"Icon pixmap should be valid for {cat}"
        assert pm.width() == 22
        assert pm.height() == 22
        
        card.close()


# ============================================================================
# 3. USAGE & TRENDS RANGE CONSISTENCY & HOME VS USAGE
# ============================================================================

def test_usage_today_matches_home_data():
    """Verify Usage page on Today tab matches Home page summary exactly."""
    page = ActivityPage()
    page.show()
    engine = AnalyticsEngine()
    
    # Today tab should be active by default
    assert page._time_range == 1
    assert page._btn_today.isChecked()
    
    today_sum = engine.get_today_summary()
    
    # Compare summary metrics
    assert page._kpi_screen_time.text() == engine.format_duration(today_sum.total_screen_time_s)
    assert page._kpi_active_time.text() == engine.format_duration(today_sum.active_time_s)
    assert page._kpi_idle_time.text() == engine.format_duration(today_sum.idle_time_s)
    
    top_c = today_sum.category_breakdown[0]["category"] if today_sum.category_breakdown else "-"
    if hasattr(top_c, "value"):
        top_c = top_c.value
    assert page._kpi_top_cat.text() == str(top_c).title()
    
    # Hourly chart must be visible for Today, and daily chart hidden
    assert not page._hourly_chart.isHidden()
    assert page._chart.isHidden()
    
    page.close()


def test_usage_7d_and_30d_ranges():
    """Verify selecting 7D and 30D updates the metrics and daily chart correctly."""
    page = ActivityPage()
    page.show()
    engine = AnalyticsEngine()
    
    # Select 7 Days
    page._on_range_changed(7)
    assert page._time_range == 7
    sum_7d = engine.get_custom_summary(date.today() - timedelta(days=6), date.today())
    assert page._kpi_screen_time.text() == engine.format_duration(sum_7d.total_screen_time_s)
    assert not page._chart.isHidden()
    assert page._hourly_chart.isHidden()
    assert "7 DAYS" in page._chart._title_lbl.text()
    
    # Select 30 Days
    page._on_range_changed(30)
    assert page._time_range == 30
    sum_30d = engine.get_custom_summary(date.today() - timedelta(days=29), date.today())
    assert page._kpi_screen_time.text() == engine.format_duration(sum_30d.total_screen_time_s)
    assert not page._chart.isHidden()
    assert page._hourly_chart.isHidden()
    assert "30 DAYS" in page._chart._title_lbl.text()
    
    page.close()


# ============================================================================
# 4. HOURLY CHART & EMPTY STATES
# ============================================================================

def test_hourly_chart_with_data_and_empty_state():
    """Verify HourlyIntensityChart updates data and displays clean empty state when 0."""
    chart = HourlyIntensityChart()
    chart.show()
    
    # With active data
    sample_data = [{"hour": f"{h:02d}:00", "total_s": 120.0 if h in (9, 10, 14) else 0.0} for h in range(24)]
    chart.update_data(sample_data)
    assert chart._empty_lbl.isHidden(), "Empty label should be hidden when data exists"
    # v4 Aurora chart keeps bar heights on the AppleBarGraphItem
    assert chart._bar_item._heights[9] == 2.0  # 120s / 60 = 2.0 mins
    
    # With all-zero data
    empty_data = [{"hour": f"{h:02d}:00", "total_s": 0.0} for h in range(24)]
    chart.update_data(empty_data)
    assert chart._empty_lbl.isVisible(), "Empty label should be visible when total usage is 0"
    assert chart._empty_lbl.text() == "No usage recorded yet"
    
    chart.close()


def test_daily_chart_empty_state():
    """Verify DailyScreenTimeChart displays clean empty state when all days are 0."""
    chart = DailyScreenTimeChart()
    chart.show()
    
    empty_pts = [{"day": (date.today() - timedelta(days=i)).strftime("%Y-%m-%d"), "active_s": 0.0} for i in range(7)]
    chart.update_data(empty_pts)
    assert chart._empty_lbl.isVisible(), "Empty label should be visible when all days have 0 usage"
    assert chart._empty_lbl.text() == "No usage recorded yet"
    
    # With real data
    active_pts = [{"day": (date.today() - timedelta(days=i)).strftime("%Y-%m-%d"), "active_s": 3600.0} for i in range(7)]
    chart.update_data(active_pts)
    assert chart._empty_lbl.isHidden(), "Empty label should be hidden when active usage exists"
    
    chart.close()
