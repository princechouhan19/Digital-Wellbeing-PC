"""
simple_category_row.py — Minimalist category row for the redesigned dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel
)

from core.constants import AppCategory, CATEGORY_ICONS
from analytics.engine import AnalyticsEngine
from ui.icons import get_icon

from ui.widgets.fluent import FluentCard

class ClickableCategoryCard(FluentCard):
    """A minimal card widget representing category usage with icon, name, and duration."""

    clicked = Signal()

    def __init__(
        self,
        category: AppCategory | str,
        duration_s: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("simple_category_row")
        
        self._category = category
        self._duration_s = duration_s
        
        self._setup_ui(duration_s)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            from ui import feedback
            feedback.tap(self)
            self.clicked.emit()
        super().mousePressEvent(event)

    def _setup_ui(self, duration_s: float) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.setFixedHeight(72)
        self.setMinimumWidth(160)
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        cat_enum = self._category if isinstance(self._category, AppCategory) else None
        if not cat_enum:
            try:
                cat_enum = AppCategory(str(self._category).title())
            except ValueError:
                pass
                
        icon_text = CATEGORY_ICONS.get(cat_enum, "apps") if cat_enum else "apps"
        cat_name = self._category.value.title() if isinstance(self._category, AppCategory) else str(self._category).title()

        # Category Icon
        self._icon_lbl = QLabel()
        self._icon_lbl.setObjectName("cat_icon_lbl")
        self._icon_lbl.setFixedSize(28, 28)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_name = icon_text
        layout.addWidget(self._icon_lbl)

        # Text Column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # Name
        self._name_lbl = QLabel(cat_name)
        self._name_lbl.setObjectName("cat_name_lbl")
        text_layout.addWidget(self._name_lbl)
        
        # Duration
        engine = AnalyticsEngine()
        self._dur_lbl = QLabel(engine.format_duration_short(duration_s))
        self._dur_lbl.setObjectName("cat_dur_lbl")
        text_layout.addWidget(self._dur_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch()

    def _apply_theme(self, is_dark: bool) -> None:
        if not hasattr(self, "_category"):
            return
            
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()
        
        from core.constants import get_category_colors
        cat_enum = self._category if isinstance(self._category, AppCategory) else None
        if not cat_enum:
            try:
                cat_enum = AppCategory(str(self._category).title())
            except ValueError:
                pass
        cat_color = get_category_colors(is_dark).get(cat_enum, tm.color('accent')) if cat_enum else tm.color('accent')
        
        self.setStyleSheet(f"""
            ClickableCategoryCard:hover {{
                border-color: {cat_color};
            }}
            QLabel#cat_icon_lbl {{ 
                background: transparent;
                border: none;
            }}
            QLabel#cat_name_lbl {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 600; }}
            QLabel#cat_dur_lbl {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 500; }}
        """)
        
        pix = get_icon(self._icon_name, color=cat_color, size=22).pixmap(22, 22)
        self._icon_lbl.setPixmap(pix)
