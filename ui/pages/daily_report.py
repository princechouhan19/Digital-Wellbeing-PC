"""
daily_report.py — Detailed historical day report.
"""

from __future__ import annotations

import json
from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QGridLayout, QSizePolicy
)

from analytics.engine import AnalyticsEngine
from database.models import DailyStat
from core.constants import AppCategory
from tracker.categorizer import display_name as get_display_name
from ui.widgets.donut_chart import CategoryBreakdownCard
from ui.widgets.app_row import AppUsageRow


class DailyReportPage(QWidget):
    """Detailed view for a specific historical day."""
    
    request_category_details = Signal(str, list, float)
    request_app_details = Signal(str)

    def __init__(self, on_back: Callable[[], None], parent=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._engine = AnalyticsEngine()
        self._stat: Optional[DailyStat] = None
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 24px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#section_header {{ font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#val_total {{ font-size: 16px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#val_active {{ font-size: 14px; font-weight: 600; color: {tm.color('success_text')}; }}
            QLabel#val_idle {{ font-size: 14px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#val_top_app {{ font-size: 14px; font-weight: 600; color: {tm.color('accent')}; }}
            QLabel#val_unlocks {{ font-size: 14px; font-weight: 600; color: {tm.color('info_text')}; }}
            QPushButton#btn_secondary {{
                background-color: {tm.color('card_bg')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton#btn_secondary:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QFrame#v2_card {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
        """)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Header
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(16)
        
        from ui.widgets.fluent import FluentButton
        btn_back = FluentButton("Back", variant="tinted")
        btn_back.set_icon_name("back", size=14)
        btn_back.setFixedWidth(88)
        btn_back.clicked.connect(self._on_back)
        hdr_row.addWidget(btn_back)
        
        self._lbl_title = QLabel("Daily Report")
        self._lbl_title.setObjectName("page_title")
        hdr_row.addWidget(self._lbl_title)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._content_layout = QVBoxLayout(inner)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(20)
        scroll.setWidget(inner)
        
        # Overview Cards
        overview_row = QHBoxLayout()
        overview_row.setSpacing(20)
        
        # Breakdown Card
        self._breakdown_card = CategoryBreakdownCard("🍩 Category Breakdown")
        self._breakdown_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self._breakdown_card.mousePressEvent = self._on_category_card_clicked
        overview_row.addWidget(self._breakdown_card, 1)
        
        # Stats Card
        stats_frame = QFrame()
        stats_frame.setObjectName("v2_card")
        s_l = QVBoxLayout(stats_frame)
        s_l.setContentsMargins(24, 20, 24, 20)
        s_l.setSpacing(14)
        
        s_hdr = QLabel("Key Metrics")
        s_hdr.setObjectName("section_header")
        s_l.addWidget(s_hdr)
        
        self._lbl_total = QLabel()
        self._lbl_total.setObjectName("val_total")
        
        self._lbl_active = QLabel()
        self._lbl_active.setObjectName("val_active")
        
        self._lbl_idle = QLabel()
        self._lbl_idle.setObjectName("val_idle")
        
        self._lbl_top_app = QLabel()
        self._lbl_top_app.setObjectName("val_top_app")
        
        self._lbl_unlocks = QLabel()
        self._lbl_unlocks.setObjectName("val_unlocks")
        
        s_l.addWidget(self._lbl_total)
        s_l.addWidget(self._lbl_active)
        s_l.addWidget(self._lbl_idle)
        s_l.addWidget(self._lbl_top_app)
        s_l.addWidget(self._lbl_unlocks)
        s_l.addStretch()
        
        overview_row.addWidget(stats_frame, 1)
        self._content_layout.addLayout(overview_row)
        
        # Top Apps Table
        apps_hdr = QLabel("Top Applications")
        apps_hdr.setObjectName("section_header")
        self._content_layout.addWidget(apps_hdr)
        
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(6)
        self._content_layout.addLayout(self._apps_layout)
        
        

        self._content_layout.addStretch()
        layout.addWidget(scroll, 1)

    def set_data(self, stat: DailyStat) -> None:
        self._stat = stat
        self._lbl_title.setText(stat.date.strftime("%A, %B %d, %Y"))
        
        self._lbl_total.setText(f"Total Screen Time: {self._engine.format_duration(stat.total_screen_time_s)}")
        self._lbl_active.setText(f"Active Focus Time: {self._engine.format_duration(stat.active_time_s)}")
        self._lbl_idle.setText(f"Idle Inactivity: {self._engine.format_duration(stat.idle_time_s)}")
        
        top_app = get_display_name(stat.top_app) if stat.top_app else "None"
        self._lbl_top_app.setText(f"Most Used App: {top_app}")
        self._lbl_unlocks.setText(f"Device Unlocks: {stat.unlock_count}")
        
        categories = json.loads(stat.category_usage_json)
        self._breakdown_card.set_data(categories, stat.active_time_s, stat.total_screen_time_s)
        
        # Apps
        while self._apps_layout.count():
            item = self._apps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        apps = json.loads(stat.app_usage_json)
        max_dur = apps[0].get("total_s", 1.0) if apps else 1.0
        for idx, app in enumerate(apps):
            row = self._create_app_row(idx + 1, app, max_dur)
            self._apps_layout.addWidget(row)
            
            

    def _create_app_row(self, rank: int, app_data: dict, max_dur: float) -> QFrame:
        try:
            cat = AppCategory(app_data.get("category", "Other"))
        except ValueError:
            cat = AppCategory.OTHER
            
        row = AppUsageRow(
            rank=rank,
            process_name=app_data.get("process_name", "Unknown"),
            display_name=get_display_name(app_data.get("process_name", "Unknown")),
            category=cat,
            duration_s=app_data.get("total_s", 0),
            max_duration_s=max_dur
        )
        row.mousePressEvent = lambda event, pn=app_data.get("process_name"): self.request_app_details.emit(pn)
        return row
        
    def _on_category_card_clicked(self, event) -> None:
        if self._stat:
            categories = json.loads(self._stat.category_usage_json)
            apps = json.loads(self._stat.app_usage_json)
            self.request_category_details.emit("All Categories", apps, self._stat.active_time_s)
