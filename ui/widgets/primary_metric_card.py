"""
primary_metric_card.py — The main 'Today's Screen Time' visual for the dashboard.

Aurora: Apple hero card — large Inter Display numeral, tinted trend pill,
hairline-bordered surface with soft hover.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QProgressBar
)
from ui.theme import ThemeManager
from ui import design_system as ds


class PrimaryMetricCard(QFrame):
    card_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("primary_metric_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        # Header: Tag + Click hint
        top_row = QHBoxLayout()
        self._title_lbl = QLabel("Today’s screen time")
        self._title_lbl.setObjectName("metric_title")
        top_row.addWidget(self._title_lbl)
        top_row.addStretch()

        self._hint_lbl = QLabel("Details ›")
        self._hint_lbl.setObjectName("metric_hint")
        top_row.addWidget(self._hint_lbl)
        layout.addLayout(top_row)

        # Primary Dominant Value
        self._value_lbl = QLabel("0h 0m")
        self._value_lbl.setObjectName("metric_value")
        layout.addWidget(self._value_lbl)

        # Trend comparison pill
        self._trend_pill = QFrame()
        self._trend_pill.setObjectName("trend_pill")
        trend_layout = QHBoxLayout(self._trend_pill)
        trend_layout.setContentsMargins(10, 4, 12, 4)
        trend_layout.setSpacing(6)

        self._trend_icon = QLabel("•")
        self._trend_icon.setObjectName("trend_icon")
        self._trend_lbl = QLabel("Calculating comparison...")
        self._trend_lbl.setObjectName("trend_text")

        trend_layout.addWidget(self._trend_icon)
        trend_layout.addWidget(self._trend_lbl)

        pill_row = QHBoxLayout()
        pill_row.addWidget(self._trend_pill)
        pill_row.addStretch()
        layout.addLayout(pill_row)

        # Activity Ratio Bar
        layout.addSpacing(6)
        self._ratio_box = QVBoxLayout()
        self._ratio_box.setSpacing(6)

        ratio_hdr = QHBoxLayout()
        self._active_ratio_lbl = QLabel("Active Time: --")
        self._active_ratio_lbl.setObjectName("ratio_label")
        self._idle_ratio_lbl = QLabel("Idle: --")
        self._idle_ratio_lbl.setObjectName("ratio_label_idle")
        ratio_hdr.addWidget(self._active_ratio_lbl)
        ratio_hdr.addStretch()
        ratio_hdr.addWidget(self._idle_ratio_lbl)
        self._ratio_box.addLayout(ratio_hdr)

        self._ratio_bar = QProgressBar()
        self._ratio_bar.setObjectName("activity_ratio_bar")
        self._ratio_bar.setFixedHeight(6)
        self._ratio_bar.setTextVisible(False)
        self._ratio_bar.setRange(0, 100)
        self._ratio_bar.setValue(100)
        self._ratio_box.addWidget(self._ratio_bar)

        layout.addLayout(self._ratio_box)

        self._apply_theme()
        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#primary_metric_card {{
                background: {tm.color('card_bg')};
                border: 1px solid {tm.color('border')};
                border-radius: {ds.RADIUS['xl']}px;
            }}
            QFrame#primary_metric_card:hover {{
                background: {tm.color('card_hover')};
                border: 1px solid {tm.color('border_hover')};
            }}
            QLabel#metric_title {{
                {ds.type_css('micro', tm.color('text_muted'))}
            }}
            QLabel#metric_hint {{
                color: {tm.color('text_muted')};
                font-size: 12px;
                font-weight: 600;
            }}
            QFrame#primary_metric_card:hover QLabel#metric_hint {{
                color: {tm.color('accent_tint_text')};
            }}
            QLabel#metric_value {{
                color: {tm.color('text_main')};
                font-size: 42px;
                font-weight: 700;
                letter-spacing: -1.2px;
                font-family: {ds.FONT_STACK_DISPLAY};
            }}
            QLabel#ratio_label {{
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#ratio_label_idle {{
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 500;
            }}
            QProgressBar#activity_ratio_bar {{
                background-color: {tm.color('track')};
                border-radius: 3px;
                border: none;
            }}
            QProgressBar#activity_ratio_bar::chunk {{
                background: {tm.color('accent')};
                border-radius: 3px;
            }}
        """)

    def set_data(self, formatted_time: str, pct_change: float, is_decrease: bool, yesterday_was_zero: bool = False):
        self._value_lbl.setText(formatted_time)
        tm = ThemeManager.instance()

        if yesterday_was_zero or pct_change is None:
            self._trend_icon.setText("•")
            self._trend_lbl.setText("No previous baseline")
            self._trend_pill.setStyleSheet(f"""
                QFrame#trend_pill {{
                    background: {tm.color('surface_secondary')};
                    border: 1px solid {tm.color('border')};
                    border-radius: {ds.RADIUS['pill'] if False else 12}px;
                }}
                QLabel#trend_icon, QLabel#trend_text {{
                    color: {tm.color('text_sub')};
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        elif pct_change == 0:
            self._trend_icon.setText("=")
            self._trend_lbl.setText("Equal to yesterday")
            self._trend_pill.setStyleSheet(f"""
                QFrame#trend_pill {{
                    background: {tm.color('surface_secondary')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 12px;
                }}
                QLabel#trend_icon, QLabel#trend_text {{
                    color: {tm.color('text_sub')};
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        elif is_decrease:
            self._trend_icon.setText("↓")
            self._trend_lbl.setText(f"{pct_change:.1f}% less than yesterday")
            self._trend_pill.setStyleSheet(f"""
                QFrame#trend_pill {{
                    background: {tm.color('success_bg')};
                    border: 1px solid {tm.color('success_border')};
                    border-radius: 12px;
                }}
                QLabel#trend_icon, QLabel#trend_text {{
                    color: {tm.color('success_text')};
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)
        else:
            self._trend_icon.setText("↑")
            self._trend_lbl.setText(f"{pct_change:.1f}% more than yesterday")
            self._trend_pill.setStyleSheet(f"""
                QFrame#trend_pill {{
                    background: {tm.color('warning_bg')};
                    border: 1px solid {tm.color('warning_border')};
                    border-radius: 12px;
                }}
                QLabel#trend_icon, QLabel#trend_text {{
                    color: {tm.color('warning_text')};
                    font-size: 12px;
                    font-weight: 600;
                }}
            """)

    def set_ratios(self, active_str: str, idle_str: str, active_s: float, idle_s: float):
        total_s = active_s + idle_s
        if total_s > 0:
            pct = int((active_s / total_s) * 100)
            self._ratio_bar.setValue(pct)
            self._active_ratio_lbl.setText(f"Active Time: {active_str} ({pct}%)")
            self._idle_ratio_lbl.setText(f"Idle: {idle_str} ({100 - pct}%)")
        else:
            self._ratio_bar.setValue(100)
            self._active_ratio_lbl.setText(f"Active Time: {active_str}")
            self._idle_ratio_lbl.setText(f"Idle: {idle_str}")

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            from ui import feedback
            feedback.tap(self)
            self.card_clicked.emit()
