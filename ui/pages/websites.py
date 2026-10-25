"""
websites.py — Cross-Browser Website Tracking Dashboard for Digital Wellbeing.

Provides:
- Overall aggregated website tracking across all web browsers (Chrome, Brave, Edge, Firefox, Atlas, Comet, etc.)
- Multi-browser badge indicators showing which browsers a website was accessed from
- Time range filtering (Today, 7 Days, 30 Days)
- Browser filter dropdown (All Browsers vs. specific browser)
- Instant domain search filter
- Cross-browser website limit management
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtCore import QSize, QTimer, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from tracker.categorizer import display_name
from ui import design_system as ds
from ui.icons import get_icon
from ui.theme import ThemeManager
from ui.widgets.website_row import WebsiteUsageRow
from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog, WebsiteTimerItem


class WebsitesPage(QWidget):
    """Full-featured cross-browser website time tracking and limits page."""

    request_navigate = Signal(int)

    def __init__(self, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._protection_manager = protection_manager
        self._repo = Repository()
        self._engine = AnalyticsEngine()
        self._time_range: int = 1  # 1 = Today, 7 = 7 Days, 30 = 30 Days
        self._selected_browser: str = "*"  # "*" means all browsers combined
        self._search_query: str = ""
        self._cached_websites: list[dict] = []

        self._setup_ui()
        self.refresh()

        tm = ThemeManager.instance()
        tm.theme_changed.connect(self._apply_theme)
        self._apply_theme(tm.is_dark)

        # Live poll timer (updates every 3 seconds while page is open)
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(3000)
        self._live_timer.timeout.connect(self._on_live_tick)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()
        self._live_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._live_timer.stop()

    def on_data_changed(self) -> None:
        """Called automatically by MainWindow when tracking data updates."""
        self.refresh()

    def _on_live_tick(self) -> None:
        if self.isVisible():
            self.refresh(is_live=True)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("page_scroll")

        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(32, 28, 32, 28)
        self._content_layout.setSpacing(24)
        scroll.setWidget(self._content_widget)
        main_layout.addWidget(scroll)

        # ── 1. Page Header ──────────────────────────────────────
        hdr_layout = QHBoxLayout()
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)

        title = QLabel("Web Activity")
        title.setObjectName("page_title")
        subtitle = QLabel("Cross-browser website time tracking aggregated across all your browsers.")
        subtitle.setObjectName("page_subtitle")

        hdr_box.addWidget(title)
        hdr_box.addWidget(subtitle)
        hdr_layout.addLayout(hdr_box)
        hdr_layout.addStretch()

        self._btn_add_limit = QPushButton("+ Add Website Limit")
        self._btn_add_limit.setObjectName("accent_btn")
        self._btn_add_limit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_add_limit.clicked.connect(self._on_add_global_limit)
        hdr_layout.addWidget(self._btn_add_limit)

        self._content_layout.addLayout(hdr_layout)

        # ── 2. KPI Analytical Cards ─────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self._kpi_web_time = self._create_kpi_card("TOTAL WEB TIME", "0m", "globe", kpi_row)
        self._kpi_top_site = self._create_kpi_card("TOP WEBSITE", "-", "compass", kpi_row)
        self._kpi_active_browsers = self._create_kpi_card("ACTIVE BROWSERS", "0", "browser", kpi_row)
        self._kpi_total_sites = self._create_kpi_card("SITES VISITED", "0", "usage", kpi_row)
        self._content_layout.addLayout(kpi_row)

        # ── 3. Filter Bar (Range + Browser Combo + Search) ──────
        filter_card = QFrame()
        filter_card.setObjectName("v2_card")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(14)

        # Range Toggles
        self._range_group = QButtonGroup(self)
        range_box = QHBoxLayout()
        range_box.setSpacing(0)

        self._btn_today = QPushButton("Today")
        self._btn_today.setCheckable(True)
        self._btn_today.setChecked(True)
        self._btn_today.setObjectName("segment_btn_left")

        self._btn_7d = QPushButton("7 Days")
        self._btn_7d.setCheckable(True)
        self._btn_7d.setObjectName("segment_btn_mid")

        self._btn_30d = QPushButton("30 Days")
        self._btn_30d.setCheckable(True)
        self._btn_30d.setObjectName("segment_btn_right")

        self._range_group.addButton(self._btn_today, 1)
        self._range_group.addButton(self._btn_7d, 7)
        self._range_group.addButton(self._btn_30d, 30)

        range_box.addWidget(self._btn_today)
        range_box.addWidget(self._btn_7d)
        range_box.addWidget(self._btn_30d)
        filter_layout.addLayout(range_box)

        # Browser Dropdown
        self._browser_combo = QComboBox()
        self._browser_combo.setObjectName("browser_filter_combo")
        self._browser_combo.addItem("All Browsers (Aggregated)", "*")
        self._browser_combo.setMinimumWidth(210)
        self._browser_combo.currentIndexChanged.connect(self._on_browser_filter_changed)
        filter_layout.addWidget(self._browser_combo)

        filter_layout.addStretch()

        # Search Bar
        self._search_input = QLineEdit()
        self._search_input.setObjectName("search_input")
        self._search_input.setPlaceholderText("Search websites... (e.g. youtube, github)")
        self._search_input.setFixedWidth(280)
        self._search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self._search_input)

        self._range_group.idClicked.connect(self._on_range_changed)
        self._content_layout.addWidget(filter_card)

        # ── 4. Websites Usage List ──────────────────────────────
        sites_header_row = QHBoxLayout()
        self._lbl_sites_section = QLabel("Websites Visited")
        self._lbl_sites_section.setObjectName("section_header")
        sites_header_row.addWidget(self._lbl_sites_section)
        sites_header_row.addStretch()

        self._lbl_sites_count = QLabel("0 websites")
        self._lbl_sites_count.setObjectName("section_count_lbl")
        sites_header_row.addWidget(self._lbl_sites_count)
        self._content_layout.addLayout(sites_header_row)

        self._sites_card = QFrame()
        self._sites_card.setObjectName("v2_card")
        sites_card_layout = QVBoxLayout(self._sites_card)
        sites_card_layout.setContentsMargins(18, 16, 18, 16)
        sites_card_layout.setSpacing(8)

        self._sites_list_layout = QVBoxLayout()
        self._sites_list_layout.setSpacing(8)
        sites_card_layout.addLayout(self._sites_list_layout)
        self._content_layout.addWidget(self._sites_card)

        # ── 5. Active Limits Section ────────────────────────────
        self._limits_section = QFrame()
        self._limits_section.setObjectName("v2_card")
        self._limits_layout = QVBoxLayout(self._limits_section)
        self._limits_layout.setContentsMargins(18, 16, 18, 16)
        self._limits_layout.setSpacing(12)

        limits_hdr = QHBoxLayout()
        lbl_limits_title = QLabel("Active Website Limits")
        lbl_limits_title.setObjectName("section_header")
        limits_hdr.addWidget(lbl_limits_title)
        limits_hdr.addStretch()
        self._limits_layout.addLayout(limits_hdr)

        self._limits_list_layout = QVBoxLayout()
        self._limits_list_layout.setSpacing(8)
        self._limits_layout.addLayout(self._limits_list_layout)
        self._content_layout.addWidget(self._limits_section)

        self._content_layout.addStretch()

    def _create_kpi_card(self, title: str, default_val: str, icon_name: str, layout: QHBoxLayout) -> QLabel:
        tm = ThemeManager.instance()
        card = QFrame()
        card.setObjectName("v2_card")
        l = QVBoxLayout(card)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(6)

        top_h = QHBoxLayout()
        top_h.setSpacing(8)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("metric_hdr")
        top_h.addWidget(lbl_title)
        top_h.addStretch()

        ico = QLabel()
        ico.setPixmap(get_icon(icon_name, color=tm.color("text_muted"), size=16).pixmap(16, 16))
        top_h.addWidget(ico)
        l.addLayout(top_h)

        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val_success")
        l.addWidget(lbl_val)

        layout.addWidget(card, 1)
        return lbl_val

    def _on_range_changed(self, range_id: int) -> None:
        self._time_range = range_id
        self.refresh()

    def _on_browser_filter_changed(self, index: int) -> None:
        self._selected_browser = self._browser_combo.currentData() or "*"
        self.refresh()

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip().lower()
        self._render_website_rows()

    def refresh(self, is_live: bool = False) -> None:
        end_d = date.today()
        start_d = end_d - timedelta(days=self._time_range - 1)

        # Update distinct browsers combo (without breaking current selection)
        distinct_browsers = self._engine.get_distinct_browsers_for_range(start_d, end_d)
        current_data = self._browser_combo.currentData() or "*"
        
        # Block signals temporarily to prevent loop
        self._browser_combo.blockSignals(True)
        self._browser_combo.clear()
        self._browser_combo.addItem("All Browsers (Aggregated)", "*")
        for b in distinct_browsers:
            b_clean = display_name(b)
            self._browser_combo.addItem(b_clean, b)
        
        # Restore selection if still present
        idx = self._browser_combo.findData(current_data)
        if idx >= 0:
            self._browser_combo.setCurrentIndex(idx)
        else:
            self._browser_combo.setCurrentIndex(0)
            self._selected_browser = "*"
        self._browser_combo.blockSignals(False)

        # Fetch websites
        b_filter = None if self._selected_browser == "*" else self._selected_browser
        raw_websites = self._engine.get_top_websites_for_range(
            start=start_d, end=end_d, browser_process=b_filter, limit=100
        )
        self._cached_websites = raw_websites

        # Compute KPIs
        total_s = sum(w["total_s"] for w in raw_websites)
        self._kpi_web_time.setText(AnalyticsEngine.format_duration_short(total_s))

        if raw_websites:
            top_site = raw_websites[0]["domain"]
            self._kpi_top_site.setText(top_site)
        else:
            self._kpi_top_site.setText("-")

        browser_count = len(distinct_browsers)
        self._kpi_active_browsers.setText(f"{browser_count} Browser{'s' if browser_count != 1 else ''}")
        self._kpi_total_sites.setText(f"{len(raw_websites)} Sites")

        # Render website rows and limits
        self._render_website_rows()
        self._render_limits()

    def _render_website_rows(self) -> None:
        # Clear list
        while self._sites_list_layout.count():
            item = self._sites_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtered = self._cached_websites
        if self._search_query:
            filtered = [w for w in filtered if self._search_query in w["domain"].lower()]

        self._lbl_sites_count.setText(f"{len(filtered)} website{'s' if len(filtered) != 1 else ''}")

        if not filtered:
            tm = ThemeManager.instance()
            msg = (
                "No websites matched your search filter."
                if self._search_query
                else "No website visits recorded for this period yet.\nWeb activity from all your browsers will appear here automatically."
            )
            empty_lbl = QLabel(msg)
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(
                f"color: {tm.color('text_sub')}; font-size: 14px; padding: 40px; line-height: 1.5;"
            )
            self._sites_list_layout.addWidget(empty_lbl)
            return

        max_dur = max((w["total_s"] for w in filtered), default=1.0)
        limits_map = self._get_active_limits_map()

        for idx, w in enumerate(filtered, start=1):
            dom = w["domain"]
            limit_s = limits_map.get(dom, 0)
            row = WebsiteUsageRow(
                domain=dom,
                duration_s=w["total_s"],
                max_duration_s=max_dur,
                browsers=w.get("browser_list", []),
                rank=idx,
                session_count=w.get("session_count", 0),
                show_limit_button=bool(self._protection_manager),
                limit_s=limit_s,
            )
            row.set_limit_requested.connect(self._on_configure_limit)
            row.website_clicked.connect(self._on_configure_limit)
            self._sites_list_layout.addWidget(row)

    def _get_active_limits_map(self) -> dict[str, int]:
        if not self._protection_manager:
            return {}
        result = {}
        all_limits = self._protection_manager.website_limits.get_all_limits()
        for dom, rule in all_limits.items():
            result[dom] = rule.get("limit_seconds", 0)
        return result

    def _render_limits(self) -> None:
        while self._limits_list_layout.count():
            item = self._limits_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._protection_manager:
            self._limits_section.hide()
            return

        all_limits = self._protection_manager.website_limits.get_all_limits()
        if not all_limits:
            self._limits_section.hide()
            return

        self._limits_section.show()
        for domain, rule in all_limits.items():
            limit_s = rule.get("limit_seconds", 0)
            used_s = self._protection_manager.website_timer.get_time(domain)
            item = WebsiteTimerItem(domain, limit_s, used_s)
            item.edit_requested.connect(self._on_edit_limit)
            item.delete_requested.connect(self._on_delete_limit)
            self._limits_list_layout.addWidget(item)

    def _on_add_global_limit(self) -> None:
        self._on_configure_limit("")

    def _on_configure_limit(self, domain: str) -> None:
        if not self._protection_manager:
            return
        current_rule = self._protection_manager.website_limits.get_limit_rule("*", domain) or {}
        dialog = WebsiteTimerConfigDialog(
            parent=self.window(),
            domain=domain,
            limit_s=current_rule.get("limit_seconds", 0),
            browser_name="All Browsers (Cross-Browser)",
        )
        if dialog.exec():
            d_name, rule = dialog.get_data()
            if d_name:
                # Set cross-browser limit using wildcard "*"
                self._protection_manager.website_limits.set_limit_rule("*", d_name, rule)
                self.refresh()

    def _on_edit_limit(self, domain: str) -> None:
        self._on_configure_limit(domain)

    def _on_delete_limit(self, domain: str) -> None:
        if not self._protection_manager:
            return
        self._protection_manager.website_limits.remove_website_limit(domain)
        self.refresh()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        bg_card = tm.color("card_bg")
        border = tm.color("border")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        accent = tm.color("accent")
        input_bg = tm.color("input_bg")
        input_border = tm.color("input_border")

        self.setStyleSheet(f"""
            QScrollArea#page_scroll {{
                background-color: transparent;
                border: none;
            }}
            QFrame#v2_card {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel#page_title {{
                font-size: 26px;
                font-weight: 700;
                color: {text_main};
            }}
            QLabel#page_subtitle {{
                font-size: 13px;
                color: {text_sub};
            }}
            QLabel#section_header {{
                font-size: 17px;
                font-weight: 700;
                color: {text_main};
            }}
            QLabel#section_count_lbl {{
                font-size: 13px;
                font-weight: 600;
                color: {text_sub};
            }}
            QLabel#metric_hdr {{
                font-size: 11px;
                font-weight: 700;
                color: {text_sub};
                letter-spacing: 0.6px;
            }}
            QLabel#metric_val_success {{
                font-size: 22px;
                font-weight: 700;
                color: {text_main};
            }}
            QPushButton#accent_btn {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                padding: 9px 18px;
            }}
            QPushButton#accent_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QLineEdit#search_input {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 8px;
                color: {text_main};
                padding: 7px 12px;
                font-size: 13px;
            }}
            QLineEdit#search_input:focus {{
                border-color: {accent};
            }}
            QComboBox#browser_filter_combo {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 8px;
                color: {text_main};
                padding: 7px 12px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#segment_btn_left, QPushButton#segment_btn_mid, QPushButton#segment_btn_right {{
                background-color: {input_bg};
                border: 1px solid {border};
                color: {text_sub};
                font-size: 12px;
                font-weight: 600;
                padding: 6px 14px;
            }}
            QPushButton#segment_btn_left {{
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                border-right: none;
            }}
            QPushButton#segment_btn_mid {{
                border-radius: 0px;
                border-right: none;
            }}
            QPushButton#segment_btn_right {{
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QPushButton#segment_btn_left:checked, QPushButton#segment_btn_mid:checked, QPushButton#segment_btn_right:checked {{
                background-color: {accent};
                color: white;
                border-color: {accent};
            }}
        """)
