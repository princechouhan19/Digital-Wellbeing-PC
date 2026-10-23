import sys
from PySide6.QtWidgets import QApplication
from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
from ui.theme import apply_theme
from PySide6.QtCore import QTimer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_theme(app, "dark")
    
    dialog = WebsiteTimerConfigDialog(domain="instagram.com", rule={"limit_seconds": 3600})
    
    def take_screenshot():
        pixmap = dialog.grab()
        pixmap.save("C:\\Users\\akshi\\.gemini\\antigravity-ide\\brain\\77176abb-7214-42a2-a272-188483d8d5a7\\scratch\\timer_config_dialog_fluent.png")
        dialog.reject()
        
    QTimer.singleShot(1000, take_screenshot)
    dialog.exec()
