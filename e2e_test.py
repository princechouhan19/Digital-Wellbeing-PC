import sys
import os
import json
from datetime import datetime
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint, QTimer

from ui.main_window import MainWindow
from ui.theme import ThemeManager
from database.repository import Repository
from database.models import AppSession, AppCategory
from protection.core import ProtectionManager
from tracker.manager import TrackingManager
from ui.widgets.app_timer_widgets import TimerConfigDialog

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    ThemeManager.instance().set_theme("dark")
    
    # 1. Setup real backend
    repo = Repository()
    repo.clear_all_sessions()
    
    # Insert dummy data for brave
    repo.insert_session(AppSession(
        id=0,
        process_name="brave.exe",
        exe_path="C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        window_title="Brave",
        start_time=datetime.now(),
        end_time=None,
        duration_s=3600,
        category=AppCategory.OTHER,
        is_idle=False,
        was_closed=False
    ))
    
    pm = ProtectionManager(repo)
    tracker = TrackingManager()
    
    win = MainWindow(tracker=tracker, protection_manager=pm)
    win.show()
    QApplication.processEvents()
    
    print("[E2E] App Launched.")
    
    # Refresh dashboard to show brave.exe
    win._dashboard_page._screen_time_card.set_data(3600, [], [{"process_name": "brave.exe", "total_s": 3600}])
    QApplication.processEvents()
    
    # 2. Click Brave Browser
    app_layout = win._dashboard_page._screen_time_card._apps_layout
    row = app_layout.itemAt(0).widget()
    
    if not row:
        print("[E2E] Failed to find SimpleAppRow!")
        sys.exit(1)
        
    print(f"[E2E] Found SimpleAppRow for: {row.process_name}")
    center = QPoint(row.width() // 2, row.height() // 2)
    QTest.mouseClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
    QApplication.processEvents()
    
    # 3. Verify App Details opens
    if win._stack.currentIndex() != 6:
        print(f"[E2E] Failed! Expected index 6, got {win._stack.currentIndex()}")
        sys.exit(1)
        
    print("[E2E] Navigated to App Details page.")
    
    # 4. Verify title shows Brave Browser
    title = win._app_details_page._title_lbl.text()
    if "brave" not in title.lower():
        print(f"[E2E] Title does not show brave! Got: {title}")
    else:
        print(f"[E2E] Verified title: {title}")
        
    # 5. Verify App Timer UI is visible
    if not win._app_details_page._timer_card.isVisible():
        print("[E2E] Timer card is not visible!")
        sys.exit(1)
    
    print("[E2E] App Timer UI is visible.")
    
    # Grab screenshot
    pixmap = win.grab()
    pixmap.save("C:\\Users\\akshi\\.gemini\\antigravity-ide\\brain\\77176abb-7214-42a2-a272-188483d8d5a7\\scratch\\app_details.png")
    print("[E2E] Screenshot saved to scratch/app_details.png")
    
    # 6. Click Change Timer
    change_btn = win._app_details_page._timer_card.change_btn
    print("[E2E] Clicking Change Timer...")
    
    # We have to use a timer to interact with the modal dialog
    dialog_found = False
    def interact_with_dialog():
        nonlocal dialog_found
        top_widget = QApplication.activeModalWidget()
        if isinstance(top_widget, TimerConfigDialog):
            dialog_found = True
            print("[E2E] TimerConfigDialog opened.")
            # 8. Save a timer
            top_widget.hr_picker.set_index(1)
            top_widget.min_picker.set_index(30)
            print("[E2E] Accepting dialog...")
            top_widget.accept()
            
    QTimer.singleShot(500, interact_with_dialog)
    
    # This will block until dialog is closed
    QTest.mouseClick(change_btn, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    
    if not dialog_found:
        print("[E2E] TimerConfigDialog never opened!")
        sys.exit(1)
        
    # Verify rule was saved
    rule = pm.limits.get_limit_rule("brave.exe")
    if not rule or rule["limit_seconds"] != 5400: # 1h 30m
        print(f"[E2E] Rule was not saved correctly! Got: {rule}")
        sys.exit(1)
        
    print(f"[E2E] Verified rule saved: {rule}")
    print("[E2E] All tests passed.")
    
    app.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
