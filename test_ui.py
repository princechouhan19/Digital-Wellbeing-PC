"""
Headless page construction test — verifies all V2 UI pages can be instantiated
without a display by mocking QApplication minimally.
"""
import sys
sys.path.insert(0, ".")

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

# Apply theme
from ui.theme import ThemeManager
ThemeManager.instance().set_theme("dark", app)

errors = []

# Dashboard Page V2
try:
    from ui.pages.dashboard import DashboardPage
    p = DashboardPage()
    p._refresh()
    print("[OK] DashboardPage V2 — instantiated and refreshed")
except Exception as e:
    errors.append(f"[FAIL] DashboardPage V2: {e}")
    print(errors[-1])

# Activity Page V2
try:
    from ui.pages.activity import ActivityPage
    p = ActivityPage()
    p._refresh()
    print("[OK] ActivityPage V2 — instantiated and refreshed")
except Exception as e:
    import traceback
    errors.append(f"[FAIL] ActivityPage V2: {e}")
    print(errors[-1])
    traceback.print_exc()

# Wellbeing Page V2
try:
    from ui.pages.wellbeing import WellbeingPage
    p = WellbeingPage()
except Exception as e:
    errors.append(f"[FAIL] WellbeingPage V2: {e}")
    print(errors[-1])

# Settings Page V2
try:
    from ui.pages.settings import SettingsPage
    from protection.core import ProtectionManager
    from database.repository import Repository
    from tracker.manager import TrackingManager
    repo = Repository()
    tracker = TrackingManager()
    protection_manager = ProtectionManager(repo)
    p = SettingsPage(tracker=tracker, protection_manager=protection_manager)
    print("[OK] SettingsPage V2 — instantiated")

    # Settings Navigation Regression Test
    expected_categories = [
        "General",
        "Appearance",
        "Tracking",
        "SleepGuard",
        "Security & PIN",
        "Data & Storage",
        "About / Updates",
    ]
    assert p._sidebar.count() == len(expected_categories), f"Expected {len(expected_categories)} sidebar items, found {p._sidebar.count()}"
    
    for i, expected_name in enumerate(expected_categories):
        item = p._sidebar.item(i)
        assert item.text() == expected_name, f"Sidebar index {i} mismatch: expected {expected_name}, got {item.text()}"
        
        # Click the item (triggers _on_sidebar_changed which updates stack index)
        p._sidebar.setCurrentRow(i)
        
        # Verify deterministic mapping
        current_stack_index = p._stack.currentIndex()
        assert current_stack_index == i, f"Stack mismatch on '{expected_name}': sidebar index {i} mapped to stack index {current_stack_index}"
        
    print("[OK] SettingsPage Navigation — 1:1 deterministic mapping verified")

except Exception as e:
    import traceback
    errors.append(f"[FAIL] SettingsPage V2: {e}")
    print(errors[-1])
    traceback.print_exc()



# Widgets
try:
    from ui.widgets.hero_card import HeroCard
    c = HeroCard()
    c.set_data("3h 45m", 12.5, True)
    print("[OK] HeroCard V2 widget")

    from ui.widgets.stat_card import StatCard
    s = StatCard("Active Focus", "2h 30m", "⚡", "#4ade80")
    print("[OK] StatCard V2 widget")

    from ui.widgets.donut_chart import DonutChart
    d = DonutChart()
    d.set_data([("Browser", 3600, "#4FC3F7"), ("Gaming", 1800, "#FF8A65")], "1h", "total")
    print("[OK] DonutChart widget")

    from ui.widgets.app_row import AppUsageRow
    from core.constants import AppCategory
    r = AppUsageRow(1, "chrome.exe", "Google Chrome", AppCategory.BROWSER, 3600, 3600)
    print("[OK] AppUsageRow widget")
except Exception as e:
    errors.append(f"[FAIL] Widgets V2: {e}")
    print(errors[-1])

if __name__ == '__main__':
    # Main window V2
    try:
        from tracker.manager import TrackingManager
        from ui.main_window import MainWindow
        tracker = TrackingManager()
        w = MainWindow(tracker)
        print("[OK] MainWindow V2 — instantiated with all pages")
    except Exception as e:
        import traceback
        errors.append(f"[FAIL] MainWindow V2: {e}")
        print(errors[-1])
        traceback.print_exc()

    print()
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        sys.exit(1)
    else:
        print("=== ALL V2 UI COMPONENTS PASS ===")
        sys.exit(0)
