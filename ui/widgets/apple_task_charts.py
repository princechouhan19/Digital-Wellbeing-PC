"""
apple_task_charts.py — Apple Design System visual analytics and hydration widgets for Smart Tasks.

Features:
- DailyActivityRingWidget: Apple Fitness-style circular completion ring with smooth gradient and glow.
- MonthlyTrendLineGraphWidget: Apple Health-style smooth Bezier line chart showing daily consistency over the month.
- WaterIntakeWidget: Interactive hydration tracker with 0.5L and 1.0L checkpoint logging.
"""
from __future__ import annotations

import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, QRectF, QPointF, Signal, Property, QEasingCurve, QPropertyAnimation
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from database.repository import Repository
from ui.theme import ThemeManager


# ─── 1. Apple Fitness Daily Activity Ring Widget ─────────────────────────────

class DailyActivityRingWidget(QWidget):
    """Circular progress ring styled after Apple Fitness Activity Rings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 180)
        self.setMaximumSize(220, 220)
        self._completed = 0
        self._total = 0
        self._percent = 0.0

    def set_stats(self, completed: int, total: int) -> None:
        self._completed = completed
        self._total = total
        self._percent = (completed / total * 100.0) if total > 0 else 0.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        center = QPointF(w / 2.0, h / 2.0)
        margin = 18.0
        radius = (side / 2.0) - margin
        stroke_width = 14.0

        ring_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)

        # 1. Background Track (translucent Apple dark track)
        track_pen = QPen(QColor(255, 255, 255, 22), stroke_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(ring_rect, 0, 360 * 16)

        # 2. Glowing Active Arc
        if self._percent > 0:
            angle_span = int(-min(100.0, self._percent) / 100.0 * 360 * 16)
            
            # Gradient from Apple Cyan to Vibrant Blue/Emerald
            grad = QLinearGradient(ring_rect.topLeft(), ring_rect.bottomRight())
            if self._percent >= 100:
                grad.setColorAt(0.0, QColor("#30D158"))  # Apple Green
                grad.setColorAt(1.0, QColor("#34C759"))
            elif self._percent >= 50:
                grad.setColorAt(0.0, QColor("#0A84FF"))  # Apple Blue
                grad.setColorAt(1.0, QColor("#5E5CE6"))  # Apple Indigo
            else:
                grad.setColorAt(0.0, QColor("#FF9F0A"))  # Apple Orange
                grad.setColorAt(1.0, QColor("#FF453A"))  # Apple Red

            arc_pen = QPen(QBrush(grad), stroke_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            # Start from top (90 degrees in Qt angles)
            painter.drawArc(ring_rect, 90 * 16, angle_span)

        # 3. Center Typography
        # Percentage Number
        painter.setPen(QColor("#FFFFFF"))
        font_pct = QFont("Inter", 22, QFont.Weight.Bold)
        font_pct.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font_pct)
        pct_text = f"{int(self._percent)}%"
        painter.drawText(QRectF(w / 2.0 - 50, h / 2.0 - 24, 100, 30), Qt.AlignmentFlag.AlignCenter, pct_text)

        # Subtitle Fraction
        painter.setPen(QColor("#8E8E93"))
        font_sub = QFont("Inter", 10, QFont.Weight.DemiBold)
        painter.setFont(font_sub)
        sub_text = f"{self._completed}/{self._total} DONE"
        painter.drawText(QRectF(w / 2.0 - 60, h / 2.0 + 8, 120, 20), Qt.AlignmentFlag.AlignCenter, sub_text)


# ─── 2. Apple Health Monthly Trend Line Graph Widget ─────────────────────────

class MonthlyTrendLineGraphWidget(QWidget):
    """Smooth Bezier line chart showing 30-day task completion consistency."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setSizePolicy(QWidget.sizePolicy(self).Policy.Expanding, QWidget.sizePolicy(self).Policy.Fixed)
        self._data: List[dict] = []

    def set_data(self, data: List[dict]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pad_l = 28.0
        pad_r = 20.0
        pad_t = 16.0
        pad_b = 26.0

        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        # 1. Subtle horizontal grid lines (25%, 50%, 75%, 100%)
        grid_pen = QPen(QColor(255, 255, 255, 16), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for pct in (25, 50, 75, 100):
            y = pad_t + plot_h - (pct / 100.0 * plot_h)
            painter.drawLine(QPointF(pad_l, y), QPointF(w - pad_r, y))

        if not self._data:
            return

        n = len(self._data)
        points: List[QPointF] = []
        for i, item in enumerate(self._data):
            rate = item.get("completion_rate", 0.0)
            x = pad_l + (i / max(1, n - 1)) * plot_w
            y = pad_t + plot_h - (rate / 100.0 * plot_h)
            points.append(QPointF(x, y))

        if len(points) < 2:
            return

        # 2. Build Smooth Cubic Bezier Path
        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(len(points) - 1):
            p0 = points[i]
            p1 = points[i + 1]
            ctrl_dist = (p1.x() - p0.x()) / 2.0
            c1 = QPointF(p0.x() + ctrl_dist, p0.y())
            c2 = QPointF(p1.x() - ctrl_dist, p1.y())
            path.cubicTo(c1, c2, p1)

        # 3. Soft Gradient Fill below the line
        fill_path = QPainterPath(path)
        fill_path.lineTo(points[-1].x(), pad_t + plot_h)
        fill_path.lineTo(points[0].x(), pad_t + plot_h)
        fill_path.closeSubpath()

        fill_grad = QLinearGradient(QPointF(0, pad_t), QPointF(0, pad_t + plot_h))
        fill_grad.setColorAt(0.0, QColor(10, 132, 255, 60))
        fill_grad.setColorAt(1.0, QColor(10, 132, 255, 0))
        painter.fillPath(fill_path, QBrush(fill_grad))

        # 4. Stroke the Line
        line_pen = QPen(QColor("#0A84FF"), 2.5)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(line_pen)
        painter.drawPath(path)

        # 5. Highlight Today point
        today_pt = None
        for i, item in enumerate(self._data):
            if item.get("is_today"):
                today_pt = points[i]
                break

        if today_pt:
            # Outer glow
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(10, 132, 255, 80))
            painter.drawEllipse(today_pt, 7, 7)
            # Inner dot
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(today_pt, 3.5, 3.5)

        # 6. Date labels along bottom
        painter.setPen(QColor("#8E8E93"))
        font_lbl = QFont("Inter", 8, QFont.Weight.Medium)
        painter.setFont(font_lbl)
        step = max(1, n // 6)
        for i in range(0, n, step):
            pt = points[i]
            day_str = f"{self._data[i].get('day', i+1)}"
            painter.drawText(QRectF(pt.x() - 12, pad_t + plot_h + 6, 24, 16), Qt.AlignmentFlag.AlignCenter, day_str)


# ─── 3. Apple Health Water Intake Widget ─────────────────────────────────────

class WaterCapsuleProgressBar(QWidget):
    """Apple Health-style fluid water progress capsule with smooth gradients and milestone markers."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self._progress = 0.0  # 0.0 to 1.0 (or >1.0)
        self._anim = QPropertyAnimation(self, b"progress", self)
        self._anim.setDuration(400)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, val: float):
        self._progress = max(0.0, float(val))
        self.update()

    progress = Property(float, get_progress, set_progress)

    def animate_to(self, target: float):
        self._anim.stop()
        self._anim.setStartValue(self._progress)
        self._anim.setEndValue(max(0.0, float(target)))
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        r = h / 2.0

        # Background track
        track_rect = QRectF(0, 0, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(track_rect, r, r)

        # Milestone ticks (25%, 50%, 75%)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1.5))
        for frac in (0.25, 0.50, 0.75):
            tx = w * frac
            p.drawLine(QPointF(tx, 2.5), QPointF(tx, h - 2.5))

        # Fill
        fill_pct = min(1.0, self._progress)
        if fill_pct > 0.0:
            fill_w = max(h, w * fill_pct)
            fill_rect = QRectF(0, 0, fill_w, h)
            grad = QLinearGradient(0, 0, fill_w, 0)
            if self._progress >= 1.0:
                # Goal completed! Vibrant Apple Emerald Cyan celebration
                grad.setColorAt(0.0, QColor("#0A84FF"))
                grad.setColorAt(0.5, QColor("#00C7BE"))
                grad.setColorAt(1.0, QColor("#30D158"))
            else:
                grad.setColorAt(0.0, QColor("#0071E3"))
                grad.setColorAt(0.65, QColor("#0A84FF"))
                grad.setColorAt(1.0, QColor("#38BDF8"))

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, r, r)

            # High-end liquid glass sheen on upper half
            sheen_rect = QRectF(1.0, 1.0, fill_w - 2.0, h / 2.0 - 0.5)
            sheen_grad = QLinearGradient(0, 1.0, 0, h / 2.0)
            sheen_grad.setColorAt(0.0, QColor(255, 255, 255, 75))
            sheen_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(sheen_grad)
            p.drawRoundedRect(sheen_rect, r - 1.0, r - 1.0)


class WaterIntakeWidget(QFrame):
    """Apple Health-style hydration tracking card with customizable goals and milestone logging."""

    water_updated = Signal(dict)

    def __init__(self, repo: Repository, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("water_card")
        self._repo = repo
        self._data = {"target_ml": 3000, "current_ml": 0, "checkpoints": []}
        self._block_goal_signal = False
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)

        # 1. Apple Health Card Header: Category Badge + Title (Left), Goal Selector (Right)
        header = QHBoxLayout()
        header.setSpacing(10)

        # Left: Water drop badge with subtle cyan aura
        icon_badge = QLabel("💧")
        icon_badge.setObjectName("water_icon_badge")
        icon_badge.setFixedSize(32, 32)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(icon_badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        sub_tag = QLabel("WATER INTAKE")
        sub_tag.setObjectName("water_tag")
        title = QLabel("Daily Hydration")
        title.setObjectName("water_title")
        title_col.addWidget(sub_tag)
        title_col.addWidget(title)
        header.addLayout(title_col, 1)

        # Right: Interactive Goal Selector (Allows user to select 2L, 2.5L, 3L, 3.5L, 4L, 5L, or custom)
        goal_box = QHBoxLayout()
        goal_box.setSpacing(4)
        goal_lbl = QLabel("Goal:")
        goal_lbl.setObjectName("water_goal_lbl")
        goal_box.addWidget(goal_lbl)

        self._goal_combo = QComboBox()
        self._goal_combo.setObjectName("water_goal_combo")
        self._populate_goal_options()
        self._goal_combo.currentIndexChanged.connect(self._on_goal_changed)
        goal_box.addWidget(self._goal_combo)
        header.addLayout(goal_box)

        layout.addLayout(header)

        # 2. Prominent Metrics Row (Apple SF Pro Display style)
        metric_row = QHBoxLayout()
        metric_row.setSpacing(8)
        metric_row.setAlignment(Qt.AlignmentFlag.AlignBaseline)

        self._val_big = QLabel("0")
        self._val_big.setObjectName("water_val_big")
        metric_row.addWidget(self._val_big)

        self._val_sub = QLabel("ml / 3,000 ml")
        self._val_sub.setObjectName("water_val_sub")
        metric_row.addWidget(self._val_sub)

        metric_row.addStretch(1)

        self._pct_pill = QLabel("0%")
        self._pct_pill.setObjectName("water_pct_pill")
        metric_row.addWidget(self._pct_pill)

        layout.addLayout(metric_row)

        # 3. Liquid Capsule Progress Bar
        self._progress_bar = WaterCapsuleProgressBar(self)
        layout.addWidget(self._progress_bar)

        # Sub-status text (Remaining / Goal reached)
        self._status_lbl = QLabel("3,000 ml remaining today")
        self._status_lbl.setObjectName("water_status_lbl")
        layout.addWidget(self._status_lbl)

        # 4. Interactive Action Checkpoints Row
        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)

        self._btn_250 = QPushButton("+250 ml (Cup 🥛)")
        self._btn_250.setObjectName("water_btn_subtle")
        self._btn_250.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_250.clicked.connect(lambda: self._on_add(250))
        btns_row.addWidget(self._btn_250)

        self._btn_500 = QPushButton("+500 ml (Bottle 💧)")
        self._btn_500.setObjectName("water_btn_primary")
        self._btn_500.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_500.clicked.connect(lambda: self._on_add(500))
        btns_row.addWidget(self._btn_500)

        self._btn_1000 = QPushButton("+1.0L (Flask 🍶)")
        self._btn_1000.setObjectName("water_btn_accent")
        self._btn_1000.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_1000.clicked.connect(lambda: self._on_add(1000))
        btns_row.addWidget(self._btn_1000)

        self._btn_reset = QPushButton("↺")
        self._btn_reset.setObjectName("water_btn_reset")
        self._btn_reset.setToolTip("Reset Today's Water Log")
        self._btn_reset.setFixedSize(30, 30)
        self._btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_reset.clicked.connect(self._on_reset)
        btns_row.addWidget(self._btn_reset)

        layout.addLayout(btns_row)
        self._apply_style()

    def _populate_goal_options(self) -> None:
        self._goal_combo.clear()
        options = [
            ("2.0 L (2,000 ml)", 2000),
            ("2.5 L (2,500 ml)", 2500),
            ("3.0 L (3,000 ml)", 3000),
            ("3.5 L (3,500 ml)", 3500),
            ("4.0 L (4,000 ml)", 4000),
            ("5.0 L (5,000 ml)", 5000),
            ("Custom Goal…", -1),
        ]
        for label, val in options:
            self._goal_combo.addItem(label, val)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QFrame#water_card {
                background-color: #1C1C1E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QLabel#water_icon_badge {
                background: rgba(10, 132, 255, 0.12);
                border: 1px solid rgba(10, 132, 255, 0.25);
                border-radius: 10px;
                font-size: 16px;
            }
            QLabel#water_tag {
                font-size: 10px;
                font-weight: 700;
                color: #0A84FF;
                letter-spacing: 0.8px;
            }
            QLabel#water_title {
                font-size: 15px;
                font-weight: 700;
                color: #FFFFFF;
                letter-spacing: -0.2px;
            }
            QLabel#water_goal_lbl {
                font-size: 11px;
                font-weight: 600;
                color: #8E8E93;
            }
            QComboBox#water_goal_combo {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #FFFFFF;
            }
            QComboBox#water_goal_combo:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(10, 132, 255, 0.5);
            }
            QComboBox#water_goal_combo::drop-down {
                border: none;
                width: 16px;
            }
            QComboBox#water_goal_combo QAbstractItemView {
                background-color: #242426;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: #0A84FF;
                color: #FFFFFF;
                padding: 4px;
            }
            QLabel#water_val_big {
                font-size: 26px;
                font-weight: 800;
                color: #FFFFFF;
                letter-spacing: -0.5px;
            }
            QLabel#water_val_sub {
                font-size: 13px;
                font-weight: 600;
                color: #8E8E93;
                padding-bottom: 2px;
            }
            QLabel#water_pct_pill {
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #0A84FF;
            }
            QLabel#water_status_lbl {
                font-size: 11px;
                font-weight: 500;
                color: #8E8E93;
                padding-top: 1px;
            }
            QPushButton#water_btn_subtle {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 9px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 600;
                color: #E5E5EA;
            }
            QPushButton#water_btn_subtle:hover {
                background: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#water_btn_primary {
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 9px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #0A84FF;
            }
            QPushButton#water_btn_primary:hover {
                background: rgba(10, 132, 255, 0.25);
            }
            QPushButton#water_btn_accent {
                background: #0A84FF;
                border: none;
                border-radius: 9px;
                padding: 7px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton#water_btn_accent:hover {
                background: #0071E3;
            }
            QPushButton#water_btn_reset {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 9px;
                color: #8E8E93;
                font-size: 14px;
            }
            QPushButton#water_btn_reset:hover {
                color: #FF453A;
                border-color: rgba(255, 69, 58, 0.4);
                background: rgba(255, 69, 58, 0.1);
            }
        """)

    def _on_goal_changed(self, index: int) -> None:
        if self._block_goal_signal:
            return
        val = self._goal_combo.currentData()
        if val == -1:
            # Custom goal dialog
            curr_target = self._data.get("target_ml", 3000)
            custom_val, ok = QInputDialog.getInt(
                self,
                "Custom Water Goal",
                "Enter your daily target in milliliters (ml):",
                value=curr_target,
                minValue=500,
                maxValue=10000,
                step=250,
            )
            if ok and custom_val:
                self._data = self._repo.set_water_target(custom_val)
                self.refresh()
                self.water_updated.emit(self._data)
            else:
                self.refresh()
            return

        if val and val > 0:
            self._data = self._repo.set_water_target(val)
            self.refresh()
            self.water_updated.emit(self._data)

    def _on_add(self, ml: int) -> None:
        self._data = self._repo.add_water_intake(ml)
        self.refresh()
        self.water_updated.emit(self._data)

    def _on_reset(self) -> None:
        self._repo.reset_water_intake()
        self.refresh()
        self.water_updated.emit(self._data)

    def refresh(self) -> None:
        self._data = self._repo.get_water_intake()
        curr = self._data.get("current_ml", 0)
        target = self._data.get("target_ml", 3000)
        pct = min(100.0, (curr / target * 100.0) if target > 0 else 0.0)

        # Update big metric and subtexts
        self._val_big.setText(f"{curr:,}")
        self._val_sub.setText(f"ml / {target:,} ml ({(target / 1000.0):.1f} L)")
        self._pct_pill.setText(f"{int(pct)}%")

        if pct >= 100.0:
            self._pct_pill.setStyleSheet("""
                background: rgba(48, 209, 88, 0.18);
                border: 1px solid rgba(48, 209, 88, 0.45);
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #30D158;
            """)
            self._status_lbl.setText("🎉 Daily Hydration Goal Accomplished!")
            self._status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #30D158;")
        else:
            self._pct_pill.setStyleSheet("""
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 10px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
                color: #0A84FF;
            """)
            rem = max(0, target - curr)
            self._status_lbl.setText(f"{rem:,} ml remaining to hit your daily goal")
            self._status_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: #8E8E93;")

        # Animate progress capsule
        self._progress_bar.animate_to(curr / target if target > 0 else 0.0)

        # Sync goal dropdown selection
        self._block_goal_signal = True
        matched_idx = -1
        for i in range(self._goal_combo.count()):
            if self._goal_combo.itemData(i) == target:
                matched_idx = i
                break
        if matched_idx >= 0:
            self._goal_combo.setCurrentIndex(matched_idx)
        else:
            # Custom entry
            custom_lbl = f"Custom ({target:,} ml)"
            # check if last item is custom or already inserted
            if self._goal_combo.count() > 0 and self._goal_combo.itemData(self._goal_combo.count() - 1) == target:
                self._goal_combo.setCurrentIndex(self._goal_combo.count() - 1)
            else:
                self._goal_combo.insertItem(self._goal_combo.count() - 1, custom_lbl, target)
                self._goal_combo.setCurrentIndex(self._goal_combo.count() - 2)
        self._block_goal_signal = False
