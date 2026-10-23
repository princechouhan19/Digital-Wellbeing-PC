"""
insights_card.py — Smart Digital Wellbeing Insights card with personalized suggestions and glowing One UI styling.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as get_display_name


from ui.widgets.fluent import FluentCard
from ui.icons import get_icon

class SmartInsightsCard(FluentCard):
    """Smart Digital Wellbeing Insights card with personalized health suggestions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("fluent_card")
        self._engine = AnalyticsEngine()
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        self._lbl = QLabel("Smart Wellbeing Insights")
        self._lbl.setObjectName("section_header")
        hdr.addWidget(self._lbl)
        hdr.addStretch()
        layout.addLayout(hdr)

        self._tips_layout = QVBoxLayout()
        self._tips_layout.setSpacing(10)
        layout.addLayout(self._tips_layout)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#insight_text {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 500; line-height: 1.4; }}
        """)
        
        # Trigger a refresh to re-render the tip colors
        if hasattr(self, "_last_stat"):
            self.refresh(self._last_stat)
        else:
            self.refresh()

    def refresh(self, stat=None) -> None:
        self._last_stat = stat
        while self._tips_layout.count():
            item = self._tips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if stat is None:
            summary = self._engine.get_today_summary()
            tips = self._generate_tips_from_summary(summary)
        else:
            tips = self._generate_tips_from_stat(stat)

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        for tip, icon, color in tips:
            row = QFrame()
            # Glassmorphism styling with colored accent strip
            row.setStyleSheet(
                f"background-color: rgba(255, 255, 255, 0.03); "
                f"border: 1px solid rgba(255, 255, 255, 0.05); "
                f"border-left: 4px solid {color}; "
                f"border-radius: 8px;"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 12, 14, 12)
            rl.setSpacing(16)

            # Icon circle pill
            ic_box = QLabel()
            ic_box.setFixedSize(32, 32)
            ic_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic_box.setStyleSheet(
                f"background-color: {color}18; border: 1px solid {color}30; border-radius: 8px;"
            )
            ic_box.setPixmap(get_icon(icon, color=color, size=16).pixmap(16, 16))

            t_lbl = QLabel(tip)
            t_lbl.setObjectName("insight_text")
            t_lbl.setWordWrap(True)

            rl.addWidget(ic_box)
            rl.addWidget(t_lbl, 1)
            self._tips_layout.addWidget(row)

    def _generate_tips_from_summary(self, summary) -> list[tuple[str, str, str]]:
        tips = []
        total_s = summary.total_screen_time_s
        active_s = summary.active_time_s
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if total_s == 0:
            tips.append(("Insufficient data to generate meaningful insights for today.", "leaf", tm.color('accent')))
            return tips

        comp = self._engine.get_yesterday_comparison()
        
        # Compare Productivity vs Yesterday
        prod_today = sum(c for k, c in comp["today_cats"].items() if k in ("programming", "productivity", "education", "utilities"))
        prod_yest = sum(c for k, c in comp["yesterday_cats"].items() if k in ("programming", "productivity", "education", "utilities"))
        
        if prod_yest > 300:
            pct_prod = ((prod_today - prod_yest) / prod_yest) * 100
            if pct_prod > 10:
                tips.append((f"Productivity increased by {int(pct_prod)}% compared to yesterday.", "trend_up", tm.color('success_text')))
            elif pct_prod < -20:
                tips.append((f"Productivity dropped by {int(abs(pct_prod))}% compared to yesterday.", "trend_down", tm.color('warning_text')))

        # Compare Browsers
        browser_today = comp["today_cats"].get("browser", 0)
        browser_yest = comp["yesterday_cats"].get("browser", 0)
        
        if browser_yest > 300:
            pct_browser = ((browser_today - browser_yest) / browser_yest) * 100
            if pct_browser < -15:
                tips.append((f"You spent {int(abs(pct_browser))}% less time on browsers than yesterday.", "globe", tm.color('info_text')))
            elif pct_browser > 30 and browser_today > 1800:
                tips.append((f"Browser usage is {int(pct_browser)}% higher than yesterday. Consider a focus session.", "hourglass", tm.color('warning_text')))

        # Streak calculation
        long_term = self._engine.get_long_term_analytics()
        streak = long_term.get("current_streak", 0)
        
        if streak >= 3:
            tips.append((f"You achieved your screen time goal for {streak} consecutive days.", "flame", tm.color('accent')))
            
        # Top app highlight (fallback)
        if len(tips) < 3 and summary.top_apps:
            top_app_name = get_display_name(summary.top_apps[0]["process_name"])
            top_app_dur = AnalyticsEngine.format_duration_short(summary.top_apps[0]["total_s"])
            tips.append((f"{top_app_name} is your most active application today with {top_app_dur} usage.", "bar_chart", tm.color('info_text')))
            
        if not tips:
             tips.append(("Data is currently insufficient for robust comparison.", "sparkles", tm.color('text_sub')))

        return tips[:3]

    def _generate_tips_from_stat(self, stat) -> list[tuple[str, str, str]]:
        tips = []
        total_s = stat.total_screen_time_s
        active_s = stat.active_time_s
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        import json
        categories = json.loads(stat.category_usage_json)
        apps = json.loads(stat.app_usage_json)

        productive_s = 0.0
        for item in categories:
            cat_name = item["category"].lower()
            if cat_name in ("programming", "productivity", "education", "utilities"):
                productive_s += item["total_s"]

        if active_s > 0:
            prod_pct = (productive_s / active_s) * 100
            if prod_pct >= 60:
                tips.append((f"{prod_pct:.0f}% of screen time was allocated to high-value productivity tasks.", "target", tm.color('success_text')))
            elif prod_pct < 30 and active_s > 1800:
                tips.append((f"Entertainment load comprised {(100-prod_pct):.0f}% of screen time.", "hourglass", tm.color('warning_text')))

        if total_s > 6 * 3600:
            tips.append(("Screen time exceeded 6 hours.", "eye", tm.color('danger_text')))
        elif total_s < 2 * 3600:
            tips.append(("Screen time remained under 2 hours.", "sparkles", tm.color('accent')))

        if apps:
            top_app_name = get_display_name(apps[0]["process_name"])
            top_app_dur = AnalyticsEngine.format_duration_short(apps[0]["total_s"])
            tips.append((f"Primary focus was {top_app_name} with {top_app_dur} of active engagement.", "bar_chart", tm.color('info_text')))

        return tips[:3]
