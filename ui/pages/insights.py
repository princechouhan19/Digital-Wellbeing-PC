"""
insights.py — Smart Insights & Analytics Highlights Page for Digital Wellbeing.
Purely derived from real tracked SQLite data. No fake scores or psychological claims.
"""
from __future__ import annotations

from datetime import date, timedelta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy, QGridLayout,
    QPushButton,
)
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager
from ui.icons import get_icon
from tracker.categorizer import display_name as get_friendly_name


class InsightHighlightCard(QFrame):
    """Clean frosted card for key metrics on the Insights page."""
    def __init__(self, title: str, val: str, sub: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName("v2_card")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)
        
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(8)
        
        title_lbl = QLabel(title)
        title_lbl.setObjectName("metric_hdr")
        hdr_row.addWidget(title_lbl)
        hdr_row.addStretch()
        
        ico = QLabel()
        ico.setPixmap(get_icon(icon_name, color=ThemeManager.instance().color('text_muted'), size=15).pixmap(15, 15))
        hdr_row.addWidget(ico)
        layout.addLayout(hdr_row)
        
        self.val_lbl = QLabel(val)
        self.val_lbl.setObjectName("metric_val")
        layout.addWidget(self.val_lbl)
        
        self.sub_lbl = QLabel(sub)
        self.sub_lbl.setObjectName("metric_sub")
        layout.addWidget(self.sub_lbl)


