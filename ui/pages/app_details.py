"""
app_details.py — Detailed Application View for Digital Wellbeing.
"""

from __future__ import annotations

from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QGridLayout, QComboBox
)

from analytics.engine import AnalyticsEngine
from ui.widgets.charts import HourlyIntensityChart
from tracker.categorizer import display_name as get_display_name
from utils.icon_provider import AppIconProvider
from ui.widgets.fluent import FluentLabel
from ui.widgets.app_timer_widgets import TimerDisplayCard, TimerConfigDialog, AnimatedProgressBar
from ui.widgets.website_timer_widgets import WebsiteTimersSection, WebsiteTimerConfigDialog
from ui.widgets.website_row import WebsiteUsageRow
from tracker.foreground import BROWSER_PROCESSES

class TodayProgressWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_box")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        self.title_lbl = FluentLabel("Today's Progress", FluentLabel.Style.HEADING)
        self.val_lbl = FluentLabel("0m / Unlimited", FluentLabel.Style.SUBHEADING)
        self.progress_bar = AnimatedProgressBar()
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)
        layout.addSpacing(16)
        layout.addWidget(self.progress_bar)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#stat_box {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
        """)

    def update_progress(self, elapsed_s, limit_s):
        from analytics.engine import AnalyticsEngine
        elapsed_str = AnalyticsEngine.format_duration_short(elapsed_s)
        
        if limit_s and limit_s > 0:
            limit_str = AnalyticsEngine.format_duration_short(limit_s)
            self.val_lbl.setText(f"{elapsed_str} / {limit_str}")
            self.progress_bar.set_value(elapsed_s / limit_s)
        else:
            self.val_lbl.setText(f"{elapsed_str} / Unlimited")
            self.progress_bar.set_value(0.0)


class StatBox(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_box")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setObjectName("stat_title")
        
        self.val_lbl = QLabel(value)
        self.val_lbl.setObjectName("stat_val")
        
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.val_lbl)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QFrame#stat_box {{
                background-color: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QLabel#stat_title {{ font-size: 13px; color: {tm.color('text_sub')}; font-weight: 600; border: none; background: transparent; }}
            QLabel#stat_val {{ font-size: 24px; font-weight: 700; color: {tm.color('text_main')}; border: none; background: transparent; }}
        """)

    def set_value(self, value: str):
        self.val_lbl.setText(value)


