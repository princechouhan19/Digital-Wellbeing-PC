"""
simple_app_row.py — Minimalist application row for the redesigned dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal, Property, QPropertyAnimation
from PySide6.QtGui import QCursor, QPainter, QColor, QBrush
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel
)

from utils.icon_provider import AppIconProvider
from analytics.engine import AnalyticsEngine

class SimpleAppRow(QFrame):
    """A minimal row widget representing app usage with icon, name, and duration only."""
    
    clicked = Signal(str)
    hover_entered = Signal(str)
    hover_left = Signal(str)

    def __init__(
        self,
        process_name: str,
        display_name: str,
        duration_s: float,
        legend_color: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.process_name = process_name
        self.display_name = display_name
        self._legend_color = legend_color
        self.setObjectName("simple_app_row")
        
        self._setup_ui(display_name, duration_s)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    @Property(float)
    def hover_progress(self) -> float:
        return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def set_highlighted(self, state: bool) -> None:
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0 if state else 0.0)
        self._hover_anim.setDirection(QPropertyAnimation.Direction.Forward)
        self._hover_anim.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.set_highlighted(True)
        self.hover_entered.emit(self.display_name)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.set_highlighted(False)
        self.hover_left.emit(self.display_name)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._hover_progress > 0.0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            from ui.theme import ThemeManager
            is_dark = ThemeManager.instance().is_dark
            
            if is_dark:
                color = QColor(255, 255, 255)
                # target alpha roughly 0.06 (15/255)
                color.setAlpha(int(15 * self._hover_progress))
            else:
                color = QColor(0, 0, 0)
                # target alpha roughly 0.04 (10/255)
                color.setAlpha(int(10 * self._hover_progress))
                
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(self.rect(), 6, 6)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            from ui import feedback
            feedback.tap(self)
            self.clicked.emit(self.process_name)
            event.accept()
        else:
            super().mousePressEvent(event)

    def _setup_ui(self, display_name: str, duration_s: float) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 7, 14, 7)
        layout.setSpacing(14)

        if self._legend_color:
            self._dot_lbl = QLabel()
            self._dot_lbl.setFixedSize(10, 10)
            self._dot_lbl.setStyleSheet(f"background-color: {self._legend_color}; border-radius: 6px;")
            layout.addWidget(self._dot_lbl)

        # App Icon
        icon_provider = AppIconProvider()
        icon = icon_provider.get_icon(self.process_name)
        
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(32, 32)
        if not icon.isNull():
            pixmap = icon.pixmap(QSize(32, 32))
            self._icon_lbl.setPixmap(pixmap)
            
        self._icon_lbl.setObjectName("icon_lbl")
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._icon_lbl)

        # Center Column (Name)
        clean_name = display_name
        if not clean_name or clean_name.lower().endswith(".exe"):
            try:
                from utils.win_utils import clean_fallback_name
                cleaned = clean_fallback_name(self.process_name)
                if cleaned:
                    clean_name = cleaned
            except Exception:
                pass

        self._name_lbl = QLabel(clean_name)
        self._name_lbl.setObjectName("name_lbl")
        self._name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._name_lbl, 1)
        
        # Right Column (Duration)
        engine = AnalyticsEngine()
        self._dur_lbl = QLabel(engine.format_duration_short(duration_s))
        self._dur_lbl.setObjectName("dur_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._dur_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._dur_lbl)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()
        
        icon_bg = "transparent"
        icon_border = "none"
        
        self.setStyleSheet(f"""
            SimpleAppRow {{
                background-color: transparent;
                border-radius: {ds.RADIUS['sm']}px;
            }}
            QLabel#icon_lbl {{ 
                background-color: {icon_bg}; 
                border: {icon_border};
                border-radius: {ds.RADIUS['sm']}px; 
            }}
            QLabel#name_lbl {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 500; }}
            QLabel#dur_lbl {{ color: {tm.color('text_sub')}; font-size: 13px; font-weight: 500; }}
        """)
