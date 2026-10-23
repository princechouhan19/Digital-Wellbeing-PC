"""
timeline_row.py — Clickable timeline row widget for displaying individual application sessions.
"""

from __future__ import annotations

from datetime import datetime
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)

from utils.icon_provider import AppIconProvider
from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name

class TimelineRow(QFrame):
    """A row widget representing a specific application session in the timeline."""
    
    row_clicked = Signal(str)

    def __init__(self, s_data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.process_name = s_data.get("process_name", "Unknown")
        self.setObjectName("timeline_row")
        self._setup_ui(s_data)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, s_data: dict) -> None:
        r_l = QHBoxLayout(self)
        r_l.setContentsMargins(16, 12, 16, 12)
        r_l.setSpacing(14)

        start_dt = datetime.fromisoformat(s_data["start_time"])
        time_str = start_dt.strftime("%I:%M %p")
        if "duration_s" in s_data:
            from datetime import timedelta
            end_dt = start_dt + timedelta(seconds=s_data["duration_s"])
            time_str += f"\n{end_dt.strftime('%I:%M %p')}"
        
        self._time_lbl = QLabel(time_str)
        self._time_lbl.setObjectName("time_lbl")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        r_l.addWidget(self._time_lbl)

        # App Icon
        icon_provider = AppIconProvider()
        icon = icon_provider.get_icon(self.process_name)
        
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(28, 28)
        if not icon.isNull():
            pixmap = icon.pixmap(QSize(28, 28))
            self._icon_lbl.setPixmap(pixmap)
        else:
            self._icon_lbl.setObjectName("icon_lbl")
        r_l.addWidget(self._icon_lbl)

        self._name_lbl = QLabel(get_display_name(self.process_name))
        self._name_lbl.setObjectName("name_lbl")

        self._title_lbl = QLabel(s_data.get("window_title", "Active Window"))
        self._title_lbl.setObjectName("title_lbl")
        
        # Ensure long titles don't stretch the layout infinitely
        from PySide6.QtGui import QFontMetrics
        metrics = QFontMetrics(self._title_lbl.font())
        elided_title = metrics.elidedText(self._title_lbl.text(), Qt.TextElideMode.ElideRight, 350)
        self._title_lbl.setText(elided_title)

        v_b = QVBoxLayout()
        v_b.setSpacing(2)
        v_b.addWidget(self._name_lbl)
        v_b.addWidget(self._title_lbl)
        r_l.addLayout(v_b, 1)

        engine = AnalyticsEngine()
        self._dur_lbl = QLabel(engine.format_duration_short(s_data.get("duration_s", 0)))
        self._dur_lbl.setObjectName("dur_lbl")
        r_l.addWidget(self._dur_lbl)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            TimelineRow#timeline_row {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            TimelineRow#timeline_row:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#time_lbl {{ font-weight: 700; color: {tm.color('accent')}; min-width: 70px; font-size: 11px; }}
            QLabel#icon_lbl {{ background-color: {tm.color('border')}; border-radius: 6px; }}
            QLabel#name_lbl {{ font-weight: 700; color: {tm.color('text_main')}; font-size: 13px; }}
            QLabel#title_lbl {{ color: {tm.color('text_sub')}; font-size: 11px; }}
            QLabel#dur_lbl {{ font-weight: 700; color: {tm.color('text_main')}; font-size: 13px; }}
        """)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.row_clicked.emit(self.process_name)
