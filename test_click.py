import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QPoint
from ui.main_window import MainWindow
from ui.theme import ThemeManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ThemeManager.instance().set_theme("dark")

    class MockTracker:
        pass
    from database.repository import Repository
    from protection.core import ProtectionManager
    pm = ProtectionManager(Repository())
    
    win = MainWindow(tracker=MockTracker(), protection_manager=pm)
    
    # Inject dummy app data to ActiveScreenTimeCard
    top_apps = [{"process_name": "brave.exe", "total_s": 3600}]
    win._dashboard_page._screen_time_card.set_data(3600, [], top_apps)
    
    win.show()
    
    # We need to wait for events to process
    QApplication.processEvents()
    
    # Find the SimpleAppRow
    app_layout = win._dashboard_page._screen_time_card._apps_layout
    row = app_layout.itemAt(0).widget()
    
    if row:
        print("Simulating click on SimpleAppRow")
        # Click center of the row
        center = QPoint(row.width() // 2, row.height() // 2)
        QTest.mouseClick(row, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center)
    
    # Ensure all slots have finished running
    QApplication.processEvents()
    
    print(f"Current page index: {win._stack.currentIndex()}")
    
    app.quit()
