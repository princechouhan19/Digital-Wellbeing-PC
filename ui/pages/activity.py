"""
activity.py — Unified Activity & Trends Dashboard for Digital Wellbeing V2.
"""

from __future__ import annotations

import json
from datetime import date, timedelta, datetime
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget, QProgressBar,
    QButtonGroup, QRadioButton
)

from analytics.engine import AnalyticsEngine
from database.repository import Repository
from database.models import DailyStat
from tracker.categorizer import display_name as get_display_name
from ui.widgets.app_row import AppUsageRow
from ui.widgets.website_row import WebsiteUsageRow
from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
from ui.widgets.charts import DailyScreenTimeChart
from ui.widgets.donut_chart import CategoryBreakdownCard
from ui.pages.category_details import CategoryDetailsPage
from ui.pages.app_details import AppDetailsPage
from ui.widgets.insights_card import SmartInsightsCard
from settings.manager import SettingsManager
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
class ActivityPage(QWidget):
    """Interactive Analytics Dashboard."""

    request_historical_details = Signal(date)

    def __init__(self, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._protection_manager = protection_manager
        self._repo = Repository()
        self._engine = AnalyticsEngine()
        self._sm = SettingsManager()
        self._current_date = date.today()
        self._chart_end_date = date.today()
        self._time_range = 1  # Default to Today
        self._setup_ui()
        self._refresh()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self._main_stack = AnimatedStackedWidget()
        main_layout.addWidget(self._main_stack)
        
        # 0: Activity Dashboard View
        self._dashboard_widget = QWidget()
        self._build_dashboard_view()
        self._main_stack.addWidget(self._dashboard_widget)
        
        # 1: Category Details
        self._category_page = CategoryDetailsPage(on_back=self._navigate_back)
        self._category_page.request_app_details.connect(self._open_app_details)
        self._main_stack.addWidget(self._category_page)
        
        # 2: App Details
        self._app_page = AppDetailsPage(on_back=self._navigate_back, protection_manager=self._protection_manager)
        self._main_stack.addWidget(self._app_page)
        
        self._navigation_history: list[int] = []

    def _build_dashboard_view(self) -> None:
        layout = QVBoxLayout(self._dashboard_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        inner = QWidget()
        self._content_layout = QVBoxLayout(inner)
        self._content_layout.setContentsMargins(32, 28, 32, 28)
        self._content_layout.setSpacing(24)
        scroll.setWidget(inner)
        layout.addWidget(scroll)

        # Header Title
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        title = QLabel("Usage & Trends")
        title.setObjectName("page_title")
        subtitle = QLabel("Comprehensive overview of your digital habits.")
        subtitle.setObjectName("page_subtitle")
        hdr_box.addWidget(title)
        hdr_box.addWidget(subtitle)
        self._content_layout.addLayout(hdr_box)

        # 1. Time Range Toggles
        self._range_group = QButtonGroup(self)
        range_layout = QHBoxLayout()
        range_layout.setSpacing(0)
        
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
        
        range_layout.addWidget(self._btn_today)
        range_layout.addWidget(self._btn_7d)
        range_layout.addWidget(self._btn_30d)
        range_layout.addStretch()
        
        self._range_group.idClicked.connect(self._on_range_changed)
        self._content_layout.addLayout(range_layout)
        
        # 2. Analytical KPI Overview Cards
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self._kpi_screen_time = self._create_kpi_card("SCREEN TIME", "0h 0m", "clock", kpi_row)
        self._kpi_active_time = self._create_kpi_card("ACTIVE TIME", "0h 0m", "usage", kpi_row)
        self._kpi_idle_time = self._create_kpi_card("IDLE TIME", "0h 0m", "hourglass", kpi_row)
        self._kpi_top_cat = self._create_kpi_card("TOP CATEGORY", "-", "apps", kpi_row)
        self._content_layout.addLayout(kpi_row)

        # 3. Charts (Hourly for Today, Daily for 7D / 30D)
        from ui.widgets.charts import HourlyIntensityChart
        self._hourly_chart = HourlyIntensityChart()
        self._hourly_chart.setVisible(False)
        self._content_layout.addWidget(self._hourly_chart)

        self._chart = DailyScreenTimeChart()
        self._chart.day_selected.connect(self._on_day_selected)
        self._content_layout.addWidget(self._chart)

        # 4. Category Breakdown
        lbl_cat = QLabel("Category breakdown")
        lbl_cat.setObjectName("section_header")
        self._content_layout.addWidget(lbl_cat)
        
        from PySide6.QtWidgets import QGridLayout
        self._category_grid = QGridLayout()
        self._category_grid.setSpacing(12)
        self._content_layout.addLayout(self._category_grid)
        
        # 5. Applications List
        lbl_apps = QLabel("Top Applications")
        lbl_apps.setObjectName("section_header")
        self._content_layout.addWidget(lbl_apps)
        
        apps_card = QFrame()
        apps_card.setObjectName("v2_card")
        apps_card_l = QVBoxLayout(apps_card)
        apps_card_l.setContentsMargins(18, 14, 18, 14)
        apps_card_l.setSpacing(6)

        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(6)
        apps_card_l.addLayout(self._apps_layout)
        self._content_layout.addWidget(apps_card)

        # 6. Top Websites List
        self._lbl_websites = QLabel("Top Websites")
        self._lbl_websites.setObjectName("section_header")
        self._content_layout.addWidget(self._lbl_websites)

        self._websites_card = QFrame()
        self._websites_card.setObjectName("v2_card")
        websites_card_l = QVBoxLayout(self._websites_card)
        websites_card_l.setContentsMargins(18, 14, 18, 14)
        websites_card_l.setSpacing(6)

        self._websites_layout = QVBoxLayout()
        self._websites_layout.setSpacing(6)
        websites_card_l.addLayout(self._websites_layout)
        self._content_layout.addWidget(self._websites_card)

        # 7. Long Term Analytics Layout
        self._analytics_layout = QVBoxLayout()
        self._analytics_layout.setSpacing(20)
        self._content_layout.addLayout(self._analytics_layout)

        # Build Analytics UI dynamically in _refresh or _update_day_details
        self._build_analytics_cards()

        self._content_layout.addStretch()

    def _create_kpi_card(self, title: str, default_val: str, icon_name: str, layout: QHBoxLayout) -> QLabel:
        from ui.icons import get_icon
        from ui.theme import ThemeManager
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
        ico.setPixmap(get_icon(icon_name, color=tm.color("text_muted"), size=15).pixmap(15, 15))
        top_h.addWidget(ico)
        l.addLayout(top_h)
        
        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val_success")
        l.addWidget(lbl_val)
        
        layout.addWidget(card, 1)
        return lbl_val

    def _build_analytics_cards(self) -> None:
        # Clear existing
        while self._analytics_layout.count():
            item = self._analytics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Usage Summary Row
        lbl_usage = QLabel("Usage Summary")
        lbl_usage.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_usage)
        
        usage_row = QHBoxLayout()
        usage_row.setSpacing(16)
        
        self._lbl_avg_daily = self._create_stat_card("Average Daily", "0h 0m", usage_row)
        self._lbl_avg_weekly = self._create_stat_card("Average Weekly", "0h 0m", usage_row)
        self._lbl_avg_monthly = self._create_stat_card("Average Monthly", "0h 0m", usage_row)
        self._analytics_layout.addLayout(usage_row)
        
        # Trends Row
        lbl_trends = QLabel("Trends")
        lbl_trends.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_trends)
        
        trends_row = QHBoxLayout()
        trends_row.setSpacing(16)
        
        self._lbl_productive_day = self._create_stat_card("Most Productive Day", "-", trends_row)
        self._lbl_longest_session = self._create_stat_card("Longest Focus Session", "0h 0m", trends_row)
        self._analytics_layout.addLayout(trends_row)
        
        # Goals Row
        lbl_goals = QLabel("Goal Statistics")
        lbl_goals.setObjectName("section_header")
        self._analytics_layout.addWidget(lbl_goals)
        
        goals_row = QHBoxLayout()
        goals_row.setSpacing(16)
        
        self._lbl_current_streak = self._create_stat_card("Current Streak", "0 Days", goals_row)
        self._lbl_best_streak = self._create_stat_card("Best Streak", "0 Days", goals_row)
        self._analytics_layout.addLayout(goals_row)

    def _create_stat_card(self, title: str, default_val: str, layout: QHBoxLayout) -> QLabel:
        card = QFrame()
        card.setObjectName("v2_card")
        l = QVBoxLayout(card)
        l.setContentsMargins(20, 16, 20, 16)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("metric_hdr")
        l.addWidget(lbl_title)
        
        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val_success")
        l.addWidget(lbl_val)
        
        layout.addWidget(card, 1)
        return lbl_val

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 26px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle {{ font-size: 13px; font-weight: 500; color: {tm.color('text_sub')}; }}
            QLabel#metric_hdr {{ color: {tm.color('text_muted')}; font-size: 11px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }}
            QLabel#metric_val_success {{ font-size: 22px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.5px; }}
            QLabel#section_header {{ font-size: 11px; font-weight: 700; color: {tm.color('text_muted')}; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px; }}
            
            /* Segmented Control Buttons */
            QPushButton#segment_btn_left, QPushButton#segment_btn_mid, QPushButton#segment_btn_right {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                color: {tm.color('text_sub')};
                padding: 7px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#segment_btn_left {{
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                border-right: none;
            }}
            QPushButton#segment_btn_mid {{
                border-radius: 0px;
                border-right: none;
            }}
            QPushButton#segment_btn_right {{
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QPushButton#segment_btn_left:hover, QPushButton#segment_btn_mid:hover, QPushButton#segment_btn_right:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#segment_btn_left:checked, QPushButton#segment_btn_mid:checked, QPushButton#segment_btn_right:checked {{
                background: {tm.color('accent_emerald_bg')};
                color: {tm.color('accent')};
                font-weight: 700;
                border: 1px solid {tm.color('accent')};
            }}
        """)
        
        self._refresh()

    def _refresh(self) -> None:
        if self._main_stack.currentIndex() == 0:
            self._update_chart()

    def _update_chart(self) -> None:
        end_d = self._chart_end_date
        start_d = end_d - timedelta(days=self._time_range - 1)
        
        if self._time_range == 1:
            # Show hourly chart for Today
            self._chart.setVisible(False)
            self._hourly_chart.setVisible(True)
            hourly_data = self._engine.get_hourly_chart_data(start_d)
            self._hourly_chart.update_data(hourly_data)
        else:
            self._hourly_chart.setVisible(False)
            self._chart.setVisible(True)
            self._chart.set_range_title("PAST 30 DAYS" if self._time_range == 30 else "PAST 7 DAYS")
            daily_pts = self._engine.get_daily_chart_data(start_d, end_d)
            self._chart.update_data(daily_pts)
            
        summary = self._update_lists(start_d, end_d)
        self._update_day_details(start_d, end_d, summary)
        
    def _on_range_changed(self, range_id: int) -> None:
        self._time_range = range_id
        btn = self._range_group.button(range_id)
        if btn and not btn.isChecked():
            btn.setChecked(True)
        self._chart_end_date = date.today()
        self._refresh()
        
    def _update_lists(self, start_d: date, end_d: date) -> None:
        self._clear_layout(self._category_grid)
        self._clear_layout(self._apps_layout)
        
        # We need aggregated data for the range
        summary = self._engine.get_custom_summary(start_d, end_d)
        
        # KPI updates
        self._kpi_screen_time.setText(self._engine.format_duration(summary.total_screen_time_s))
        self._kpi_active_time.setText(self._engine.format_duration(summary.active_time_s))
        self._kpi_idle_time.setText(self._engine.format_duration(summary.idle_time_s))
        top_c = summary.category_breakdown[0]["category"] if summary.category_breakdown else "-"
        if hasattr(top_c, "value"):
            top_c = top_c.value
        self._kpi_top_cat.setText(str(top_c).title())

        # Categories
        cat_breakdown = summary.category_breakdown
        if not cat_breakdown:
            lbl = QLabel("No category data recorded.")
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 13px; font-weight: 500;")
            self._category_grid.addWidget(lbl, 0, 0)
        else:
            sorted_cats = sorted(cat_breakdown, key=lambda x: float(x.get("total_s", 0)), reverse=True)
            row_idx = 0
            col_idx = 0
            for item in sorted_cats:
                dur = float(item.get("total_s", 0))
                if dur > 60:  # Only show > 1 min
                    from ui.widgets.simple_category_row import ClickableCategoryCard
                    card = ClickableCategoryCard(item["category"], dur)
                    cat_val = item["category"].value if hasattr(item["category"], "value") else str(item["category"])
                    card.clicked.connect(lambda c=cat_val: self.open_category_details(c))
                    self._category_grid.addWidget(card, row_idx, col_idx)
                    col_idx += 1
                    if col_idx >= 3:
                        col_idx = 0
                        row_idx += 1
                    
        # Apps
        top_apps = summary.top_apps
        if not top_apps:
            lbl = QLabel("No application data recorded.")
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 13px; font-weight: 500;")
            self._apps_layout.addWidget(lbl)
        else:
            max_dur = top_apps[0]["total_s"] if top_apps else 0
            for i, app in enumerate(top_apps[:10]):
                if app["total_s"] > 60:
                    row = AppUsageRow(
                        rank=i+1,
                        process_name=app["process_name"],
                        display_name=app.get("display_name", app["process_name"]),
                        category=app["category"],
                        duration_s=app["total_s"],
                        max_duration_s=max_dur
                    )
                    row.app_clicked.connect(self._open_app_details)
                    self._apps_layout.addWidget(row)

        # Websites
        self._clear_layout(self._websites_layout)
        top_websites = self._engine.get_top_websites_for_range(start_d, end_d, limit=10)
        if not top_websites:
            self._lbl_websites.hide()
            self._websites_card.hide()
        else:
            self._lbl_websites.show()
            self._websites_card.show()
            max_web_dur = top_websites[0]["total_s"] if top_websites else 1.0
            for w in top_websites:
                w_row = WebsiteUsageRow(
                    domain=w["domain"],
                    duration_s=w["total_s"],
                    max_duration_s=max_web_dur,
                    browser_process=w.get("browser_process", ""),
                    show_limit_button=bool(self._protection_manager),
                )
                w_row.set_limit_requested.connect(
                    lambda dom, bproc=w.get("browser_process", ""): self._on_set_website_limit_from_activity(dom, bproc)
                )
                self._websites_layout.addWidget(w_row)

        return summary

    def _on_set_website_limit_from_activity(self, domain: str, browser_process: str = "") -> None:
        if not self._protection_manager:
            return
        b_proc = browser_process or "chrome.exe"
        current_rule = self._protection_manager.website_limits.get_all_limits(b_proc).get(domain, {})
        dialog = WebsiteTimerConfigDialog(
            parent=self.window(),
            domain=domain,
            limit_s=current_rule.get("limit_seconds", 0),
            browser_name=get_display_name(b_proc)
        )
        if dialog.exec():
            d_name, rule = dialog.get_data()
            if d_name:
                self._protection_manager.website_limits.set_limit_rule(b_proc, d_name, rule)
                self._refresh()
        
    def _on_day_selected(self, date_str: str) -> None:
        selected_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        self.request_historical_details.emit(selected_dt)

    def _update_day_details(self, start_d: date, end_d: date, summary) -> None:
        # Populate Long-Term Analytics
        long_term = self._engine.get_long_term_analytics()
        
        self._lbl_avg_daily.setText(self._engine.format_duration(summary.average_daily_s))
        
        if (end_d - start_d).days == 0:
            self._lbl_avg_weekly.setText(self._engine.format_duration(summary.average_daily_s * 7))
            self._lbl_avg_monthly.setText(self._engine.format_duration(summary.average_daily_s * 30))
        else:
            self._lbl_avg_weekly.setText(self._engine.format_duration(summary.average_daily_s * 7))
            self._lbl_avg_monthly.setText(self._engine.format_duration(summary.average_daily_s * 30))
        
        best_day = long_term.get("most_productive_day")
        if best_day:
            self._lbl_productive_day.setText(best_day.strftime("%A, %b %d"))
        else:
            self._lbl_productive_day.setText("-")
            
        if summary.longest_session_app:
            self._lbl_longest_session.setText(f"{get_display_name(summary.longest_session_app)} ({self._engine.format_duration_short(summary.longest_session_s)})")
        else:
            self._lbl_longest_session.setText("-")
        
        self._lbl_current_streak.setText(f"{long_term.get('current_streak', 0)} Days")
        self._lbl_best_streak.setText(f"{long_term.get('best_streak', 0)} Days")

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
                
    def open_category_details(self, category_name: str) -> None:
        start_d = self._chart_end_date - timedelta(days=self._time_range - 1)
        end_d = self._chart_end_date
        summary = self._engine.get_custom_summary(start_d, end_d)
        self._category_page.set_data(category_name, summary.top_apps, summary.active_time_s)
        self._navigate_to(1)

    def _on_category_card_clicked(self, event) -> None:
        self.open_category_details("All Categories")
        
    def open_app_details(self, process_name: str) -> None:
        self._app_page.set_app(process_name)
        self._navigate_to(2)
        
    def _open_app_details(self, process_name: str) -> None:
        self.open_app_details(process_name)
        
    def _navigate_to(self, index: int) -> None:
        self._navigation_history.append(self._main_stack.currentIndex())
        self._main_stack.setCurrentIndex(index)
        
    def _navigate_back(self) -> None:
        if self._navigation_history:
            prev = self._navigation_history.pop()
            self._main_stack.setCurrentIndex(prev)
            if prev == 0:
                self._refresh()

    def on_data_changed(self) -> None:
        self._refresh()
