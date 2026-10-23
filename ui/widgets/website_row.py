"""
website_row.py — Sleek, responsive website usage row for Digital Wellbeing UI.

Displays:
- Real website logo/favicon fetched dynamically via WebsiteIconProvider
- Domain name with typography matching the design system
- Optional browser badge (e.g. Chrome, Edge, Brave)
- Progress bar displaying share of browser or overall web activity
- Formatted duration (e.g. 1h 24m)
- Interactive 'Set Limit' action button
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager
from utils.website_icon_provider import WebsiteIconProvider


class WebsiteUsageRow(QFrame):
    """A row widget representing website usage with logo, domain, duration, and limit shortcut."""

    website_clicked = Signal(str)      # domain
    set_limit_requested = Signal(str)  # domain

    def __init__(
        self,
        domain: str,
        duration_s: float,
        max_duration_s: float,
        browser_process: str = "",
        browsers: Optional[list[str]] = None,
        rank: Optional[int] = None,
        session_count: int = 0,
        show_limit_button: bool = True,
        limit_s: int = 0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.domain = domain
        self._duration_s = duration_s
        self._max_duration_s = max(max_duration_s, 1.0)
        self._browser_process = browser_process
        self._browsers = browsers or ([browser_process] if browser_process else [])
        self._rank = rank
        self._session_count = session_count
        self._show_limit_button = show_limit_button
        self._limit_s = limit_s
        self.setObjectName("website_usage_row")

        self._setup_ui()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.is_dark)

        # Connect to icon ready signal for live logo updates
        self._provider = WebsiteIconProvider()
        self._provider.icon_ready.connect(self._on_icon_ready)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.website_clicked.emit(self.domain)
        super().mousePressEvent(event)

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # 0. Rank Number (optional)
        if self._rank is not None:
            self._rank_lbl = QLabel(str(self._rank))
            self._rank_lbl.setObjectName("rank_lbl")
            self._rank_lbl.setFixedWidth(20)
            self._rank_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self._rank_lbl)

        # 1. Favicon / Logo Container
        self._icon_container = QFrame()
        self._icon_container.setFixedSize(36, 36)
        self._icon_container.setObjectName("logo_container")
        icon_layout = QHBoxLayout(self._icon_container)
        icon_layout.setContentsMargins(2, 2, 2, 2)
        icon_layout.setSpacing(0)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(32, 32)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self._icon_lbl)
        layout.addWidget(self._icon_container)

        # Load initial icon (disk/memory or high-res letter fallback avatar)
        provider = WebsiteIconProvider()
        icon = provider.get_icon(self.domain, size=32)
        if not icon.isNull():
            self._icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))

        # 2. Domain & Details Column
        center_layout = QVBoxLayout()
        center_layout.setSpacing(4)

        top_line = QHBoxLayout()
        top_line.setSpacing(8)

        self._domain_lbl = QLabel(self.domain)
        self._domain_lbl.setObjectName("domain_lbl")
        top_line.addWidget(self._domain_lbl)

        # Browser Badges (shows all browsers used for this domain!)
        if self._browsers:
            from tracker.categorizer import display_name
            shown_browsers = self._browsers[:3]
            for b in shown_browsers:
                b_name = display_name(b).replace(" Browser", "")
                badge = QLabel(b_name)
                badge.setObjectName("browser_badge")
                top_line.addWidget(badge)
            if len(self._browsers) > 3:
                more_badge = QLabel(f"+{len(self._browsers) - 3}")
                more_badge.setObjectName("browser_badge")
                top_line.addWidget(more_badge)

        if self._session_count > 0:
            sess_text = f"• {self._session_count} visit{'s' if self._session_count != 1 else ''}"
            lbl_sess = QLabel(sess_text)
            lbl_sess.setObjectName("session_count_lbl")
            top_line.addWidget(lbl_sess)

        top_line.addStretch()
        center_layout.addLayout(top_line)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("website_progress")
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setRange(0, 1000)
        pct = min(1.0, max(0.0, self._duration_s / self._max_duration_s))
        self._progress_bar.setValue(int(pct * 1000))
        center_layout.addWidget(self._progress_bar)

        layout.addLayout(center_layout, 1)

        # 3. Duration text
        dur_str = AnalyticsEngine.format_duration_short(self._duration_s)
        self._duration_lbl = QLabel(dur_str)
        self._duration_lbl.setObjectName("duration_lbl")
        layout.addWidget(self._duration_lbl)

        # 4. Action Button (Set Limit or Show Limit)
        if self._show_limit_button:
            if self._limit_s > 0:
                lim_text = AnalyticsEngine.format_duration_short(self._limit_s)
                self._btn_limit = QPushButton(f"Limit: {lim_text}")
                self._btn_limit.setObjectName("btn_limit_active")
            else:
                self._btn_limit = QPushButton("Set Limit")
                self._btn_limit.setObjectName("btn_limit")
            self._btn_limit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._btn_limit.clicked.connect(lambda: self.set_limit_requested.emit(self.domain))
            layout.addWidget(self._btn_limit)

    def _on_icon_ready(self, domain: str, icon: QIcon) -> None:
        if WebsiteIconProvider.normalize_domain(domain) == WebsiteIconProvider.normalize_domain(self.domain):
            if not icon.isNull():
                self._icon_lbl.setPixmap(icon.pixmap(QSize(32, 32)))

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        bg_card = tm.color("card_bg")
        hover_bg = tm.color("card_hover")
        border = tm.color("border")
        border_hover = tm.color("border_hover")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")

        container_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.03)"
        badge_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        badge_color = tm.color("text_muted")

        self.setStyleSheet(f"""
            QFrame#website_usage_row {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QFrame#website_usage_row:hover {{
                background-color: {hover_bg};
                border: 1px solid {border_hover};
            }}
            QFrame#logo_container {{
                background-color: {container_bg};
                border-radius: 8px;
            }}
            QLabel#domain_lbl {{
                font-size: 14px;
                font-weight: 700;
                color: {text_main};
                border: none;
                background: transparent;
            }}
            QLabel#browser_badge {{
                font-size: 11px;
                font-weight: 600;
                color: {badge_color};
                background-color: {badge_bg};
                border-radius: 4px;
                padding: 1px 6px;
                border: none;
            }}
            QLabel#duration_lbl {{
                font-size: 13px;
                font-weight: 600;
                color: {text_main};
                border: none;
                background: transparent;
            }}
            QProgressBar#website_progress {{
                background-color: {container_bg};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar#website_progress::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
            QLabel#rank_lbl {{
                font-size: 13px;
                font-weight: 700;
                color: {text_sub};
                border: none;
                background: transparent;
            }}
            QLabel#session_count_lbl {{
                font-size: 11px;
                color: {text_sub};
                border: none;
                background: transparent;
            }}
            QPushButton#btn_limit {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 6px;
                color: {accent};
                font-size: 12px;
                font-weight: 600;
                padding: 5px 12px;
            }}
            QPushButton#btn_limit:hover {{
                background-color: {accent};
                color: white;
                border: 1px solid {accent};
            }}
            QPushButton#btn_limit_active {{
                background-color: rgba(10, 132, 255, 0.15);
                border: 1px solid {accent};
                border-radius: 6px;
                color: {accent};
                font-size: 12px;
                font-weight: 700;
                padding: 5px 12px;
            }}
            QPushButton#btn_limit_active:hover {{
                background-color: {accent};
                color: white;
            }}
        """)
