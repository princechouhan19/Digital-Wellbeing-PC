"""
app_row.py — Premium application usage row for Top Applications list on Home Dashboard.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout,
)

from core.constants import CATEGORY_COLORS, AppCategory
from utils.icon_provider import AppIconProvider
from analytics.engine import AnalyticsEngine

class AppUsageRow(QFrame):
    """A row widget representing app usage with icon, name, category, duration, and progress bar."""

    app_clicked = Signal(str)

    def __init__(
        self,
        rank: int,
        process_name: str,
        display_name: str,
        category: AppCategory | str,
        duration_s: float,
        max_duration_s: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.process_name = process_name
        self.setObjectName("app_row")
        
        # Store for re-rendering
        self._rank = rank
        self._display_name = display_name
        self._category = category
        self._duration_s = duration_s
        self._max_duration_s = max_duration_s
        
        self._setup_ui(rank, display_name, category, duration_s, max_duration_s)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.app_clicked.emit(self.process_name)
        super().mousePressEvent(event)

    def _setup_ui(
        self, rank: int, display_name: str, category: AppCategory | str, duration_s: float, max_duration_s: float
    ) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        # Rank removed per user request

        # App Icon
        icon_provider = AppIconProvider()
        icon = icon_provider.get_icon(self.process_name)
        
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(32, 32)
        if not icon.isNull():
            pixmap = icon.pixmap(QSize(32, 32))
            self._icon_lbl.setPixmap(pixmap)
        else:
            self._icon_lbl.setObjectName("icon_lbl")
        layout.addWidget(self._icon_lbl)

        # Center Column (Name + Badge + Progress)
        center_layout = QVBoxLayout()
        center_layout.setSpacing(4)
        
        name_cat_layout = QHBoxLayout()
        name_cat_layout.setSpacing(8)
        
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
        name_cat_layout.addWidget(self._name_lbl)
        name_cat_layout.addStretch()
        
        center_layout.addLayout(name_cat_layout)
        
        # Progress Bar
        self._bar = QProgressBar()
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setObjectName("app_progress")
        
        pct = int((duration_s / max_duration_s) * 100) if max_duration_s > 0 else 0
        self._bar.setValue(pct)
        center_layout.addWidget(self._bar)
        
        layout.addLayout(center_layout, 1)

        # Right Column (Duration + Percentage)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        engine = AnalyticsEngine()
        self._dur_lbl = QLabel(engine.format_duration_short(duration_s))
        self._dur_lbl.setObjectName("dur_lbl")
        self._dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(self._dur_lbl)
        
        self._pct_lbl = QLabel(f"{pct}%")
        self._pct_lbl.setObjectName("pct_lbl")
        self._pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(self._pct_lbl)
        
        layout.addLayout(right_layout)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager, get_app_color
        tm = ThemeManager.instance()
        
        cat_enum = self._category if isinstance(self._category, AppCategory) else None
        
        # Use deterministic app color
        app_color = get_app_color(self.process_name)
        
        self.setStyleSheet(f"""
            AppUsageRow#app_row {{
                background-color: transparent;
                border-radius: 8px;
            }}
            AppUsageRow#app_row:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QLabel#rank_lbl {{ color: {tm.color('text_muted')}; font-size: 13px; font-weight: 600; min-width: 24px; }}
            QLabel#icon_lbl {{ background-color: transparent; border: none; }}
            QLabel#name_lbl {{ color: {tm.color('text_main')}; font-size: 14px; font-weight: 700; }}
            QLabel#dur_lbl {{ color: {tm.color('text_main')}; font-size: 14px; font-weight: 700; }}
            QLabel#pct_lbl {{ color: {tm.color('text_sub')}; font-size: 11px; }}
            QProgressBar#app_progress {{ background-color: {tm.color('border')}; border-radius: 3px; }}
            QProgressBar#app_progress::chunk {{ background-color: {app_color}; border-radius: 3px; }}
        """)
