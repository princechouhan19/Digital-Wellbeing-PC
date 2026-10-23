import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from tracker.manager import TrackingManager
from tracker.sleepguard import SleepGuardController
import pytest

def test_startup_smoke():
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Initialize Core Components
    tracker = TrackingManager()
    sleepguard = SleepGuardController()
    
    # Initialize UI
    window = MainWindow(tracker=tracker, sleepguard=sleepguard)
    
    # Verify the window can be shown and created without throwing exceptions
    assert window is not None
    assert tracker is not None
    assert sleepguard is not None
    
    # Clean up
    tracker.stop()
    sleepguard.stop()
