"""
screen_time_card.py — Large Interactive Screen Time Card for Digital Wellbeing Dashboard.
Premium Samsung/Apple inspired design with glassmorphism.
"""

from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name
from core.constants import AppCategory
from ui.widgets.simple_app_row import SimpleAppRow
from ui.widgets.donut_chart import DonutChart


from ui.widgets.fluent import FluentCard

class ActiveScreenTimeCard(FluentCard):
    """Large interactive card displaying today's screen time, donut chart, and top apps."""

    card_clicked = Signal()
    app_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._app_rows = {}
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        from ui.widgets.fluent import FluentLabel
        self._title = FluentLabel("Today's Active Screen Time", FluentLabel.Style.HEADING)
        
        header_layout.addWidget(self._title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Content Row (Donut + Top Apps)
        content_row = QHBoxLayout()
        content_row.setSpacing(12)

        # Left: Donut Chart & Total Time
        self._donut = DonutChart()
        self._donut.setMinimumSize(220, 220)
        self._donut.segment_hovered.connect(self._on_donut_segment_hovered)
        content_row.addWidget(self._donut, 0, Qt.AlignmentFlag.AlignCenter)

        # Right: Lists
        self._lists_layout = QVBoxLayout()
        self._lists_layout.setSpacing(8)
        self._lists_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(4)
        self._lists_layout.addLayout(self._apps_layout)

        self._lists_layout.addStretch()

        content_row.addLayout(self._lists_layout, 1)

        layout.addLayout(content_row)

    def _apply_theme(self, is_dark: bool) -> None:
        pass

    def set_data(self, active_s: float, category_breakdown: List[dict], top_apps: List[dict]) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        segments = []
        if not top_apps or active_s <= 0:
            segments = [("Active", 1.0, tm.color('accent'))]
        else:
            sorted_apps = sorted(top_apps, key=lambda x: float(x.get("total_s", 0.0)), reverse=True)
            fluent_palette = ["#0A84FF", "#30D158", "#64D2FF"]
            accounted_s = 0.0
            for idx, item in enumerate(sorted_apps[:3]):
                dur = float(item.get("total_s", 0.0))
                if dur > 0:
                    color = fluent_palette[idx] if idx < len(fluent_palette) else tm.color('text_muted')
                    segments.append((get_display_name(item["process_name"]), dur, color))
                    accounted_s += dur
            
            other_dur = active_s - accounted_s
            if other_dur > 0:
                segments.append(("Other", other_dur, tm.color('text_muted')))

        # Update Donut
        formatted_total = AnalyticsEngine.format_duration_short(active_s)
        self._donut.set_data(segments, center_text=formatted_total, center_subtext="Active Time")
        
        # Update Top Apps
        self._app_rows.clear()
        while self._apps_layout.count():
            item = self._apps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not top_apps:
            from ui.widgets.fluent import FluentLabel
            placeholder = FluentLabel("No application usage recorded today.", FluentLabel.Style.MUTED)
            self._apps_layout.addWidget(placeholder)
        else:
            fluent_palette = ["#0A84FF", "#30D158", "#64D2FF"]
            for idx, s in enumerate(top_apps[:3]):
                display_name = get_display_name(s["process_name"])
                color = fluent_palette[idx] if idx < len(fluent_palette) else tm.color('text_muted')
                row = SimpleAppRow(
                    process_name=s["process_name"],
                    display_name=display_name,
                    duration_s=s["total_s"],
                    legend_color=color
                )
                self._app_rows[display_name] = row
                row.clicked.connect(lambda pname=s["process_name"]: self._on_app_row_clicked(pname))
                row.hover_entered.connect(self._donut.set_highlighted_segment)
                row.hover_left.connect(lambda _: self._donut.set_highlighted_segment(""))
                self._apps_layout.addWidget(row)

    def _on_donut_segment_hovered(self, label: str) -> None:
        for name, row in self._app_rows.items():
            if name == label:
                row.set_highlighted(True)
            else:
                row.set_highlighted(False)

    def _on_app_row_clicked(self, pname: str) -> None:
        print("App clicked signal emitted (ActiveScreenTimeCard)")
        self.app_clicked.emit(pname)
