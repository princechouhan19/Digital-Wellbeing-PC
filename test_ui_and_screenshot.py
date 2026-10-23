"""
test_ui_and_screenshot.py — UI verification and screenshot capturing script.
"""

import sys
import os
import time
import logging
from pathlib import Path

# Force UTF-8 and test mode
sys.path.insert(0, str(Path(__file__).parent))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ui_screenshot")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap

from settings.manager import SettingsManager
from ui.pages.settings import SettingsPage
from ui.pages.wellbeing import WellbeingPage
from ui.main_window import MainWindow

def test_persistence():
    print("=== Testing Setting Persistence Across Application Restart ===")
    sm = SettingsManager()
    
    for action in ["lock", "sleep", "hibernate", "shutdown"]:
        sm.sleepguard_action = action
        # Create new SettingsManager instance to simulate restart
        sm_new = SettingsManager()
        val = sm_new.sleepguard_action
        assert val == action, f"Expected {action}, got {val}"
        print(f"  [OK] Setting '{action}' saved and verified on reload")

    # Reset back to default lock
    sm.sleepguard_action = "lock"
    print("[OK] Setting persistence test passed!")

def capture_settings_screenshot():
    print("=== Capturing Settings Page Screenshot ===")
    app = QApplication.instance() or QApplication(sys.argv)

    from ui.theme import ThemeManager
    tm = ThemeManager.instance()
    tm.set_theme("dark")

    sm = SettingsManager()
    sm.sleepguard_action = "lock"

    win = MainWindow(tracker=None)
    win.resize(1100, 750)
    win.show()
    win._apply_theme(True)
    app.processEvents()

    # Navigate to Settings Page (index 3)
    win._navigate(3)

    # Process events in loop to complete AnimatedStackedWidget transition animation
    start = time.time()
    while time.time() - start < 1.0:
        app.processEvents()
        time.sleep(0.05)

    if hasattr(win._settings_page, "_scroll"):
        scroll = win._settings_page._scroll
        scroll.widget().adjustSize()
        scroll.verticalScrollBar().setValue(300)
        app.processEvents()

    screenshot_path = Path(__file__).parent / "settings_action_setting.png"
    pixmap = win.grab()
    pixmap.save(str(screenshot_path))
    print(f"[OK] Screenshot saved to: {screenshot_path}")

    # Copy to artifacts directory as required
    artifacts_dir = Path(r"C:\Users\akshi\.gemini\antigravity-ide\brain\f3b0ab4a-a59c-4c95-b1e0-4c7152704d06")
    if artifacts_dir.exists():
        dest_path = artifacts_dir / "settings_action_setting.png"
        pixmap.save(str(dest_path))
        print(f"[OK] Screenshot copied to artifact directory: {dest_path}")

    win.close()

if __name__ == "__main__":
    test_persistence()
    capture_settings_screenshot()
