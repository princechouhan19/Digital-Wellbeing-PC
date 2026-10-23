"""
category_details.py — Detailed view of applications within a category.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QProgressBar
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name
from ui.widgets.app_row import AppUsageRow


class CategoryDetailsPage(QWidget):
    """Detailed view for a specific category showing apps."""
    
    request_app_details = Signal(str)

    def __init__(self, on_back: Callable[[], None], parent=None) -> None:
        super().__init__(parent)
        self._on_back = on_back
        self._engine = AnalyticsEngine()
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 24px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#total_time {{ font-size: 16px; font-weight: 700; color: {tm.color('success_text')}; }}
            QLabel#placeholder {{ color: {tm.color('text_sub')}; padding: 24px; }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 18px;
                font-size: 20px;
                font-weight: 400;
                color: {tm.color('text_sub')};
                padding: 0;
            }}
            QPushButton#btn_secondary:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_secondary:pressed {{
                background-color: {tm.color('border')};
                color: {tm.color('text_main')};
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
        btn_back = FluentButton("", variant="tinted")
        btn_back.set_icon_name("back", size=15)
        btn_back.setFixedSize(36, 36)
        btn_back.clicked.connect(self._on_back)
        hdr_row.addWidget(btn_back)
        
        self._lbl_title = QLabel("Category Details")
        self._lbl_title.setObjectName("page_title")
        hdr_row.addWidget(self._lbl_title)
        
        self._lbl_total_time = QLabel()
        self._lbl_total_time.setObjectName("total_time")
        hdr_row.addStretch()
        hdr_row.addWidget(self._lbl_total_time)
        
        layout.addLayout(hdr_row)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._apps_layout = QVBoxLayout(inner)
        self._apps_layout.setContentsMargins(0, 0, 0, 0)
        self._apps_layout.setSpacing(10)
        scroll.setWidget(inner)
        
        layout.addWidget(scroll, 1)

    def set_data(self, category_name: str, all_app_data: list, total_time_s: float) -> None:
        self._lbl_title.setText(f"{category_name} Details")
        
        # Filter apps if category is not "All Categories"
        apps = all_app_data
        if category_name != "All Categories":
            apps = [a for a in all_app_data if a.get("category", "") == category_name]
            
        cat_total = sum(a.get("total_s", 0) for a in apps)
        self._lbl_total_time.setText(f"Total: {self._engine.format_duration(cat_total)}")
        
        while self._apps_layout.count():
            item = self._apps_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        apps.sort(key=lambda x: x.get("total_s", 0), reverse=True)
        
        if not apps:
            placeholder = QLabel(f"No applications found in {category_name}.")
            placeholder.setObjectName("placeholder")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._apps_layout.addWidget(placeholder)
            return

        for idx, app in enumerate(apps):
            dur = app.get("total_s", 0)
            
            from core.constants import AppCategory
            try:
                cat = AppCategory(app.get("category", "Other"))
            except ValueError:
                cat = AppCategory.OTHER
                
            row = AppUsageRow(
                rank=idx + 1,
                process_name=app.get("process_name", "Unknown"),
                display_name=get_display_name(app.get("process_name", "Unknown")),
                category=cat,
                duration_s=dur,
                max_duration_s=cat_total
            )
            row.mousePressEvent = lambda e, name=app.get("process_name"): self.request_app_details.emit(name)
            self._apps_layout.addWidget(row)
            
        self._apps_layout.addStretch()
