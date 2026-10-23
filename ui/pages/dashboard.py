"""
dashboard.py — Premium Samsung/Apple inspired Dashboard Page for Digital Wellbeing.
Features minimal clutter, strong visual hierarchy, and large interactive cards.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from ui.widgets.primary_metric_card import PrimaryMetricCard
from ui.widgets.kpi_cards import KPICard
from ui.widgets.quick_actions import QuickActionsRow
from ui.widgets.simple_category_row import ClickableCategoryCard
from ui.widgets.flow_layout import FlowLayout

class ClickableCategoryRow(ClickableCategoryCard):
    clicked = Signal(str)
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        cat_name = self._category.value if hasattr(self._category, "value") else str(self._category)
        self.clicked.emit(cat_name)


class DashboardPage(QWidget):
    """Premium visual Dashboard for Digital Wellbeing."""

    request_screen_time_details = Signal()
    request_focus_session = Signal()
    request_category_details = Signal(str)
    request_app_details = Signal(str)

    def __init__(self, on_global_refresh: Optional[Callable[[], None]] = None, navigate_callback: Optional[Callable[[int], None]] = None, parent=None) -> None:
        super().__init__(parent)
        self._on_global_refresh = on_global_refresh
        self._navigate = navigate_callback
        self._engine = AnalyticsEngine()
        self._setup_ui()
        self._refresh()

        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 22, 36, 22)
        main_layout.setSpacing(0)

        # Header Row
        header = QHBoxLayout()
        header.setSpacing(24)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        
        self._greeting_label = QLabel("Good morning")
        self._greeting_label.setObjectName("dashboard_greeting")
        self._context_label = QLabel("")
        self._context_label.setObjectName("dashboard_context")
        self._date_label = QLabel("")
        self._date_label.setObjectName("dashboard_date")
        
        title_box.addWidget(self._greeting_label)
        title_box.addWidget(self._context_label)
        title_box.addWidget(self._date_label)
        header.addLayout(title_box)

        header.addStretch()

        from ui.widgets.fluent import IconButton
        self._refresh_btn = IconButton("refresh")
        self._refresh_btn.setToolTip("Refresh Data")
        self._is_refreshing = False
        self._refresh_btn.clicked.connect(self._trigger_refresh)
        header.addWidget(self._refresh_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(header)
        main_layout.addSpacing(16)

        # Scroll Container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(16)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # 1. Top Section (Hero Screen Time + KPIs)
        top_row = QHBoxLayout()
        top_row.setSpacing(20)
        
        # Left: Primary Metric Card
        self._primary_metric = PrimaryMetricCard()
        self._primary_metric.card_clicked.connect(self.request_screen_time_details.emit)
        top_row.addWidget(self._primary_metric, stretch=5)
        
        # Right: KPIs
        kpi_layout = QVBoxLayout()
        kpi_layout.setSpacing(14)
        
        self._kpi_active = KPICard("Active Time", icon_name="usage")
        self._kpi_idle = KPICard("Idle Time", icon_name="hourglass")
        
        kpi_layout.addWidget(self._kpi_active)
        kpi_layout.addWidget(self._kpi_idle)
        top_row.addLayout(kpi_layout, stretch=3)
        
        self._inner_layout.addLayout(top_row)

        # 2. Cockpit Lower Grid: 2 Columns
        cockpit_grid = QHBoxLayout()
        cockpit_grid.setSpacing(20)

        # ── Left Column: Top Applications & Categories ─────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Top Applications Card
        apps_card = QFrame()
        apps_card.setObjectName("dense_card")
        apps_card_layout = QVBoxLayout(apps_card)
        apps_card_layout.setContentsMargins(22, 20, 22, 20)
        apps_card_layout.setSpacing(14)

        apps_hdr = QHBoxLayout()
        lbl_apps = QLabel("Top applications")
        lbl_apps.setObjectName("cockpit_section_title")
        apps_hdr.addWidget(lbl_apps)
        apps_hdr.addStretch()
        apps_card_layout.addLayout(apps_hdr)

        self._apps_container = QVBoxLayout()
        self._apps_container.setSpacing(8)
        apps_card_layout.addLayout(self._apps_container)
        left_col.addWidget(apps_card)

        # Most Used Categories Card
        cats_card = QFrame()
        cats_card.setObjectName("dense_card")
        cats_card_layout = QVBoxLayout(cats_card)
        cats_card_layout.setContentsMargins(22, 20, 22, 20)
        cats_card_layout.setSpacing(14)

        cats_hdr = QHBoxLayout()
        lbl_cats = QLabel("Most used categories")
        lbl_cats.setObjectName("cockpit_section_title")
        cats_hdr.addWidget(lbl_cats)
        cats_hdr.addStretch()
        cats_card_layout.addLayout(cats_hdr)

        self._cats_container = QWidget()
        self._cats_layout = FlowLayout(self._cats_container, margin=0, hSpacing=12, vSpacing=12)
        cats_card_layout.addWidget(self._cats_container)
        left_col.addWidget(cats_card)

        cockpit_grid.addLayout(left_col, stretch=5)

        # ── Right Column: Focus & Wellbeing Status ────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Focus Cockpit Card
        focus_card = QFrame()
        focus_card.setObjectName("dense_card")
        focus_layout = QVBoxLayout(focus_card)
        focus_layout.setContentsMargins(22, 20, 22, 20)
        focus_layout.setSpacing(14)

        focus_hdr = QHBoxLayout()
        from ui.icons import get_icon
        f_icon = QLabel()
        f_icon.setFixedSize(16, 16)
        f_icon.setPixmap(get_icon("focus", size=16).pixmap(16, 16))
        lbl_focus = QLabel("Focus session")
        lbl_focus.setObjectName("cockpit_section_title")
        focus_hdr.addWidget(f_icon)
        focus_hdr.addWidget(lbl_focus)
        focus_hdr.addStretch()
        focus_layout.addLayout(focus_hdr)

        self._focus_status_lbl = QLabel("No session active. Ready to eliminate distractions.")
        self._focus_status_lbl.setObjectName("cockpit_desc")
        self._focus_status_lbl.setWordWrap(True)
        focus_layout.addWidget(self._focus_status_lbl)

        focus_btn_row = QHBoxLayout()
        from ui.widgets.fluent import FluentButton
        self._start_focus_btn = FluentButton("Start Focus Session", primary=True)
        self._start_focus_btn.set_icon_name("play", size=13, color="#FFFFFF")
        self._start_focus_btn.setMinimumHeight(38)
        self._start_focus_btn.clicked.connect(self._on_start_focus_clicked)
        focus_btn_row.addWidget(self._start_focus_btn)
        focus_layout.addLayout(focus_btn_row)
        right_col.addWidget(focus_card)

        # System Controls Card (App Limits & SleepGuard Quick Status)
        ctrl_card = QFrame()
        ctrl_card.setObjectName("dense_card")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(22, 20, 22, 20)
        ctrl_layout.setSpacing(14)

        ctrl_hdr = QHBoxLayout()
        lbl_ctrl = QLabel("Wellbeing controls")
        lbl_ctrl.setObjectName("cockpit_section_title")
        ctrl_hdr.addWidget(lbl_ctrl)
        ctrl_hdr.addStretch()
        ctrl_layout.addLayout(ctrl_hdr)

        # App Timer row
        timer_row = QHBoxLayout()
        t_icon = QLabel()
        t_icon.setFixedSize(16, 16)
        t_icon.setPixmap(get_icon("clock", size=16).pixmap(16, 16))
        t_text = QLabel("App Timers")
        t_text.setObjectName("cockpit_item_title")
        timer_row.addWidget(t_icon)
        timer_row.addWidget(t_text)
        timer_row.addStretch()
        btn_view_timers = QPushButton("View")
        btn_view_timers.setObjectName("cockpit_pill_btn")
        btn_view_timers.clicked.connect(lambda: self._navigate(4) if self._navigate else None)
        timer_row.addWidget(btn_view_timers)
        ctrl_layout.addLayout(timer_row)

        # App Locker row
        locker_row = QHBoxLayout()
        l_icon = QLabel()
        l_icon.setFixedSize(16, 16)
        l_icon.setPixmap(get_icon("lock", size=16).pixmap(16, 16))
        l_text = QLabel("App Locker")
        l_text.setObjectName("cockpit_item_title")
        locker_row.addWidget(l_icon)
        locker_row.addWidget(l_text)
        locker_row.addStretch()
        btn_view_locker = QPushButton("Configure")
        btn_view_locker.setObjectName("cockpit_pill_btn")
        btn_view_locker.clicked.connect(lambda: self._navigate(3) if self._navigate else None)
        locker_row.addWidget(btn_view_locker)
        ctrl_layout.addLayout(locker_row)

        # SleepGuard row
        sleep_row = QHBoxLayout()
        s_icon = QLabel()
        s_icon.setFixedSize(16, 16)
        s_icon.setPixmap(get_icon("sleepguard", size=16).pixmap(16, 16))
        s_text = QLabel("SleepGuard")
        s_text.setObjectName("cockpit_item_title")
        sleep_row.addWidget(s_icon)
        sleep_row.addWidget(s_text)
        sleep_row.addStretch()
        btn_view_sleep = QPushButton("Status")
        btn_view_sleep.setObjectName("cockpit_pill_btn")
        btn_view_sleep.clicked.connect(lambda: self._navigate(6) if self._navigate else None)
        sleep_row.addWidget(btn_view_sleep)
        ctrl_layout.addLayout(sleep_row)

        right_col.addWidget(ctrl_card)
        right_col.addStretch()

        cockpit_grid.addLayout(right_col, stretch=3)
        self._inner_layout.addLayout(cockpit_grid)
        self._inner_layout.addStretch()

    def _on_start_focus_clicked(self) -> None:
        from ui import feedback
        feedback.tap(self._start_focus_btn)
        self.request_focus_session.emit()

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#dashboard_greeting {{
                {ds.type_css('title1', tm.color('text_main'))}
            }}
            QLabel#dashboard_context {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                margin-top: 1px;
                margin-bottom: 2px;
            }}
            QLabel#dashboard_date {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_muted')};
            }}
            QLabel#cockpit_section_title {{
                {ds.type_css('micro', tm.color('text_muted'))}
                text-transform: uppercase;
            }}
            QLabel#cockpit_desc {{
                color: {tm.color('text_sub')};
                font-size: 13px;
            }}
            QLabel#cockpit_item_title {{
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#cockpit_pill_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_sub')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.RADIUS['xs']}px;
                font-size: 12px;
                font-weight: 500;
                padding: 5px 12px;
            }}
            QPushButton#cockpit_pill_btn:hover {{
                background-color: {tm.color('accent_tint_bg')};
                color: {tm.color('accent_tint_text')};
                border-color: transparent;
            }}
            QPushButton#cockpit_pill_btn:pressed {{
                background-color: {tm.color('accent_hover_bg')};
            }}
        """)

    def _trigger_refresh(self) -> None:
        if getattr(self, '_is_refreshing', False):
            return
        self._is_refreshing = True
        self._refresh_btn.set_spinning(True)
        
        if self._on_global_refresh:
            self._on_global_refresh()
        else:
            self._refresh()
            
        QTimer.singleShot(600, self._finish_refresh)

    def _finish_refresh(self) -> None:
        self._refresh_btn.set_spinning(False)
        self._is_refreshing = False

    @staticmethod
    def get_greeting_and_context(now: datetime, name: str = "", screen_time_s: float = 0.0, formatted_time: str = "") -> tuple[str, str]:
        """
        Determines the time-aware greeting and thoughtful contextual message based on local system time.
        Time periods:
          - Morning (05:00 - 11:59)
          - Afternoon (12:00 - 16:59)
          - Evening (17:00 - 21:59)
          - Late-Night (22:00 - 23:59)
          - Very Late Hours (00:00 - 04:59)
        """
        hour = now.hour
        day_seed = now.timetuple().tm_yday

        # 1. Base Greeting
        if 5 <= hour < 12:
            base_greeting = "Good morning"
        elif 12 <= hour < 17:
            base_greeting = "Good afternoon"
        elif 17 <= hour < 22:
            base_greeting = "Good evening"
        else:
            base_greeting = "Good night"

        greeting = f"{base_greeting}, {name}" if name else base_greeting

        # 2. Contextual Message
        if 0 <= hour < 5:
            # Very late hours (past midnight)
            very_late_with_name = f"Still going, {name}? It's well past midnight. Give yourself a proper break." if name else "Still going? It's well past midnight. Give yourself a proper break."
            messages = [
                very_late_with_name,
                "Late hours add up quietly. Rest when you're ready.",
                "Tomorrow is already here. A quiet night awaits.",
                "Past midnight. Consider saving your work and catching some rest.",
            ]
            context = messages[day_seed % len(messages)]
        elif 22 <= hour < 24:
            # Late-night hours (10 PM - midnight)
            messages = [
                "The day's winding down. Maybe your screen time should too.",
                "It's getting late. Your screen can wait until tomorrow.",
                "Tomorrow will still be there. Give yourself a proper break.",
                "Still going? It might be a good time to call it a night.",
            ]
            context = messages[day_seed % len(messages)]
        elif 17 <= hour < 22:
            # Evening hours
            messages = [
                "A little more focus, or a little more rest?",
                "Wrapping up your priorities for today.",
                "Time to review the day and unwind.",
                "The evening is yours. Pace yourself.",
            ]
            context = messages[day_seed % len(messages)]
        elif 12 <= hour < 17:
            # Afternoon hours
            if screen_time_s >= 60 and formatted_time:
                context = f"You've spent {formatted_time} on your computer today."
            else:
                messages = [
                    "Steady progress makes the day.",
                    "Keep your momentum going into the afternoon.",
                    "Focus where it matters most this afternoon.",
                ]
                context = messages[day_seed % len(messages)]
        else:
            # Morning hours (05:00 - 11:59)
            messages = [
                "Your day is yours. Make it count.",
                "Ready for a focused, intentional day?",
                "Start with what matters most today.",
                "A fresh start to work on what matters.",
            ]
            context = messages[day_seed % len(messages)]

        return greeting, context

    def _refresh(self) -> None:
        now = datetime.now()
        from settings.manager import SettingsManager
        user_name = SettingsManager().display_name

        summary = self._engine.get_today_summary()
        formatted_total = self._engine.format_duration(summary.total_screen_time_s)

        greeting, context_msg = self.get_greeting_and_context(
            now, user_name, summary.total_screen_time_s, formatted_total
        )
        self._greeting_label.setText(greeting)
        self._context_label.setText(context_msg)

        today = date.today()
        self._date_label.setText(today.strftime("%A, %B %d, %Y"))

        comp = self._engine.get_yesterday_comparison()
        pct = abs(comp["pct_change"]) if comp["pct_change"] is not None else None
        
        # Update Primary Metric
        self._primary_metric.set_data(
            formatted_total,
            pct,
            not comp["is_increase"],
            comp.get("yesterday_was_zero", False)
        )
        self._primary_metric.set_ratios(
            self._engine.format_duration(summary.active_time_s),
            self._engine.format_duration(summary.idle_time_s),
            summary.active_time_s,
            summary.idle_time_s
        )
        
        # Update KPIs
        self._kpi_active.set_value(self._engine.format_duration(summary.active_time_s))
        self._kpi_idle.set_value(self._engine.format_duration(summary.idle_time_s))
        
        # Check Focus status
        from protection.focus_manager import FocusManager
        fm = FocusManager.instance()
        if fm.is_active:
            m, s = divmod(fm.remaining_seconds, 60)
            mode_name = fm.mode.title() if hasattr(fm, "mode") else "Focus"
            self._focus_status_lbl.setText(f"Active: {m:02d}:{s:02d} remaining in {mode_name} mode.")
            self._start_focus_btn.setText("Manage Active Focus")
        else:
            self._focus_status_lbl.setText("No session active. Ready to eliminate distractions.")
            self._start_focus_btn.setText("Start Focus Session")

        # Update Top Applications
        while self._apps_container.count():
            item = self._apps_container.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        top_apps = summary.top_apps
        if not top_apps:
            from ui.theme import ThemeManager
            lbl = QLabel("No application activity recorded today.")
            lbl.setStyleSheet(f"color: {ThemeManager.instance().color('text_muted')}; font-size: 13px;")
            self._apps_container.addWidget(lbl)
        else:
            from ui.widgets.simple_app_row import SimpleAppRow
            for app in top_apps[:4]:
                if app.get("total_s", 0) > 0:
                    dur_s = float(app.get("total_s", 0))
                    row = SimpleAppRow(
                        process_name=app["process_name"],
                        display_name=app.get("display_name", app["process_name"]),
                        duration_s=dur_s
                    )
                    row.clicked.connect(self.request_app_details.emit)
                    self._apps_container.addWidget(row)

        # Update Top Categories
        while self._cats_layout.count():
            item = self._cats_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
                
        category_breakdown = summary.category_breakdown
        if not category_breakdown:
            from ui.theme import ThemeManager
            placeholder2 = QLabel("No category data recorded today.")
            placeholder2.setStyleSheet(f"color: {ThemeManager.instance().color('text_muted')}; font-size: 13px;")
            self._cats_layout.addWidget(placeholder2)
        else:
            sorted_cats2 = sorted(category_breakdown, key=lambda x: float(x.get("total_s", 0.0)), reverse=True)
            for item in sorted_cats2[:3]:
                dur = float(item.get("total_s", 0.0))
                if dur > 0:
                    row2 = ClickableCategoryRow(
                        category=item["category"],
                        duration_s=dur
                    )
                    row2.clicked.connect(self.request_category_details.emit)
                    self._cats_layout.addWidget(row2)

    def on_data_changed(self) -> None:
        self._refresh()

