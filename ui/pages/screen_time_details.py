"""
screen_time_details.py — Detailed Screen Time View for Digital Wellbeing.
"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from datetime import date
import json

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from ui.widgets.charts import HourlyIntensityChart
from ui.widgets.app_row import AppUsageRow
from tracker.categorizer import display_name as get_display_name
from core.constants import AppCategory


class ExpandableCategoryList(QFrame):
    """An expandable list of applications for a specific category."""
    
    app_clicked = Signal(str)

    def __init__(self, category_name: str, apps: list[dict], max_dur: float, parent=None):
        super().__init__(parent)
        self.setObjectName("expandable_category")
        
        self._expanded = False
        self._apps = apps
        self._max_dur = max_dur
        self._category_name = category_name
        
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        
    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QFrame#expandable_category {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#expand_icon {{ color: {tm.color('accent')}; font-size: 14px; }}
            QLabel#expand_title {{ font-size: 15px; font-weight: 600; color: {tm.color('text_main')}; }}
            QLabel#expand_time {{ font-size: 14px; color: {tm.color('text_sub')}; }}
        """)

    def _setup_ui(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        
        # Header (Clickable)
        self._header = QWidget()
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self._icon_lbl = QLabel("▸")
        self._icon_lbl.setObjectName("expand_icon")
        
        self._title_lbl = QLabel(self._category_name.title())
        self._title_lbl.setObjectName("expand_title")
        
        total_s = sum([app.get("total_s", 0) for app in self._apps])
        self._time_lbl = QLabel(AnalyticsEngine.format_duration_short(total_s))
        self._time_lbl.setObjectName("expand_time")
        
        header_layout.addWidget(self._icon_lbl)
        header_layout.addWidget(self._title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self._time_lbl)
        
        self._layout.addWidget(self._header)
        
        # Apps container
        self._apps_container = QWidget()
        self._apps_layout = QVBoxLayout(self._apps_container)
        self._apps_layout.setContentsMargins(24, 12, 0, 0)
        self._apps_layout.setSpacing(8)
        
        for idx, app in enumerate(self._apps):
            row = AppUsageRow(
                rank=idx + 1,
                process_name=app["process_name"],
                display_name=get_display_name(app["process_name"]),
                category=AppCategory(app.get("category", "Uncategorized")),
                duration_s=app["total_s"],
                max_duration_s=self._max_dur,
            )
            # Make the row clickable for details
            row.mousePressEvent = lambda e, name=app["process_name"]: self.app_clicked.emit(name)
            self._apps_layout.addWidget(row)
            
        self._apps_container.setVisible(False)
        self._layout.addWidget(self._apps_container)
        
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.pos().y() <= self._header.height() + 16:
            self._expanded = not self._expanded
            self._apps_container.setVisible(self._expanded)
            self._icon_lbl.setText("▾" if self._expanded else "▸")


class ScreenTimeDetailsPage(QWidget):
    """Detailed view of today's screen time, categories, and timeline."""

    request_app_details = Signal(str)
    back_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._engine = AnalyticsEngine()
        self._repo = Repository()
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#total_time {{ font-size: 32px; font-weight: 700; color: {tm.color('accent')}; }}
            QLabel#section_header {{ font-size: 18px; font-weight: 700; color: {tm.color('text_main')}; }}
        """)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setSpacing(20)
        
        from ui.widgets.back_header import BackHeader
        self._back_header = BackHeader("Screen Time Details", "Today's complete usage breakdown")
        self._back_header.back_requested.connect(self.back_requested.emit)
        
        header.addWidget(self._back_header)

        header.addStretch()
        
        self._total_time_lbl = QLabel("0h 00m")
        self._total_time_lbl.setObjectName("total_time")
        header.addWidget(self._total_time_lbl)

        main_layout.addLayout(header)
        main_layout.addSpacing(32)

        # Scroll Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(32)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # Timeline Chart
        self._chart = HourlyIntensityChart()
        self._inner_layout.addWidget(self._chart)

        # Most Used Applications
        apps_lbl = QLabel("Most Used Applications")
        apps_lbl.setObjectName("section_header")
        self._inner_layout.addWidget(apps_lbl)
        
        self._apps_container = QVBoxLayout()
        self._apps_container.setSpacing(8)
        self._inner_layout.addLayout(self._apps_container)
        
        self._inner_layout.addSpacing(16)
        
        # Category Breakdown
        cats_lbl = QLabel("Category Breakdown")
        cats_lbl.setObjectName("section_header")
        self._inner_layout.addWidget(cats_lbl)
        
        self._cats_container = QVBoxLayout()
        self._cats_container.setSpacing(12)
        self._inner_layout.addLayout(self._cats_container)
        
        self._inner_layout.addStretch()

    def refresh(self, target_date: Optional[date] = None) -> None:
        if target_date is None or target_date == date.today():
            self._back_header._subtitle_lbl.setText("Today's complete usage breakdown")
            summary = self._engine.get_today_summary()
            total_time_s = summary.total_screen_time_s
            top_apps = summary.top_apps
            hourly = self._engine.get_hourly_chart_data(date.today())
        else:
            self._back_header._subtitle_lbl.setText(f"Complete usage breakdown for {target_date.strftime('%B %d, %Y')}")
            stat = self._repo.get_daily_stat(target_date)
            if stat:
                total_time_s = stat.total_screen_time_s
                top_apps = json.loads(stat.app_usage_json)
                hourly = self._engine.get_hourly_chart_data(target_date)
            else:
                total_time_s = 0
                top_apps = []
                hourly = []

        self._total_time_lbl.setText(self._engine.format_duration(total_time_s))
        
        # Update Chart
        self._chart.update_data(hourly)
        
        # Update Top Apps (All)
        while self._apps_container.count():
            item = self._apps_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        max_dur = top_apps[0]["total_s"] if top_apps else 1.0
        
        for idx, app in enumerate(top_apps):
            row = AppUsageRow(
                rank=idx + 1,
                process_name=app["process_name"],
                display_name=get_display_name(app["process_name"]),
                category=AppCategory(app.get("category", "Uncategorized")),
                duration_s=app["total_s"],
                max_duration_s=max_dur,
            )
            row.mousePressEvent = lambda e, name=app["process_name"]: self.request_app_details.emit(name)
            self._apps_container.addWidget(row)
            
        # Update Categories
        while self._cats_container.count():
            item = self._cats_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Group apps by category
        from collections import defaultdict
        cats_dict = defaultdict(list)
        for app in top_apps:
            cat = app.get("category", "Uncategorized")
            cats_dict[cat].append(app)
            
        # Sort categories by total duration
        sorted_cats = sorted(cats_dict.items(), key=lambda x: sum(a["total_s"] for a in x[1]), reverse=True)
        
        for cat_name, apps in sorted_cats:
            cat_view = ExpandableCategoryList(cat_name, apps, max_dur)
            cat_view.app_clicked.connect(self.request_app_details.emit)
            self._cats_container.addWidget(cat_view)
