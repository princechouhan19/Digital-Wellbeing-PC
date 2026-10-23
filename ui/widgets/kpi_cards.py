"""
kpi_cards.py — Reusable Key Performance Indicator cards.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from ui.theme import ThemeManager
from ui.icons import get_icon

class KPICard(QFrame):
    def __init__(self, title: str, icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("kpi_card")
        self._icon_name = icon_name
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)

        if self._icon_name:
            self._icon_lbl = QLabel()
            self._icon_lbl.setFixedSize(16, 16)
            self._icon_lbl.setPixmap(get_icon(self._icon_name, size=16).pixmap(16, 16))
            hdr.addWidget(self._icon_lbl)

        self._title_lbl = QLabel(title)
        self._title_lbl.setObjectName("kpi_title")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()
        layout.addLayout(hdr)
        
        self._value_lbl = QLabel("-")
        self._value_lbl.setObjectName("kpi_value")
        layout.addWidget(self._value_lbl)

        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        from ui import design_system as ds
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#kpi_card {{
                background: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.RADIUS['lg']}px;
            }}
            QFrame#kpi_card:hover {{
                background: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#kpi_title {{
                {ds.type_css('micro', tm.color('text_muted'))}
                text-transform: uppercase;
            }}
            QLabel#kpi_value {{
                color: {tm.color('text_main')};
                font-size: 22px;
                font-weight: 700;
                letter-spacing: -0.5px;
                font-family: {ds.FONT_STACK_DISPLAY};
            }}
        """)
        if getattr(self, "_icon_name", "") and hasattr(self, "_icon_lbl"):
            self._icon_lbl.setPixmap(get_icon(self._icon_name, color=tm.color('text_muted'), size=16).pixmap(16, 16))

    def set_value(self, text: str):
        self._value_lbl.setText(text)

