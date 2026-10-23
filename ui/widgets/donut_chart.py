"""
donut_chart.py — Responsive Donut Chart and Category Breakdown Card for Digital Wellbeing.
Solves legend overlapping, auto-wraps long labels, shows Top 5 + Other, and adapts to any window size.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from analytics.engine import AnalyticsEngine
from core.constants import CATEGORY_COLORS, AppCategory, get_category_colors
from ui.theme import get_theme_tokens, ThemeManager
from ui import design_system as ds


class DonutChart(QWidget):
    """Responsive Antialiased Donut Chart Ring with Center Typography."""
    segment_hovered = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._segments: List[Tuple[str, float, str]] = []
        self._total: float = 0.0
        self._center_text: str = ""
        self._center_subtext: str = ""
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        
        self._hovered_label: str = ""
        self._hit_paths: List[Tuple[QPainterPath, str]] = []

        # Sweep-in reveal animation (Apple ring style)
        self._reveal = 1.0
        self._reveal_anim = QVariantAnimation(self)
        self._reveal_anim.setDuration(680)
        self._reveal_anim.setStartValue(0.0)
        self._reveal_anim.setEndValue(1.0)
        self._reveal_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._reveal_anim.valueChanged.connect(self._on_reveal)

        from PySide6.QtCore import QTimer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._update_animations)
        self._anim_timer.setInterval(16)
        
        self._current_opacities = {}
        self._current_scales = {}

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)

    def _apply_theme(self, is_dark: bool) -> None:
        self.update()

    def _on_reveal(self, val) -> None:
        self._reveal = float(val)
        self.update()

    def set_data(
        self,
        segments: List[Tuple[str, float, str]],
        center_text: str = "",
        center_subtext: str = "",
    ) -> None:
        self._segments = segments
        self._total = sum(s[1] for s in segments)
        self._center_text = center_text
        self._center_subtext = center_subtext
        
        self._current_opacities = {s[0]: 1.0 for s in segments}
        self._current_scales = {s[0]: 1.0 for s in segments}
        self._reveal_anim.stop()
        self._reveal_anim.start()
        self.update()

    def set_highlighted_segment(self, label: str) -> None:
        if self._hovered_label == label:
            return
        self._hovered_label = label
        self._anim_timer.start()

    def _update_animations(self):
        changed = False
        any_hovered = bool(self._hovered_label)
        
        for label, _, _ in self._segments:
            target_opacity = 1.0
            target_scale = 1.0
            
            if any_hovered:
                if label == self._hovered_label:
                    target_opacity = 1.0
                    target_scale = 1.05
                else:
                    target_opacity = 0.3
                    target_scale = 1.0
                    
            curr_o = self._current_opacities.get(label, 1.0)
            curr_s = self._current_scales.get(label, 1.0)
            
            if abs(curr_o - target_opacity) > 0.02:
                curr_o += 0.12 * (1 if target_opacity > curr_o else -1)
                changed = True
            else:
                curr_o = target_opacity
                
            if abs(curr_s - target_scale) > 0.002:
                curr_s += 0.006 * (1 if target_scale > curr_s else -1)
                changed = True
            else:
                curr_s = target_scale
                
            self._current_opacities[label] = curr_o
            self._current_scales[label] = curr_s
            
        if changed:
            self.update()
        else:
            self._anim_timer.stop()

    def mouseMoveEvent(self, event):
        pos = event.position()
        hovered = ""
        for path, label in self._hit_paths:
            if path.contains(pos):
                hovered = label
                break
                
        if hovered != self._hovered_label:
            self.set_highlighted_segment(hovered)
            self.segment_hovered.emit(hovered)
            
            if hovered:
                for lbl, val, _ in self._segments:
                    if lbl == hovered:
                        pct = max(1, int((val / self._total) * 100)) if self._total > 0 else 0
                        dur_str = AnalyticsEngine.format_duration_short(val)
                        from PySide6.QtWidgets import QToolTip
                        from PySide6.QtGui import QCursor
                        QToolTip.showText(QCursor.pos(), f"{lbl}\n{dur_str} ({pct}%)", self)
                        break
            else:
                from PySide6.QtWidgets import QToolTip
                QToolTip.hideText()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.set_highlighted_segment("")
        self.segment_hovered.emit("")
        from PySide6.QtWidgets import QToolTip
        QToolTip.hideText()

    def paintEvent(self, event) -> None:
        if not self._segments or self._total <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        track_color = QColor(tm.color("border"))
        center_bg = QColor(tm.color("card_bg"))
        text_color = QColor(tm.color("text_main"))
        subtext_color = QColor(tm.color("text_sub"))

        size = min(self.width(), self.height())
        margin = 15
        base_outer_r = (size - margin * 2) / 2.0
        inner_r = base_outer_r * 0.80
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        track_path = QPainterPath()
        track_path.addEllipse(QRectF(cx - base_outer_r, cy - base_outer_r, base_outer_r * 2, base_outer_r * 2))
        track_path.addEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
        painter.fillPath(track_path, track_color)

        angle = 90.0
        gap = 2.4 if len(self._segments) > 1 else 0.0
        sweep_elapsed = self._reveal * 360.0  # degrees swept clockwise from start

        self._hit_paths.clear()

        for label, value, color_str in self._segments:
            span = (value / self._total) * 360.0
            if span < 0.5:
                continue

            # Reveal: each segment draws only the part the sweep has reached
            swept_to_start = 90.0 - angle  # 0 → 360 as we progress through the loop
            drawn_span = min(span, max(0.0, sweep_elapsed - swept_to_start))
            if drawn_span <= 0.3:
                angle -= span
                continue

            scale = self._current_scales.get(label, 1.0)
            opacity = self._current_opacities.get(label, 1.0)
            outer_r = base_outer_r * scale

            path = QPainterPath()
            path.moveTo(QPointF(
                cx + outer_r * math.cos(math.radians(-angle)),
                cy + outer_r * math.sin(math.radians(-angle)),
            ))

            arc_rect_outer = QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2)
            arc_rect_inner = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

            path.arcTo(arc_rect_outer, angle, -drawn_span + gap)
            end_rad = math.radians(-(angle - drawn_span + gap))
            path.lineTo(QPointF(
                cx + inner_r * math.cos(end_rad),
                cy + inner_r * math.sin(end_rad),
            ))
            path.arcTo(arc_rect_inner, angle - drawn_span + gap, drawn_span - gap)
            path.closeSubpath()

            if self._reveal >= 1.0:
                self._hit_paths.append((path, label))

            col = QColor(color_str)
            col.setAlphaF(opacity)
            painter.fillPath(path, col)
            angle -= span

        bg_circle = QPainterPath()
        bg_circle.addEllipse(QRectF(cx - inner_r + 0.5, cy - inner_r + 0.5, (inner_r - 0.5) * 2, (inner_r - 0.5) * 2))
        painter.fillPath(bg_circle, center_bg)

        if self._center_text:
            painter.setPen(text_color)
            font = painter.font()
            font.setFamily("Inter Display")
            font.setPointSize(max(14, int(inner_r * 0.26)))
            font.setWeight(QFont.Weight.DemiBold)
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 98)
            painter.setFont(font)
            # Bottom-align just above the ring center so the subtext never overlaps
            painter.drawText(
                QRectF(cx - inner_r, cy - inner_r + int(inner_r * 0.10), inner_r * 2, inner_r * 0.90),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                self._center_text,
            )

        if self._center_subtext:
            painter.setPen(subtext_color)
            font = painter.font()
            font.setFamily("Inter")
            font.setPointSize(max(7, int(inner_r * 0.115)))
            font.setWeight(QFont.Weight.Medium)
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 108)
            painter.setFont(font)
            painter.drawText(
                QRectF(cx - inner_r, cy + int(inner_r * 0.14), inner_r * 2, inner_r * 0.7),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                self._center_subtext.upper(),
            )

        painter.end()


class CategoryLegendWidget(QWidget):
    """Responsive Category Legend with Top 5 + Other consolidation, auto-wrapping labels, and zero overlapping."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 4, 0, 4)
        self._layout.setSpacing(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        text_muted = tm.color("text_muted")

        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget() and getattr(item.widget(), "is_legend_row", False):
                row_widget = item.widget()
                name_lbl = row_widget.findChild(QLabel, "name_lbl")
                dur_lbl = row_widget.findChild(QLabel, "dur_lbl")
                pct_lbl = row_widget.findChild(QLabel, "pct_lbl")
                if name_lbl: name_lbl.setStyleSheet(f"color: {text_main}; font-size: 13px; font-weight: 500;")
                if dur_lbl: dur_lbl.setStyleSheet(f"color: {text_sub}; font-size: 12px; font-weight: 600;")
                if pct_lbl: pct_lbl.setStyleSheet(f"color: {text_muted}; font-size: 12px; font-weight: 400;")

    def set_data(self, category_breakdown: list[dict] | None, active_seconds: float) -> list[tuple[str, float, str]]:
        """Populate legend items and return consolidated segments for chart rendering."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
                        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if not category_breakdown or active_seconds <= 0:
            lbl = QLabel("Tracking active applications...")
            lbl.setStyleSheet(f"color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600;")
            lbl.setWordWrap(True)
            self._layout.addWidget(lbl)
            return [("Active", 1.0, tm.color('accent'))]

        agg_map = {}
        category_colors = get_category_colors(tm.is_dark)
        for item in category_breakdown:
            dur = float(item.get("total_s", 0.0))
            if dur <= 0:
                continue
            cat_raw = item.get("category", "").title()
            try:
                cat_enum = AppCategory(cat_raw)
                cat_name = cat_enum.value.title()
                color_hex = category_colors.get(cat_enum, tm.color('accent'))
            except ValueError:
                cat_name = "Other"
                color_hex = category_colors.get(AppCategory.OTHER, tm.color('text_muted'))
            
            if cat_name not in agg_map:
                agg_map[cat_name] = {"dur": 0.0, "color": color_hex}
            agg_map[cat_name]["dur"] += dur

        sorted_cats = sorted(agg_map.items(), key=lambda x: x[1]["dur"], reverse=True)
        top_cats = sorted_cats[:5]
        remaining = sorted_cats[5:]

        consolidated: list[tuple[str, float, str]] = []
        for name, data in top_cats:
            consolidated.append((name, data["dur"], data["color"]))

        if remaining:
            other_dur = sum(data["dur"] for name, data in remaining)
            if other_dur > 0:
                found = False
                for i, (n, d, c) in enumerate(consolidated):
                    if n == "Other":
                        consolidated[i] = (n, d + other_dur, c)
                        found = True
                        break
                if not found:
                    consolidated.append(("Other", other_dur, get_category_colors(tm.is_dark).get(AppCategory.OTHER, tm.color('text_muted'))))

        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")
        text_muted = tm.color("text_muted")

        for cat_name, dur, color_hex in consolidated:
            row_widget = QWidget()
            row_widget.is_legend_row = True
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 3, 0, 3)
            row_layout.setSpacing(10)

            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color_hex}; font-size: 11px;")
            dot.setFixedWidth(14)
            dot.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

            cpct = max(1, int((dur / active_seconds) * 100))
            name_lbl = QLabel(f"{cat_name}")
            name_lbl.setObjectName("name_lbl")
            name_lbl.setStyleSheet(f"color: {text_main}; font-size: 13px; font-weight: 500;")
            name_lbl.setWordWrap(True)
            name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

            pct_lbl = QLabel(f"{cpct}%")
            pct_lbl.setObjectName("pct_lbl")
            pct_lbl.setStyleSheet(f"color: {text_muted}; font-size: 12px; font-weight: 400;")
            pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            pct_lbl.setMinimumWidth(36)

            dur_lbl = QLabel(AnalyticsEngine.format_duration_short(dur))
            dur_lbl.setObjectName("dur_lbl")
            dur_lbl.setStyleSheet(f"color: {text_sub}; font-size: 12px; font-weight: 600;")
            dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            dur_lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
            dur_lbl.setMinimumWidth(55)

            row_layout.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(name_lbl, 1)
            row_layout.addWidget(pct_lbl, 0, Qt.AlignmentFlag.AlignTop)
            row_layout.addWidget(dur_lbl, 0, Qt.AlignmentFlag.AlignTop)

            self._layout.addWidget(row_widget)

        self._layout.addStretch()
        return consolidated


class CategoryBreakdownCard(QFrame):
    """Complete, responsive Category Breakdown Card combining Donut Chart and Legend without overlapping."""
    category_clicked = Signal(str)

    def __init__(self, title: str = "Category Breakdown", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dense_card")
        self._setup_ui(title)
        
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self, title: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        self._hdr = QLabel(title)
        self._hdr.setObjectName("section_header")
        layout.addWidget(self._hdr)

        container_widget = QWidget()
        container = QHBoxLayout(container_widget)
        container.setContentsMargins(0, 0, 0, 0)
        container.setSpacing(40)
        container.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.donut = DonutChart()
        self.donut.setFixedSize(180, 180)
        self.donut.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        container.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignTop)

        self.legend = CategoryLegendWidget()
        self.legend.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        container.addWidget(self.legend)

        container.addStretch()
        layout.addWidget(container_widget, 1)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#section_header {{ font-size: 14px; font-weight: 700; color: {tm.color('accent')}; letter-spacing: 1.2px; }}
        """)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.category_clicked.emit("All Categories")

    def set_data(self, category_breakdown: list[dict] | None, active_seconds: float, total_screen_time_s: float = 0.0) -> None:
        """Update legend items and redraw chart ring."""
        segments = self.legend.set_data(category_breakdown, active_seconds)
        
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        display_total = total_screen_time_s if total_screen_time_s > 0 else active_seconds
        
        if active_seconds > 0 and segments:
            self.donut.set_data(
                segments,
                center_text=AnalyticsEngine.format_duration_short(display_total),
                center_subtext="TOTAL SCREEN TIME",
            )
        else:
            self.donut.set_data(
                [("Active", 1.0, tm.color('accent'))],
                center_text="0m",
                center_subtext="TOTAL SCREEN TIME",
            )
