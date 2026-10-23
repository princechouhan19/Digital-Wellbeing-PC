import sys
from PySide6.QtWidgets import QApplication, QFrame
from ui.main_window import MainWindow

def test_render():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(None, None)
    window.show()
    
    app.processEvents()
    
    print("MainWindow layout:", window.layout())
    print("MainWindow size:", window.size())
    print("Stack visible:", window._stack.isVisible())
    print("Stack current index:", window._stack.currentIndex())
    print("DashboardPage visible:", window._dashboard_page.isVisible())
    print("DashboardPage geometry:", window._dashboard_page.geometry())
    
    app.quit()

if __name__ == "__main__":
    test_render()
