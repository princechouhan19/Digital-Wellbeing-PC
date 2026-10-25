"""
history.py — Daily History Timeline Page in the Aurora design language.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
)
from database.repository import Repository
from analytics.engine import AnalyticsEngine
from ui.theme import ThemeManager


class HistoryTimelineItem(QFrame):
    def __init__(self, date_str: str, active_s: float, idle_s: float, top_app: str, parent=None):
        super().__init__(parent)
        self.setObjectName("timeline_card")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # Left: Date
        date_lbl = QLabel(date_str)
        date_lbl.setObjectName("timeline_date")
        date_lbl.setFixedWidth(120)
        
        # Middle: Graph/Dot
        dot = QLabel("●")
        dot.setObjectName("timeline_dot")
        
        # Right: Stats
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(4)
        
        active_lbl = QLabel(f"Active Screen Time: {AnalyticsEngine.format_duration_short(active_s)}")
        active_lbl.setObjectName("timeline_stat")
        
        idle_lbl = QLabel(f"Idle Time: {AnalyticsEngine.format_duration_short(idle_s)}")
        idle_lbl.setObjectName("timeline_stat_sub")
        
        top_app_lbl = QLabel(f"Primary Application: {top_app if top_app else 'None'}")
        top_app_lbl.setObjectName("timeline_stat_sub")
        
        stats_layout.addWidget(active_lbl)
        stats_layout.addWidget(idle_lbl)
        stats_layout.addWidget(top_app_lbl)
        
        layout.addWidget(date_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(stats_layout, 1)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool = True):
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        card_bg = tm.color('surface_elevated') if not is_dark else "#1E1E20"
        card_hover = tm.color('card_hover') if not is_dark else "#121722"
        border_col = tm.color('border')
        border_hover = tm.color('border_hover')
        text_main = tm.color('text_main')
        text_sub = tm.color('text_sub')
        accent = tm.color('accent')

        self.setStyleSheet(f"""
            QFrame#timeline_card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            QFrame#timeline_card:hover {{
                background-color: {card_hover};
                border-color: {border_hover};
            }}
            QLabel#timeline_date {{
                color: {text_main};
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#timeline_dot {{
                color: {accent};
                font-size: 14px;
            }}
            QLabel#timeline_stat {{
                color: {text_main};
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#timeline_stat_sub {{
                color: {text_sub};
                font-size: 12px;
            }}
        """)


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._repo = Repository()
        self._setup_ui()
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(24)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("History Timeline")
        title.setObjectName("page_title")
        subtitle = QLabel("A chronological view of your daily screen time and primary applications.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(10)
        scroll.setWidget(inner)
        
        layout.addWidget(scroll, 1)
        
        self._build_timeline()
        self._inner_layout.addStretch()

    def _build_timeline(self):
        stats = self._repo.get_all_daily_stats()
        sorted_stats = sorted(stats, key=lambda x: x.date, reverse=True)
        
        if not sorted_stats:
            lbl = QLabel("No historical data recorded yet.")
            lbl.setStyleSheet("color: #6E6E73; font-size: 14px; font-weight: 500; margin-top: 20px;")
            self._inner_layout.addWidget(lbl)
            return
            
        for stat in sorted_stats:
            date_str = stat.date.strftime("%a, %b %d")
            item = HistoryTimelineItem(
                date_str=date_str,
                active_s=stat.active_time_s,
                idle_s=stat.idle_time_s,
                top_app=stat.top_app
            )
            self._inner_layout.insertWidget(self._inner_layout.count() - 1, item)

    def _apply_theme(self, is_dark: bool = True):
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel#page_title {{
                font-size: 26px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.5px;
            }}
            QLabel#page_subtitle {{
                font-size: 14px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
        """)
        
    def on_data_changed(self):
        while self._inner_layout.count() > 1:
            item = self._inner_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
        self._build_timeline()
