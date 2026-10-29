"""
capture_screenshots.py — Script to capture updated screenshots for v4.4.0 release.
Captures:
- dark_sleepguard.png
- dark_insights.png
- dark_websites.png
- dark_activity.png
- dark_tasks.png
- dark_session_logs.png
- dark_settings_parental.png
- ambient_notch.png
"""
import os
import sys
import time
from pathlib import Path

# Setup environment
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
os.chdir(str(root))
os.environ["DW_TEST_MODE"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.theme import ThemeManager
from ui.widgets.ambient_notch import AmbientNotch
from database.repository import Repository

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    tm = ThemeManager.instance()
    tm.set_theme("dark")

    # Seed sample tasks if none exist so Tasks page looks great in screenshot
    repo = Repository()
    tasks = repo.get_smart_tasks()
    if not tasks:
        repo.add_smart_task("Quarterly Financial Modeling", "Excel projections & budget", priority=1, estimated_minutes=45, target_processes=["excel.exe"])
        repo.add_smart_task("Review Core PR #142", "Code review & unit tests", priority=2, estimated_minutes=25, target_processes=["code.exe"])
        repo.add_smart_task("Study Biology Module 4", "Reading textbook & notes", priority=3, estimated_minutes=30, target_processes=["onenote.exe", "acrobat.exe"])

    win = MainWindow(tracker=None)
    win.resize(1140, 780)
    win.show()
    win._apply_theme(True)
    app.processEvents()

    out_dir = root / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = [
        (1, "dark_activity.png"),         # Usage / Activity with < > historical buttons
        (2, "dark_focus.png"),            # Focus with rounded start button
        (13, "dark_tasks.png"),           # Smart Tasks page
        (12, "dark_websites.png"),        # Websites with < > historical buttons
        (5, "dark_insights.png"),         # Interactive Insights (Weekly/Monthly/Yearly)
        (6, "dark_sleepguard.png"),       # Redesigned SleepGuard page
        (8, "dark_settings.png"),         # Settings
        (9, "dark_session_logs.png"),     # Session Logs (no emojis, system diagnostics)
    ]

    for page_idx, filename in pages:
        win._navigate(page_idx)
        start = time.time()
        while time.time() - start < 0.6:
            app.processEvents()
            time.sleep(0.04)

        target = out_dir / filename
        win.grab().save(str(target))
        print(f"[OK] Captured {filename}")

    # Capture Ambient Notch
    notch = AmbientNotch()
    notch.sync_active_task()
    notch.show()
    notch.set_expanded(True)
    start = time.time()
    while time.time() - start < 0.5:
        app.processEvents()
        time.sleep(0.04)

    notch_target = out_dir / "ambient_notch.png"
    notch.grab().save(str(notch_target))
    print("[OK] Captured ambient_notch.png")

    notch.close()
    win.close()
    print("All screenshots captured successfully!")

if __name__ == "__main__":
    main()
