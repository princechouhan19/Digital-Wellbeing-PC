"""
quick_actions.py — A row of quick action buttons for the dashboard.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout
from ui.widgets.fluent import FluentButton

class QuickActionsRow(QWidget):
    action_focus = Signal()
    action_locker = Signal()
    action_settings = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        btn_focus = FluentButton("Start Focus", primary=True)
        btn_focus.set_icon_name("focus", size=14, color="#FFFFFF")
        btn_focus.clicked.connect(self.action_focus.emit)
        
        btn_locker = FluentButton("App Locker", variant="tinted")
        btn_locker.set_icon_name("lock", size=14)
        btn_locker.clicked.connect(self.action_locker.emit)
        
        btn_settings = FluentButton("Settings", variant="tinted")
        btn_settings.set_icon_name("settings", size=14)
        btn_settings.clicked.connect(self.action_settings.emit)
        
        layout.addWidget(btn_focus)
        layout.addWidget(btn_locker)
        layout.addWidget(btn_settings)
        layout.addStretch()
