from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class StatCard(QFrame):
    def __init__(
        self,
        label: str,
        value: str,
        icon: str,
        accent_color_key: str = "accent",
        subtext: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self._accent_key = accent_color_key
        self._setup_ui(label, value, icon, subtext)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, label: str, value: str, icon: str, subtext: str) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 18)
        self._layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # Icon pill with soft translucent glow
        self._icon_label = QLabel(icon)
        self._icon_label.setObjectName("stat_card_icon")
        self._icon_label.setFixedSize(40, 40)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label_label = QLabel(label.upper())
        self._label_label.setObjectName("stat_card_label")

        top_row.addWidget(self._icon_label)
        top_row.addSpacing(12)
        top_row.addWidget(self._label_label, 1)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("stat_card_value")

        self._layout.addLayout(top_row)
        self._layout.addWidget(self._value_label)

        if subtext:
            self._subtext_label = QLabel(subtext)
            self._subtext_label.setObjectName("stat_card_subtext")
            self._layout.addWidget(self._subtext_label)
        else:
            self._subtext_label = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        accent = tm.color(self._accent_key)
        
        self.setStyleSheet(f"""
            QLabel#stat_card_label {{ color: {tm.color('text_sub')}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; }}
            QLabel#stat_card_value {{ font-size: 32px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.8px; }}
            QLabel#stat_card_subtext {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
        """)
        
        self._icon_label.setStyleSheet(
            f"color: {accent}; "
            f"background-color: {accent}20; "
            f"border: 1px solid {accent}40; "
            f"border-radius: 14px; "
            f"font-size: 18px;"
        )

    def update_value(self, value: str, subtext: str = "") -> None:
        self._value_label.setText(value)
        if subtext:
            if self._subtext_label is None:
                self._subtext_label = QLabel(subtext)
                self._subtext_label.setObjectName("stat_card_subtext")
                self._layout.addWidget(self._subtext_label)
                
                # Apply theme again to style the new subtext label
                from ui.theme import ThemeManager
                self._apply_theme(ThemeManager.instance().is_dark)
            else:
                self._subtext_label.setText(subtext)
