"""
hero_card.py — V2 Hero Screen Time Card for Digital Wellbeing Dashboard.
Features big typography, target countdown, and inline multi-color category breakdown bar.
"""

from __future__ import annotations

from typing import List, Tuple

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from core.constants import CATEGORY_COLORS, AppCategory, get_category_colors
from ui import design_system as ds


class CategoryProportionBar(QWidget):
    """Inline multi-color horizontal proportion bar with category legend."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._segments: List[Tuple[float, QColor]] = []
        self._total_s: float = 0.0

    def set_segments(self, category_breakdown: List[dict] | None, total_s: float) -> None:
        self._segments.clear()
        self._total_s = max(total_s, 0.0)
        if not category_breakdown or self._total_s <= 0:
            self.update()
            return

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        category_colors = get_category_colors(tm.is_dark)

        for item in category_breakdown:
            dur = float(item.get("total_s", 0.0))
            if dur <= 0:
                continue
            cat_str = item.get("category", "").lower()
            try:
                cat = AppCategory(cat_str)
                color_hex = category_colors.get(cat, tm.color("accent"))
            except ValueError:
                color_hex = tm.color("text_muted")
            self._segments.append((dur, QColor(color_hex)))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())
        radius = 6.0

        # Draw base track
        base_path = QPainterPath()
        base_path.addRoundedRect(rect, radius, radius)
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        painter.fillPath(base_path, QColor(tm.color("border")))

        if not self._segments or self._total_s <= 0:
            return

        painter.save()
        painter.setClipPath(base_path)

        curr_x = 0.0
        w = float(self.width())
        for dur, color in self._segments:
            seg_w = (dur / self._total_s) * w
            if seg_w > 0.5:
                seg_rect = QRectF(curr_x, 0, seg_w + 1.0, float(self.height()))
                painter.fillRect(seg_rect, color)
                curr_x += seg_w

        painter.restore()


from ui.widgets.fluent import FluentCard

class HeroCard(FluentCard):
    """Hero card displaying today's screen time, goal progress, multi-color category split, and delta vs yesterday."""

    focus_requested = Signal()
    refresh_requested = Signal()
    card_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Left Column: Primary Screen Time Story & Category Bar
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        self._header_lbl = QLabel("Today’s active screen time")
        self._header_lbl.setObjectName("hero_header")

        self._time_lbl = QLabel("0h 00m")
        self._time_lbl.setObjectName("hero_time")

        # Inline Category Proportion Bar + Legend
        cat_box = QVBoxLayout()
        cat_box.setSpacing(6)
        
        self._cat_bar = CategoryProportionBar()
        cat_box.addWidget(self._cat_bar)

        self._cat_legend_lbl = QLabel("Category Breakdown: Tracking active applications...")
        self._cat_legend_lbl.setObjectName("hero_legend")
        self._cat_legend_lbl.setWordWrap(True)
        cat_box.addWidget(self._cat_legend_lbl)

        # Goal Progress Bar
        goal_col = QVBoxLayout()
        goal_col.setSpacing(6)
        
        goal_hdr = QHBoxLayout()
        self._goal_lbl = QLabel("Daily Target Limit: 8h 00m")
        self._goal_lbl.setObjectName("hero_goal")
        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setObjectName("hero_pct")
        goal_hdr.addWidget(self._goal_lbl)
        goal_hdr.addStretch()
        goal_hdr.addWidget(self._pct_lbl)
        goal_col.addLayout(goal_hdr)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setObjectName("hero_progress")
        goal_col.addWidget(self._progress_bar)

        left_col.addWidget(self._header_lbl)
        left_col.addWidget(self._time_lbl)
        left_col.addLayout(cat_box)
        left_col.addSpacing(4)
        left_col.addLayout(goal_col)
        layout.addLayout(left_col, 1)

        # Right Column: Trend Comparison & Quick Actions
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._badge = QLabel("— vs yesterday")
        self._badge.setObjectName("hero_badge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from ui.widgets.fluent import FluentButton
        self._focus_btn = FluentButton("Start 25m Focus Session", primary=True)
        self._focus_btn.set_icon_name("focus", size=15, color="#FFFFFF")
        self._focus_btn.setMinimumHeight(46)
        self._focus_btn.clicked.connect(self.focus_requested.emit)

        right_col.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._focus_btn, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(right_col)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#hero_header {{ {ds.type_css('micro', tm.color('accent_tint_text'))} text-transform: uppercase; }}
            QLabel#hero_time {{ font-size: 44px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -1.2px; font-family: {ds.FONT_STACK_DISPLAY}; }}
            QLabel#hero_legend {{ font-size: 12px; font-weight: 500; color: {tm.color('text_sub')}; }}
            QLabel#hero_goal {{ font-size: 13px; font-weight: 500; color: {tm.color('text_sub')}; }}
            QLabel#hero_pct {{ font-size: 13px; font-weight: 700; color: {tm.color('accent_tint_text')}; }}
            QProgressBar#hero_progress {{ background-color: {tm.color('track')}; border-radius: 4px; border: none; }}
            QProgressBar#hero_progress::chunk {{ background-color: {tm.color('accent')}; border-radius: 4px; }}
        """)
        
        if hasattr(self, "_badge"):
            self._update_badge_style(getattr(self, "_last_delta_pct", 0.0), getattr(self, "_last_is_decrease", False))

    def _update_badge_style(self, delta_pct: float, is_decrease: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        if delta_pct == 0.0:
            self._badge.setStyleSheet(f"""
                background-color: {tm.color('info_bg')}; color: {tm.color('info_text')};
                border: none; border-radius: 20px;
                font-size: 12px; font-weight: 600; padding: 7px 16px;
            """)
        elif is_decrease:
            self._badge.setStyleSheet(f"""
                background-color: {tm.color('success_bg')}; color: {tm.color('success_text')};
                border: none; border-radius: 20px;
                font-size: 12px; font-weight: 600; padding: 7px 16px;
            """)
        else:
            self._badge.setStyleSheet(f"""
                background-color: {tm.color('danger_bg')}; color: {tm.color('danger_text')};
                border: none; border-radius: 20px;
                font-size: 12px; font-weight: 600; padding: 7px 16px;
            """)

    def set_data(
        self,
        time_str: str,
        delta_pct: float,
        is_decrease: bool,
        active_seconds: float = 0.0,
        target_seconds: float = 28800.0,
        category_breakdown: List[dict] | None = None,
    ) -> None:
        self._last_delta_pct = delta_pct
        self._last_is_decrease = is_decrease
        
        self._time_lbl.setText(time_str)

        # Update Goal Progress
        target_s = max(target_seconds, 1.0)
        pct = min(100, int((active_seconds / target_s) * 100))
        self._progress_bar.setValue(pct)
        self._pct_lbl.setText(f"{pct}%")
        
        target_h = int(target_seconds // 3600)
        rem_s = max(0.0, target_seconds - active_seconds)
        rem_h = int(rem_s // 3600)
        rem_m = int((rem_s % 3600) // 60)
        if active_seconds > target_seconds:
            self._goal_lbl.setText("You exceeded your goal")
        elif active_seconds == target_seconds:
            self._goal_lbl.setText("Goal achieved")
        else:
            self._goal_lbl.setText(f"{rem_h}h {rem_m:02d}m remaining under daily target of {target_h}h 00m")

        # Update Category Proportion Bar & Legend
        self._cat_bar.set_segments(category_breakdown, active_seconds)
        if category_breakdown and active_seconds > 0:
            top_cats = sorted(category_breakdown, key=lambda x: x.get("total_s", 0.0), reverse=True)[:3]
            legend_parts = []
            for c in top_cats:
                dur = float(c.get("total_s", 0.0))
                if dur <= 0:
                    continue
                cpct = int((dur / active_seconds) * 100)
                name = c.get("category", "").title()
                legend_parts.append(f"{name}: {cpct}%")
            if legend_parts:
                self._cat_legend_lbl.setText(" • ".join(legend_parts))
            else:
                self._cat_legend_lbl.setText("Category Breakdown: Active tracking...")
        else:
            self._cat_legend_lbl.setText("Category Breakdown: Tracking active applications...")

        # Update Yesterday Delta Badge
        if delta_pct == 0.0:
            self._badge.setText("Equal to yesterday")
        elif is_decrease:
            self._badge.setText(f"↓ {abs(delta_pct):.1f}% vs yesterday")
        else:
            self._badge.setText(f"↑ {abs(delta_pct):.1f}% vs yesterday")
            
        self._update_badge_style(delta_pct, is_decrease)
