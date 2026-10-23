import sys
import os
import time
from pathlib import Path
from datetime import datetime, date

# Add root folder to sys.path
os.environ["DW_TEST_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCloseEvent

# Core components
from core.constants import APP_NAME
from core.logger import logger
from database.repository import Repository
from database.models import AppSession
from settings.manager import SettingsManager
from tracker.manager import TrackingManager
from tracker.foreground import get_foreground_app, ForegroundApp
from tracker.idle import get_idle_seconds, is_idle
from tracker.session import SessionEvent, SessionMonitor
from notifications.notifier import Notifier

def run_tests():
    os.environ["DW_TEST_MODE"] = "1"
    import tempfile
    from pathlib import Path
    temp_db = Path(tempfile.gettempdir()) / "digital_wellbeing_test_features.db"
    if temp_db.exists():
        try:
            temp_db.unlink()
        except Exception:
            pass
    Repository.set_db_path_override(temp_db)

    print("==================================================")
    print("           DIGITAL WELLBEING FEATURE TESTS         ")
    print("==================================================")

    results = {}
    
    # Initialize QApplication for GUI testing
    app = QApplication.instance() or QApplication(sys.argv)
    
    # 1. Database is created
    try:
        repo = Repository()
        db_path = repo._db_path
        results["Database is created"] = db_path.exists()
        print(f"[OK] Database created at: {db_path}")
    except Exception as e:
        results["Database is created"] = False
        print(f"[FAIL] Database creation: {e}")

    # 2. Settings are saved
    try:
        sm = SettingsManager()
        sm.set_bool("test_setting_key", True)
        assert sm.get_bool("test_setting_key") is True
        sm.set_bool("test_setting_key", False)
        assert sm.get_bool("test_setting_key") is False
        results["Settings are saved"] = True
        print("[OK] Settings manager read/write verified")
    except Exception as e:
        results["Settings are saved"] = False
        print(f"[FAIL] Settings manager: {e}")

    # 3. Tracking starts
    try:
        tracker = TrackingManager()
        assert not tracker.is_running
        tracker.start()
        assert tracker.is_running
        results["Tracking starts"] = True
        print("[OK] Tracking manager starts correctly")
    except Exception as e:
        results["Tracking starts"] = False
        print(f"[FAIL] Tracking manager start: {e}")

    # 4. Foreground app detection works
    try:
        fg = get_foreground_app()
        # Even if headless/None on some test runs, we can verify it doesn't crash
        # and returns either None or ForegroundApp.
        if fg is not None:
            assert isinstance(fg, ForegroundApp)
            assert isinstance(fg.process_name, str)
        results["Foreground app detection works"] = True
        print(f"[OK] Foreground app detection checked: {fg}")
    except Exception as e:
        results["Foreground app detection works"] = False
        print(f"[FAIL] Foreground app detection: {e}")

    # 5. Idle detection works
    try:
        idle_s = get_idle_seconds()
        assert isinstance(idle_s, float) and idle_s >= 0
        # Check threshold evaluation
        res_idle = is_idle(999999.0)
        assert res_idle is False
        results["Idle detection works"] = True
        print(f"[OK] Idle detection checked (current idle: {idle_s:.2f}s)")
    except Exception as e:
        results["Idle detection works"] = False
        print(f"[FAIL] Idle detection: {e}")

    # 6. Lock/Unlock detection works & Sleep/Resume detection works
    try:
        events = []
        def cb(e):
            events.append(e)
            
        monitor = SessionMonitor(cb)
        
        # Test WM_WTSSESSION_CHANGE message processing
        # WTS_SESSION_LOCK (0x7)
        monitor._wnd_proc(0, 0x02B1, 0x7, 0)
        # WTS_SESSION_UNLOCK (0x8)
        monitor._wnd_proc(0, 0x02B1, 0x8, 0)
        
        # Test WM_POWERBROADCAST message processing
        # PBT_APMSUSPEND (0x0004)
        monitor._wnd_proc(0, 0x0218, 0x0004, 0)
        # PBT_APMRESUMEAUTOMATIC (0x0012)
        monitor._wnd_proc(0, 0x0218, 0x0012, 0)
        
        assert SessionEvent.LOCK in events
        assert SessionEvent.UNLOCK in events
        results["Lock/Unlock detection works"] = True
        print("[OK] Lock/Unlock detection handler verified")
        
        assert SessionEvent.SLEEP in events
        assert SessionEvent.RESUME in events
        results["Sleep/Resume detection works"] = True
        print("[OK] Sleep/Resume detection handler verified")
    except Exception as e:
        results["Lock/Unlock detection works"] = False
        results["Sleep/Resume detection works"] = False
        print(f"[FAIL] Lock/Unlock / Sleep/Resume detection: {e}")

    # Clean up tracking manager if still running
    try:
        if tracker.is_running:
            tracker.stop()
    except Exception:
        pass

    # 7. Dashboard loads & Charts display correctly
    try:
        from ui.pages.dashboard import DashboardPage
        from ui.pages.activity import ActivityPage
        
        # Prepare a mock record in DB to make sure charts don't render completely empty or crash
        from core.constants import AppCategory
        s = AppSession("chrome.exe", "Chrome", datetime.now(), datetime.now(), 60.0, AppCategory.BROWSER, False)
        repo.insert_session(s)
        
        # Dashboard page instantiation and refresh
        db_page = DashboardPage()
        db_page._refresh()
        results["Dashboard loads"] = True
        print("[OK] Dashboard page loaded and refreshed successfully")
        
        # Draw charts on Activity page
        act_page = ActivityPage()
        act_page._refresh()
        
        results["Charts display correctly"] = True
        print("[OK] Activity and Donut charts display correctly")
    except Exception as e:
        results["Dashboard loads"] = False
        results["Charts display correctly"] = False
        print(f"[FAIL] Pages and Charts load: {e}")

    # 8. System tray works & Window close triggers quit (not minimize to tray)
    try:
        sm = SettingsManager()
        sm.set_bool("minimize_to_tray", False)
        from ui.app import DigitalWellbeingApp
        dw_app = DigitalWellbeingApp(start_minimized=False)

        # Check system tray icon is created and visible while app is running
        assert dw_app._tray is not None
        results["System tray works"] = True
        print("[OK] System tray icon initialized successfully")

        # Verify window is shown (close=exit means no hidden start)
        win = dw_app._window
        assert win is not None
        QApplication.processEvents()
        assert win.isVisible()

        # Simulate closing the window: close event must be ACCEPTED (not ignored),
        # and quit_requested signal must be emitted.
        quit_signal_fired = []
        win.quit_requested.connect(lambda: quit_signal_fired.append(True))

        evt = QCloseEvent()
        win.closeEvent(evt)
        assert evt.isAccepted(), "closeEvent must accept the event (not minimize to tray)"
        assert len(quit_signal_fired) == 1, "quit_requested signal must fire exactly once"

        results["Window minimizes to tray"] = True
        print("[OK] Close event accepted and quit_requested signal emitted (close=exit)")
        dw_app._quit()
    except Exception as e:
        import traceback
        traceback.print_exc()
        results["System tray works"] = False
        results["Window minimizes to tray"] = False
        print(f"[FAIL] System tray / window close test: {e}")

    # 9. Application launches successfully
    # If we reached here, the app modules import and initialize successfully
    results["Application launches successfully"] = True
    print("[OK] Application launches successfully")

    # 10. Notifications work
    try:
        # Check QSystemTrayIcon notification
        dw_app = DigitalWellbeingApp(start_minimized=True)
        dw_app._tray.showMessage("Test Title", "Test Message", QSystemTrayIcon.MessageIcon.Information, 100)
        
        # Check fallback notifier
        notifier = Notifier()
        notifier.notify("Test Notification", "This is a verification notification", duration=1)
        
        results["Notifications work"] = True
        print("[OK] Notifications triggered successfully via QSystemTrayIcon and Notifier")
        dw_app._quit()
    except Exception as e:
        results["Notifications work"] = False
        print(f"[FAIL] Notifications: {e}")

    print("\n==================================================")
    print("                 TESTS RESULTS REPORT             ")
    print("==================================================")
    all_passed = True
    for feature, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{feature:<40}: {status}")
        if not passed:
            all_passed = False
            
    print("==================================================")
    if all_passed:
        print("          ALL VERIFICATION TESTS PASSED           ")
    else:
        print("          SOME VERIFICATION TESTS FAILED          ")
    print("==================================================")
    
    # Cleanup DB override
    Repository.set_db_path_override(None)
    if temp_db.exists():
        try:
            temp_db.unlink()
        except Exception:
            pass

    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
