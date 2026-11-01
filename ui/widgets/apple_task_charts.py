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

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
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
    QFrame,
    QHBoxLayout,
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

class WaterIntakeWidget(QFrame):
    """Hydration tracker widget with 0.5L and 1.0L interactive checkpoints."""

    water_updated = Signal(dict)

    def __init__(self, repo: Repository, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("water_card")
        self._repo = repo
        self._data = {"target_ml": 3000, "current_ml": 0, "checkpoints": []}
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        icon_lbl = QLabel("💧")
        icon_lbl.setStyleSheet("font-size: 16px;")
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title = QLabel("Daily Hydration")
        title.setObjectName("water_title")
        self._sub_lbl = QLabel("Goal: 3,000 ml (3.0 L)")
        self._sub_lbl.setObjectName("water_sub")
        title_col.addWidget(title)
        title_col.addWidget(self._sub_lbl)
        header.addLayout(title_col, 1)

        self._val_lbl = QLabel("0 / 3,000 ml")
        self._val_lbl.setObjectName("water_val")
        header.addWidget(self._val_lbl)

        layout.addLayout(header)

        # Visual progress bar
        self._bar_container = QFrame()
        self._bar_container.setObjectName("water_bar_track")
        self._bar_container.setFixedHeight(12)
        bar_layout = QHBoxLayout(self._bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)

        self._bar_fill = QFrame()
        self._bar_fill.setObjectName("water_bar_fill")
        self._bar_fill.setFixedHeight(12)
        bar_layout.addWidget(self._bar_fill)
        bar_layout.addStretch()
        layout.addWidget(self._bar_container)

        # Action Checkpoint Buttons
        btns_row = QHBoxLayout()
        btns_row.setSpacing(8)

        self._btn_500 = QPushButton("+0.5L (500 ml)")
        self._btn_500.setObjectName("water_pill_btn")
        self._btn_500.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_500.clicked.connect(lambda: self._on_add(500))
        btns_row.addWidget(self._btn_500)

        self._btn_1000 = QPushButton("+1.0L (1,000 ml)")
        self._btn_1000.setObjectName("water_pill_btn_accent")
        self._btn_1000.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_1000.clicked.connect(lambda: self._on_add(1000))
        btns_row.addWidget(self._btn_1000)

        self._btn_reset = QPushButton("↺")
        self._btn_reset.setObjectName("water_reset_btn")
        self._btn_reset.setToolTip("Reset Today's Water Intake")
        self._btn_reset.setFixedSize(28, 28)
        self._btn_reset.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_reset.clicked.connect(self._on_reset)
        btns_row.addWidget(self._btn_reset)

        layout.addLayout(btns_row)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QFrame#water_card {
                background-color: #1C1C1E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QLabel#water_title {
                font-size: 13px;
                font-weight: 700;
                color: #FFFFFF;
                letter-spacing: -0.2px;
            }
            QLabel#water_sub {
                font-size: 10px;
                color: #8E8E93;
            }
            QLabel#water_val {
                font-size: 14px;
                font-weight: 700;
                color: #38BDF8;
            }
            QFrame#water_bar_track {
                background: rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QFrame#water_bar_fill {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007AFF, stop:1 #38BDF8);
                border-radius: 6px;
            }
            QPushButton#water_pill_btn {
                background: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                color: #38BDF8;
            }
            QPushButton#water_pill_btn:hover {
                background: rgba(56, 189, 248, 0.2);
            }
            QPushButton#water_pill_btn_accent {
                background: #0A84FF;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QPushButton#water_pill_btn_accent:hover {
                background: #0071E3;
            }
            QPushButton#water_reset_btn {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #8E8E93;
                font-size: 12px;
            }
            QPushButton#water_reset_btn:hover {
                color: #FF453A;
                border-color: rgba(255, 69, 58, 0.4);
            }
        """)

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

        self._val_lbl.setText(f"{curr:,} / {target:,} ml ({int(pct)}%)")
        
        # Adjust bar fill width based on percentage
        total_w = self._bar_container.width()
        fill_w = int((pct / 100.0) * max(1, total_w - 4))
        self._bar_fill.setFixedWidth(max(10 if curr > 0 else 0, fill_w))