class InsightsPage(QWidget):
    """Synthesized analytics and behavioral insights page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._engine = AnalyticsEngine()
        self._setup_ui()
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(32, 28, 32, 28)
        self._inner_layout.setSpacing(24)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Header Title
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("Insights")
        title.setObjectName("page_title")
        subtitle = QLabel("Synthesized behavioral trends and observations derived from your local activity.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box, 1)
        self._report_btn = QPushButton("Weekly report")
        self._report_btn.setObjectName("secondary_pill_btn")
        self._report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._report_btn.setIcon(get_icon("bar_chart", color=ThemeManager.instance().color("text_sub"), size=14))
        self._report_btn.clicked.connect(self._open_weekly_report)
        header_row.addWidget(self._report_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._inner_layout.addLayout(header_row)

        # 1. YOUR DIGITAL DAY Hero Card
        self._hero_card = QFrame()
        self._hero_card.setObjectName("hero_card")
        hero_layout = QVBoxLayout(self._hero_card)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(12)

        hero_top_row = QHBoxLayout()
        hero_tag = QLabel("YOUR DIGITAL DAY")
        hero_tag.setObjectName("hero_tag")
        hero_top_row.addWidget(hero_tag)
        hero_top_row.addStretch()
        hero_layout.addLayout(hero_top_row)

        self._hero_headline = QLabel("Observing your digital day...")
        self._hero_headline.setObjectName("hero_headline")
        self._hero_headline.setWordWrap(True)
        hero_layout.addWidget(self._hero_headline)

        self._hero_narrative = QLabel("Detailed metrics are synthesized locally from your verified activity log.")
        self._hero_narrative.setObjectName("hero_narrative")
        self._hero_narrative.setWordWrap(True)
        hero_layout.addWidget(self._hero_narrative)

        self._inner_layout.addWidget(self._hero_card)

        # 2. Key Metrics Row
        lbl_kpis = QLabel("CORE HIGHLIGHTS")
        lbl_kpis.setObjectName("section_header")
        self._inner_layout.addWidget(lbl_kpis)

        self._metrics_row = QHBoxLayout()
        self._metrics_row.setSpacing(14)
        self._card_screen_time = InsightHighlightCard("SCREEN TIME", "0h 0m", "Total recorded today", "clock")
        self._card_active_time = InsightHighlightCard("ACTIVE TIME", "0h 0m", "0% active ratio", "usage")
        self._card_top_cat = InsightHighlightCard("TOP CATEGORY", "-", "Most frequent activity", "apps")
        self._card_top_app = InsightHighlightCard("TOP APPLICATION", "-", "0m recorded", "shield")

        self._metrics_row.addWidget(self._card_screen_time)
        self._metrics_row.addWidget(self._card_active_time)
        self._metrics_row.addWidget(self._card_top_cat)
        self._metrics_row.addWidget(self._card_top_app)
        self._inner_layout.addLayout(self._metrics_row)

        # 2b. Attention Quality: fragmentation + flow
        lbl_attention = QLabel("ATTENTION QUALITY")
        lbl_attention.setObjectName("section_header")
        self._inner_layout.addWidget(lbl_attention)

        from ui.widgets.attention_cards import FlowContinuityCard, FocusFragmentationCard

        self._attention_row = QHBoxLayout()
        self._attention_row.setSpacing(14)
        self._fragmentation_card = FocusFragmentationCard()
        self._flow_card = FlowContinuityCard()
        self._attention_row.addWidget(self._fragmentation_card, 1)
        self._attention_row.addWidget(self._flow_card, 1)
        self._inner_layout.addLayout(self._attention_row)

        # 3. Category Distribution Donut
        lbl_dist = QLabel("CATEGORY DISTRIBUTION")
        lbl_dist.setObjectName("section_header")
        self._inner_layout.addWidget(lbl_dist)

        self._breakdown_container = QVBoxLayout()
        self._breakdown_container.setSpacing(12)
        self._inner_layout.addLayout(self._breakdown_container)

        # 4. Long-Term Habits & Trend Analysis
        lbl_trends = QLabel("HABIT PATTERNS & TRENDS")
        lbl_trends.setObjectName("section_header")
        self._inner_layout.addWidget(lbl_trends)

        self._patterns_grid = QGridLayout()
        self._patterns_grid.setSpacing(14)
        self._card_best_day = InsightHighlightCard("PEAK PRODUCTIVE DAY", "-", "Based on longest focused duration", "flame")
        self._card_longest_session = InsightHighlightCard("LONGEST UNBROKEN SESSION", "-", "Single continuous session", "hourglass")
        self._card_avg_daily = InsightHighlightCard("DAILY AVERAGE", "0h 0m", "Historical baseline", "activity")
        self._card_streak = InsightHighlightCard("CONSISTENCY STREAK", "0 Days", "Days actively tracked", "sparkles")

        self._patterns_grid.addWidget(self._card_best_day, 0, 0)
        self._patterns_grid.addWidget(self._card_longest_session, 0, 1)
        self._patterns_grid.addWidget(self._card_avg_daily, 1, 0)
        self._patterns_grid.addWidget(self._card_streak, 1, 1)
        self._inner_layout.addLayout(self._patterns_grid)

        self._inner_layout.addStretch()

        self._refresh()

    def _open_weekly_report(self) -> None:
        from ui.widgets.weekly_report_dialog import WeeklyReportDialog

        dialog = WeeklyReportDialog(parent=self.window())
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _refresh(self):
        self._clear_layout(self._breakdown_container)

        summary = self._engine.get_today_summary()
        long_term = self._engine.get_long_term_analytics()
        comparison = self._engine.get_yesterday_comparison()
        fragmentation = self._engine.get_focus_fragmentation()
        flow = self._engine.get_flow_analytics(days=7)

        self._fragmentation_card.update_data(fragmentation)
        self._flow_card.update_data(flow)

        # Update Hero Headline & Narrative
        total_s = summary.total_screen_time_s
        active_s = summary.active_time_s
        idle_s = summary.idle_time_s
        pct_active = int((active_s / max(total_s, 1)) * 100)

        total_fmt = self._engine.format_duration(total_s)
        active_fmt = self._engine.format_duration(active_s)

        pct_change = comparison.get("pct_change")
        if pct_change is not None:
            if pct_change < 0:
                change_str = f"↓ {abs(pct_change):.1f}% less screen time compared to yesterday."
            elif pct_change > 0:
                change_str = f"↑ {pct_change:.1f}% more screen time compared to yesterday."
            else:
                change_str = "Screen time matches yesterday's volume."
        else:
            change_str = "Baseline establishing for yesterday comparison."

        top_apps = summary.top_apps
        cats = summary.category_breakdown

        if total_s > 0:
            top_cat_name = cats[0]["category"] if cats else "General"
            if hasattr(top_cat_name, "value"):
                top_cat_name = top_cat_name.value
            self._hero_headline.setText(f"{total_fmt} recorded today  ·  {active_fmt} actively focused")
            self._hero_narrative.setText(
                f"{change_str} Your highest volume category today is {str(top_cat_name).title()}. "
                f"Your active-to-idle engagement ratio is currently {pct_active}%."
            )
        else:
            self._hero_headline.setText("No activity recorded yet today")
            self._hero_narrative.setText("As you interact with applications, local analytics will summarize your productivity patterns here.")

        # Key Metrics Row
        self._card_screen_time.val_lbl.setText(total_fmt)
        self._card_active_time.val_lbl.setText(active_fmt)
        self._card_active_time.sub_lbl.setText(f"{pct_active}% active engagement")

        if cats:
            top_c = cats[0]["category"]
            c_name = top_c.value if hasattr(top_c, "value") else str(top_c)
            self._card_top_cat.val_lbl.setText(c_name.title())
            c_dur = self._engine.format_duration_short(cats[0].get("total_s", 0))
            self._card_top_cat.sub_lbl.setText(f"{c_dur} accumulated")
        else:
            self._card_top_cat.val_lbl.setText("-")
            self._card_top_cat.sub_lbl.setText("No categories yet")

        if top_apps:
            t_app = top_apps[0]
            app_disp = get_friendly_name(t_app["process_name"])
            self._card_top_app.val_lbl.setText(app_disp)
            self._card_top_app.sub_lbl.setText(f"{self._engine.format_duration_short(t_app['total_s'])} focused")
        else:
            self._card_top_app.val_lbl.setText("-")
            self._card_top_app.sub_lbl.setText("No apps yet")

        # Category Donut Card
        from ui.widgets.donut_chart import CategoryBreakdownCard
        donut_card = CategoryBreakdownCard("Category Allocation")
        donut_card.set_data(cats, total_s, total_s)
        self._breakdown_container.addWidget(donut_card)

        # Habit Patterns Grid
        best_day = long_term.get("most_productive_day")
        if best_day:
            self._card_best_day.val_lbl.setText(best_day.strftime("%A"))
            self._card_best_day.sub_lbl.setText(f"Peak recorded on {best_day.strftime('%b %d')}")
        else:
            self._card_best_day.val_lbl.setText("-")
            self._card_best_day.sub_lbl.setText("Accumulating historical days")

        if summary.longest_session_app:
            self._card_longest_session.val_lbl.setText(self._engine.format_duration_short(summary.longest_session_s))
            self._card_longest_session.sub_lbl.setText(f"On {get_friendly_name(summary.longest_session_app)}")
        else:
            self._card_longest_session.val_lbl.setText("-")
            self._card_longest_session.sub_lbl.setText("No long sessions recorded")

        avg_daily_s = summary.average_daily_s
        self._card_avg_daily.val_lbl.setText(self._engine.format_duration(avg_daily_s))
        self._card_avg_daily.sub_lbl.setText(f"{summary.days_tracked} days tracked in range")

        streak = long_term.get("current_streak", 0)
        self._card_streak.val_lbl.setText(f"{streak} Days")
        self._card_streak.sub_lbl.setText(f"Best: {long_term.get('best_streak', 0)} days")

    def _apply_theme(self, is_dark: bool):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel#page_title {{
                font-size: 26px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.5px;
            }}
            QLabel#page_subtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#section_header {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-top: 6px;
            }}
            QFrame#hero_card {{
                background-color: {tm.color('surface')};
                border: 1px solid rgba(10, 132, 255, 0.24);
                border-radius: 14px;
            }}
            QLabel#hero_tag {{
                color: #0A84FF;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: rgba(10, 132, 255, 0.14);
                border: 1px solid rgba(10, 132, 255, 0.30);
                border-radius: 10px;
                padding: 3px 10px;
            }}
            QLabel#hero_headline {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#hero_narrative {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QFrame#v2_card {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#v2_card:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#metric_hdr {{
                color: {tm.color('text_muted')};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.2px;
                text-transform: uppercase;
            }}
            QLabel#metric_val {{
                font-size: 18px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#metric_sub {{
                font-size: 11px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QFrame#attention_card {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#attention_eyebrow {{
                color: {tm.color('text_muted')};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.3px;
            }}
            QLabel#attention_badge {{
                color: {tm.color('text_muted')};
                font-size: 10px;
                font-weight: 600;
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 2px 8px;
            }}
            QLabel#attention_value {{
                color: {tm.color('text_main')};
                font-size: 20px;
                font-weight: 700;
                letter-spacing: -0.4px;
            }}
            QLabel#attention_sub {{
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 500;
            }}
            QLabel#attention_legend {{
                color: {tm.color('text_muted')};
                font-size: 10px;
                font-weight: 500;
            }}
            QLabel#attention_empty {{
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 500;
                padding: 6px 0;
            }}
            QLabel#flow_dot {{ color: #30D158; font-size: 9px; }}
            QLabel#flow_app {{ color: {tm.color('text_main')}; font-size: 12px; font-weight: 600; }}
            QLabel#flow_time {{ color: {tm.color('text_muted')}; font-size: 10px; font-weight: 500; }}
            QPushButton#secondary_pill_btn {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 999px;
                color: {tm.color('text_sub')};
                padding: 7px 15px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#secondary_pill_btn:hover {{
                color: {tm.color('text_main')};
                border-color: {tm.color('accent')};
            }}
        """)
        self._refresh()

    def on_data_changed(self) -> None:
        self._refresh()
