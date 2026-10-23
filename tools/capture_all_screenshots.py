"""
tools/capture_all_screenshots.py
Captures updated, pixel-perfect screenshots of all Digital Wellbeing pages
for both README.md and the website.
"""

import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap

from ui.theme import ThemeManager
from ui.main_window import MainWindow
from ui.onboarding import OnboardingFlow
from settings.manager import SettingsManager

def capture_all():
    app = QApplication.instance() or QApplication(sys.argv)
    
    docs_ss_dir = root_dir / "docs" / "screenshots"
    web_ss_dir = root_dir / "website" / "public" / "images" / "app"
    docs_ss_dir.mkdir(parents=True, exist_ok=True)
    web_ss_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure display name is friendly
    sm = SettingsManager()
    if not sm.display_name or sm.display_name == "Unknown":
        sm.display_name = "Prince"
        
    win = MainWindow(tracker=None)
    win.resize(1200, 800)
    win.show()
    
    def process(duration=0.3):
        start = time.time()
        while time.time() - start < duration:
            app.processEvents()
            time.sleep(0.02)

    # -------------------------------------------------------------
    # 1. Dark Mode Screenshots
    # -------------------------------------------------------------
    print("Capturing Dark Mode pages...")
    ThemeManager.instance().set_theme("dark")
    win._apply_theme(True)
    process(0.5)
    
    pages = [
        (0, "dark_dashboard.png", "home-dark.png"),
        (1, "dark_activity.png", "usage-dark.png"),
        (2, "dark_focus.png", "focus-dark.png"),
        (3, "dark_app_locker.png", "app-locker-dark.png"),
        (4, "dark_app_timer.png", "app-timer-dark.png"),
        (5, "dark_insights.png", "insights-dark.png"),
        (6, "dark_sleepguard.png", "sleepguard-dark.png"),
        (8, "dark_settings.png", "settings-dark.png"),
        (12, "dark_websites.png", None),
    ]
    
    for idx, docs_name, web_name in pages:
        win._navigate(idx)
        process(0.4)
        
        pix = win.grab()
        if docs_name:
            out_path = docs_ss_dir / docs_name
            pix.save(str(out_path))
            print(f"Saved: {out_path}")
        if web_name:
            out_path = web_ss_dir / web_name
            pix.save(str(out_path))
            print(f"Saved: {out_path}")
            
    # Capture SafeBrowse by scrolling Settings
    win._navigate(8)
    process(0.2)
    if hasattr(win._settings_page, "_scroll") and win._settings_page._scroll:
        scroll = win._settings_page._scroll
        scroll.verticalScrollBar().setValue(380)
        process(0.3)
        pix = win.grab()
        safebrowse_path = docs_ss_dir / "safebrowse_dark.png"
        pix.save(str(safebrowse_path))
        print(f"Saved: {safebrowse_path}")

    # -------------------------------------------------------------
    # 2. Light Mode Screenshots
    # -------------------------------------------------------------
    print("\nCapturing Light Mode pages...")
    ThemeManager.instance().set_theme("light")
    win._apply_theme(False)
    process(0.5)
    
    light_pages = [
        (0, "light_dashboard.png", "home-light.png"),
        (1, "light_activity.png", "usage-light.png"),
        (2, "light_focus.png", "focus-light.png"),
        (3, "light_app_locker.png", "app-locker-light.png"),
        (4, "light_app_timer.png", "app-timer-light.png"),
        (5, "light_insights.png", "insights-light.png"),
        (6, "light_sleepguard.png", "sleepguard-light.png"),
        (8, "light_settings.png", "settings-light.png"),
    ]
    
    for idx, docs_name, web_name in light_pages:
        win._navigate(idx)
        process(0.4)
        
        pix = win.grab()
        if docs_name:
            out_path = docs_ss_dir / docs_name
            pix.save(str(out_path))
            print(f"Saved: {out_path}")
        if web_name:
            out_path = web_ss_dir / web_name
            pix.save(str(out_path))
            print(f"Saved: {out_path}")

    win.close()
    process(0.2)
    
    # -------------------------------------------------------------
    # 3. Onboarding Wizard Screenshot
    # -------------------------------------------------------------
    print("\nCapturing Onboarding Wizard...")
    ThemeManager.instance().set_theme("dark")
    wizard = OnboardingFlow()
    wizard.show()
    process(0.5)
    
    wizard_pix = wizard.grab()
    onboarding_path = docs_ss_dir / "onboarding_dark.png"
    wizard_pix.save(str(onboarding_path))
    print(f"Saved: {onboarding_path}")
    wizard.close()
    process(0.2)
    
    print("\n[SUCCESS] All screenshots updated successfully!")

if __name__ == "__main__":
    capture_all()