class AppDetailsPage(QWidget):
    """Detailed view for a specific application."""

    back_requested = Signal()

    def __init__(self, on_back: Optional[Callable[[], None]] = None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = AnalyticsEngine()
        self._protection_manager = protection_manager
        self._current_app: str = ""
        self._setup_ui()
        
        if on_back:
            self.back_requested.connect(on_back)
            
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

        # Setup live update timer
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(2000) # Update every 2 seconds
        self._live_timer.timeout.connect(self._on_live_update)

    def showEvent(self, event):
        super().showEvent(event)
        self._live_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._live_timer.stop()

    def _on_live_update(self):
        if not self._current_app or not self._protection_manager:
            return
            
        # Update app timer progress
        current_rule = self._protection_manager.limits.get_limit_rule(self._current_app)
        limit_s = current_rule.get("limit_seconds", 0) if current_rule else 0
        
        # We need today_s from DB or active memory. It's expensive to do full DB query every 2s.
        # Instead of full refresh(), we can just refresh the website timers list which uses memory.
        if hasattr(self, "_website_timers_section") and self._website_timers_section.isVisible():
            self._website_timers_section.refresh()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#app_title {{ font-size: 32px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#app_cat {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
        """)
        
    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(0)

        # Top Bar
        top_bar = QHBoxLayout()
        from ui.widgets.back_header import BackHeader
        self._back_header = BackHeader("App Details", "Detailed statistics and timeline")
        self._back_header.back_requested.connect(self.back_requested.emit)
        top_bar.addWidget(self._back_header)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)
        
        main_layout.addSpacing(24)

        # Header
        header = QHBoxLayout()
        header.setSpacing(24)
        
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(64, 64)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        self._title_lbl = QLabel("App Name")
        self._title_lbl.setObjectName("app_title")
        
        self._cat_lbl = QLabel("Category")
        self._cat_lbl.setObjectName("app_cat")
        
        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._cat_lbl)
        header.addWidget(self._icon_lbl)
        header.addLayout(title_box)

        header.addStretch()
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
        self._inner_layout.setSpacing(24)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # Stats Grid
        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(16)
        
        self._stat_today = StatBox("Today's Usage", "0m")
        self._stat_yesterday = StatBox("Yesterday", "0m")
        self._stat_weekly = StatBox("Weekly Average", "0m")
        self._stat_sessions = StatBox("Session Count", "0")
        
        self._stats_grid.addWidget(self._stat_today, 0, 0)
        self._stats_grid.addWidget(self._stat_yesterday, 0, 1)
        self._stats_grid.addWidget(self._stat_weekly, 0, 2)
        self._stats_grid.addWidget(self._stat_sessions, 0, 3)
        
        self._inner_layout.addLayout(self._stats_grid)

        # -----------------------------------------------------
        # App Timer Section
        # -----------------------------------------------------
        if self._protection_manager:
            # Progress Widget
            self._progress_widget = TodayProgressWidget()
            self._inner_layout.addWidget(self._progress_widget)
            
            # Standalone App Timer Card (Samsung-inspired)
            self._timer_card = TimerDisplayCard()
            self._timer_card.change_requested.connect(self._on_change_timer)
            self._inner_layout.addWidget(self._timer_card)
            
            # Override Status
            self._override_lbl = QLabel("")
            self._override_lbl.setStyleSheet("color: #FFD60A; font-weight: 600; font-size: 13px; margin-top: 8px;")
            self._inner_layout.addWidget(self._override_lbl)
            
            # Restriction Type Segmented Control
            self._restriction_type_combo = QComboBox()
            self._restriction_type_combo.addItems(["Entire Application", "Specific Websites"])
            self._restriction_type_combo.setFixedWidth(200)
            self._restriction_type_combo.setStyleSheet("""
                QComboBox {
                    padding: 8px; border-radius: 6px; border: 1px solid #444; background: #222; color: white;
                }
            """)
            self._inner_layout.addWidget(QLabel("Restriction Mode:"))
            self._inner_layout.addWidget(self._restriction_type_combo)
            
            self._website_timers_section = WebsiteTimersSection(self._protection_manager, self._current_app)
            self._inner_layout.addWidget(self._website_timers_section)
            self._website_timers_section.hide()
            
            self._restriction_type_combo.currentIndexChanged.connect(self._on_restriction_type_changed)

        # -----------------------------------------------------
        # Websites Visited Section (Visible for Web Browsers)
        # -----------------------------------------------------
        self._websites_section = QFrame()
        self._websites_section.setObjectName("v2_card")
        self._websites_layout = QVBoxLayout(self._websites_section)
        self._websites_layout.setContentsMargins(18, 16, 18, 16)
        self._websites_layout.setSpacing(12)

        web_hdr_box = QHBoxLayout()
        web_hdr_box.setSpacing(8)
        self._websites_header = QLabel("Websites Visited Today")
        self._websites_header.setObjectName("section_header")
        self._websites_header.setStyleSheet("font-size: 18px; font-weight: 700;")
        web_hdr_box.addWidget(self._websites_header)
        web_hdr_box.addStretch()
        self._websites_layout.addLayout(web_hdr_box)

        self._websites_list_layout = QVBoxLayout()
        self._websites_list_layout.setSpacing(8)
        self._websites_layout.addLayout(self._websites_list_layout)

        self._inner_layout.addWidget(self._websites_section)
        self._websites_section.hide()

        history_header = QLabel("Usage History")
        history_header.setObjectName("app_title")
        history_header.setStyleSheet("font-size: 20px; font-weight: 700; margin-top: 16px;")
        self._inner_layout.addWidget(history_header)

        # Timeline Chart
        self._chart = HourlyIntensityChart()
        self._inner_layout.addWidget(self._chart)
        
        self._inner_layout.addStretch()

    def _on_change_timer(self) -> None:
        if not self._protection_manager or not self._current_app:
            return
            
        current_rule = self._protection_manager.limits.get_limit_rule(self._current_app)
        dialog = TimerConfigDialog(self.window(), current_rule)
        
        if dialog.exec():
            rule = dialog.get_rule()
            self._protection_manager.limits.set_limit_rule(self._current_app, rule)
            self.refresh()

    def _on_restriction_type_changed(self, idx: int) -> None:
        if idx == 0:
            self._timer_card.show()
            self._website_timers_section.hide()
        else:
            self._timer_card.hide()
            self._website_timers_section.show()

    def set_app(self, process_name: str) -> None:
        self._current_app = process_name
        if hasattr(self, "_website_timers_section"):
            self._website_timers_section.process_name = process_name
        self.refresh()
        
    def refresh(self) -> None:
        if not self._current_app:
            return
            
        process_name = self._current_app
        
        # Update Icon
        icon = AppIconProvider().get_icon(process_name)
        if not icon.isNull():
            from PySide6.QtCore import QSize
            self._icon_lbl.setPixmap(icon.pixmap(QSize(64, 64)))
            
        # Update Labels
        self._title_lbl.setText(get_display_name(process_name))
        
        # Get Stats
        import sqlite3
        import os
        from database.repository import _get_db_path
        
        db_path = str(_get_db_path())
        today_s = 0.0
        yesterday_s = 0.0
        sessions = 0
        
        from datetime import date, timedelta
        today_date = date.today().isoformat()
        yesterday_date = (date.today() - timedelta(days=1)).isoformat()
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Today
                cur = conn.cursor()
                cur.execute("SELECT SUM(duration_s) FROM app_sessions WHERE process_name=? AND date(start_time)=?", (process_name, today_date))
                res = cur.fetchone()
                today_s = res[0] or 0.0
                
                # Sessions today
                cur.execute("SELECT COUNT(*) FROM app_sessions WHERE process_name=? AND date(start_time)=?", (process_name, today_date))
                res = cur.fetchone()
                sessions = res[0] or 0
                
                # Yesterday
                cur.execute("SELECT SUM(duration_s) FROM app_sessions WHERE process_name=? AND date(start_time)=?", (process_name, yesterday_date))
                res = cur.fetchone()
                yesterday_s = res[0] or 0.0
                
                # Hourly today for chart
                cur.execute("""
                    SELECT strftime('%H', start_time) as hr, SUM(duration_s)
                    FROM app_sessions
                    WHERE process_name=? AND date(start_time)=?
                    GROUP BY hr
                """, (process_name, today_date))
                
                hourly_data = {str(i).zfill(2): 0.0 for i in range(24)}
                for row in cur.fetchall():
                    hourly_data[row[0]] = row[1]
                    
                hourly_rows = [{"hour": int(h), "total_s": s} for h, s in hourly_data.items()]
                self._chart.update_data(hourly_rows)
                
        except Exception as e:
            pass
            
        self._stat_today.set_value(AnalyticsEngine.format_duration_short(today_s))
        self._stat_yesterday.set_value(AnalyticsEngine.format_duration_short(yesterday_s))
        self._stat_sessions.set_value(str(sessions))
        # Weekly Average is a placeholder for now, just mock based on today/yesterday
        self._stat_weekly.set_value(AnalyticsEngine.format_duration_short((today_s + yesterday_s) / 2.0))

        if self._protection_manager:
            current_rule = self._protection_manager.limits.get_limit_rule(process_name)
            limit_s = current_rule.get("limit_seconds", 0) if current_rule else 0
            
            self._timer_card.set_limit(current_rule)
            
            self._progress_widget.update_progress(today_s, limit_s)

            if self._protection_manager.has_active_override(process_name):
                self._override_lbl.setText("Status: Override active for today.")
                self._override_lbl.setVisible(True)
            else:
                self._override_lbl.setText("")
                self._override_lbl.setVisible(False)
                
            # Update Website Timers Section
            is_browser = process_name.lower() in BROWSER_PROCESSES
            if is_browser:
                self._restriction_type_combo.parentWidget().layout().itemAt(self._inner_layout.indexOf(self._restriction_type_combo) - 1).widget().show() # The label
                self._restriction_type_combo.show()
                self._website_timers_section.refresh()
                # Check if there are website limits configured
                limits = self._protection_manager.website_limits.get_all_limits(process_name)
                if limits and self._restriction_type_combo.currentIndex() != 1:
                    self._restriction_type_combo.setCurrentIndex(1)
            else:
                self._restriction_type_combo.parentWidget().layout().itemAt(self._inner_layout.indexOf(self._restriction_type_combo) - 1).widget().hide()
                self._restriction_type_combo.hide()
                self._restriction_type_combo.setCurrentIndex(0)
                self._website_timers_section.hide()

        # Update Websites Visited Section for browsers
        is_browser = process_name.lower() in BROWSER_PROCESSES
        if is_browser:
            while self._websites_list_layout.count():
                child = self._websites_list_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            from datetime import date
            websites = self._engine.get_top_websites_for_browser(process_name, date.today(), date.today(), limit=30)
            if websites:
                max_w_dur = max(w["total_s"] for w in websites)
                for w in websites:
                    row = WebsiteUsageRow(
                        domain=w["domain"],
                        duration_s=w["total_s"],
                        max_duration_s=max_w_dur,
                        browser_process=process_name,
                        show_limit_button=bool(self._protection_manager),
                    )
                    row.set_limit_requested.connect(self._on_set_website_limit)
                    self._websites_list_layout.addWidget(row)
            else:
                from ui.theme import ThemeManager
                tm = ThemeManager.instance()
                empty_lbl = QLabel("No website sessions recorded for this browser today yet.")
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_lbl.setStyleSheet(f"color: {tm.color('text_sub')}; font-size: 13px; padding: 24px;")
                self._websites_list_layout.addWidget(empty_lbl)

            self._websites_section.show()
        else:
            self._websites_section.hide()

    def _on_set_website_limit(self, domain: str) -> None:
        if not self._protection_manager or not self._current_app:
            return
        current_rule = self._protection_manager.website_limits.get_all_limits(self._current_app).get(domain, {})
        dialog = WebsiteTimerConfigDialog(
            parent=self.window(),
            domain=domain,
            limit_s=current_rule.get("limit_seconds", 0),
            browser_name=get_display_name(self._current_app)
        )
        if dialog.exec():
            d_name, rule = dialog.get_data()
            if d_name:
                self._protection_manager.website_limits.set_limit_rule(self._current_app, d_name, rule)
                self.refresh()
