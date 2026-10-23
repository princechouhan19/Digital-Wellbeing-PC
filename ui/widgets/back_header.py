"""
back_header.py — Reusable navigation header with a Back button.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

class BackHeader(QWidget):
    """
    A reusable header component containing a Back button and page titles.
    Emits `back_requested` when the back button is clicked.
    """
    back_requested = Signal()

    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Back Button (chevron via SVG icon)
        from ui.icons import get_icon
        self._back_btn = QPushButton()
        self._back_btn.setObjectName("back_btn")
        self._back_btn.setFixedSize(36, 36)
        self._back_btn.setIconSize(self._back_btn.size())
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.back_requested.emit)

        layout.addWidget(self._back_btn)

        # Title and Subtitle
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        self._title_lbl = QLabel(self._title)
        self._title_lbl.setObjectName("page_title")
        title_box.addWidget(self._title_lbl)

        if self._subtitle:
            self._subtitle_lbl = QLabel(self._subtitle)
            self._subtitle_lbl.setObjectName("page_subtitle")
            title_box.addWidget(self._subtitle_lbl)

        layout.addLayout(title_box)
        layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        from ui import design_system as ds
        from ui.icons import get_icon
        tm = ThemeManager.instance()

        self._back_btn.setIcon(get_icon("back", color=tm.color('text_sub'), size=18))

        self.setStyleSheet(f"""
            QPushButton#back_btn {{
                background: transparent;
                border: 1px solid {tm.color('border')};
                border-radius: 18px;
                color: {tm.color('text_sub')};
                padding: 0;
            }}
            QPushButton#back_btn:hover {{
                background: {tm.color('surface_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#back_btn:pressed {{
                background: {tm.color('surface_pressed')};
            }}
            QLabel#page_title {{
                {ds.type_css('title1', tm.color('text_main'))}
            }}
            QLabel#page_subtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
        """)
