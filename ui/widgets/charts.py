"""
charts.py — Aurora Apple-style chart widgets for Digital Wellbeing v4.0.

Custom rounded-top bar renderer (QPainterPath) on pyqtgraph plot infrastructure:
  • Apple-blue gradient bars with rounded caps and hover states
  • Spring-out entrance animation on data updates
  • Inter typography ticks, hairline axes, subtle y-grid
  • Strict yMin=0 limits (no negative-axis glitches)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient, QPen, QBrush
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget, QToolTip


def _tick_font() -> QFont:
    f = QFont("Inter", 9)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return f


class AppleBarGraphItem(pg.GraphicsObject):
    """Rounded-top gradient bars with entrance animation (Apple Charts style)."""

    def __init__(self) -> None:
        super().__init__()
        self._xs: List[float] = []
        self._heights: List[float] = []
        self._colors: List[QColor] = []
        self._bar_width = 0.62
        self._progress = 1.0

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(560)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, val) -> None:
        self._progress = float(val)
        self._invalidate()

    def set_data(self, xs: List[float], heights: List[float], width: float,
                 colors: List[QColor], animate: bool = True) -> None:
        self.prepareGeometryChange()
        self._xs = list(xs)
        self._heights = list(heights)
        self._bar_width = width
        self._colors = list(colors)
        if animate and any(h > 0 for h in heights):
            self._anim.stop()
            self._anim.start()
        else:
            self._progress = 1.0
            self._invalidate()

    def _invalidate(self) -> None:
        self.update()
        self.informViewBoundsChanged()

    def dataBounds(self, axis, frac=1.0, orthoRange=None):
        # pyqtgraph compatibility: report exact bounds
        if axis == 0:
            if not self._xs:
                return None
            w = self._bar_width / 2.0
            return (min(self._xs) - w, max(self._xs) + w)
        if not self._heights:
            return (0, 1)
        return (0, max(self._heights) or 1)

    def boundingRect(self) -> QRectF:
        if not self._xs:
            return QRectF(0, 0, 1, 1)
        w = self._bar_width / 2.0
        max_h = max(self._heights) if self._heights else 1.0
        return QRectF(min(self._xs) - w, 0, max(self._xs) - min(self._xs) + self._bar_width, max_h)

    def paint(self, painter: QPainter, *_args) -> None:
        if not self._xs:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = min(self._bar_width / 2.0, 4.0)

        for x, h, color in zip(self._xs, self._heights, self._colors):
            hh = h * self._progress
            if hh <= 0.001:
                continue
            x0 = x - self._bar_width / 2.0
            x1 = x + self._bar_width / 2.0

            grad = QLinearGradient(x0, 0, x0, hh)
            top = QColor(color)
            bottom = QColor(color)
            bottom.setAlpha(int(color.alpha() * 0.45))
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, bottom)

            path = QPainterPath()
            radius = min(r, hh)
            path.moveTo(x0, 0)
            path.lineTo(x0, hh - radius)
            path.quadTo(x0, hh, x0 + radius, hh)
            path.lineTo(x1 - radius, hh)
            path.quadTo(x1, hh, x1, hh - radius)
            path.lineTo(x1, 0)
            path.closeSubpath()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawPath(path)


class _BaseAppleBarChart(QFrame):
    """Shared plumbing for Apple-style bar charts (axes, grid, ticks, empty state)."""

    def _setup_plot(self) -> None:
        self._plot = pg.PlotWidget()
        self._plot.setMinimumHeight(230)
        self._plot.setBackground(None)
        self._plot.getPlotItem().layout.setContentsMargins(12, 16, 16, 16)

        self._plot.showGrid(x=False, y=True, alpha=0.14)
        self._plot.getPlotItem().setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)

        self._bar_item = AppleBarGraphItem()
        self._plot.addItem(self._bar_item)

        self._empty_lbl = QLabel("No usage recorded yet", self._plot)
        self._empty_lbl.setObjectName("chart_empty_lbl")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setVisible(False)

        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

    # Subclass API ---------------------------------------------------------
    def _on_mouse_moved(self, pos) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def _chart_rows(self) -> List[dict]:
        return getattr(self, "_hourly_rows", [])

    def _chart_heights(self) -> List[float]:
        return getattr(self._bar_item, "_heights", [])

    # Theme ------------------------------------------------------------------
    def _style_axes(self) -> None:
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()

        self.setStyleSheet(f"""
            QLabel#section_header {{ {ds.type_css('headline', tm.color('text_main'))} }}
            QLabel#page_subtitle {{ font-size: 12px; font-weight: 400; color: {tm.color('text_sub')}; }}
            QLabel#chart_empty_lbl {{ font-size: 13px; font-weight: 500; color: {tm.color('text_muted')}; background: transparent; }}
        """)

        axis_pen = pg.mkPen(color=QColor(128, 128, 128, 40), width=1)
        text_pen = pg.mkPen(color=QColor(tm.color('text_sub')))
        tick_font = _tick_font()

        for axis_name in ("left", "bottom"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setStyle(tickFont=tick_font)

        self._plot.getPlotItem().setLabel("left", "Minutes", color=tm.color('text_sub'), size="10pt")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_empty_lbl") and hasattr(self, "_plot"):
            self._empty_lbl.setGeometry(0, 0, self._plot.width(), self._plot.height())

    def _update_empty_state(self, max_val: float) -> None:
        if max_val <= 0.0:
            self._empty_lbl.setVisible(True)
            self._empty_lbl.setGeometry(0, 0, self._plot.width(), self._plot.height())
        else:
            self._empty_lbl.setVisible(False)


class HourlyIntensityChart(_BaseAppleBarChart):
    """24-Hour Screen Time Intensity Chart for Today View (Segment 0)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dense_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(320)
        self._hourly_rows: List[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self._title_lbl = QLabel("Hourly Screen Time")
        self._title_lbl.setObjectName("section_header")

        self._subtitle_lbl = QLabel("Active minutes per hour across the 24-hour day")
        self._subtitle_lbl.setObjectName("page_subtitle")

        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._subtitle_lbl)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self._setup_plot()

        ticks = [(i, f"{i:02d}:00") for i in range(0, 24, 3)]
        self._plot.getPlotItem().getAxis("bottom").setTicks([ticks, []])

        self._plot.getViewBox().setLimits(yMin=0, xMin=-1, xMax=24)
        self._plot.setXRange(-0.8, 23.8, padding=0)
        self._plot.setYRange(0, 10, padding=0)

        layout.addWidget(self._plot)

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        self._style_axes()
        self._refresh_bar_colors(animate=False)

    def _refresh_bar_colors(self, animate: bool = False) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        accent = QColor(tm.color('accent'))
        n = len(self._bar_item._heights) or 24
        colors = [QColor(accent) for _ in range(max(n, 24))]
        xs = list(range(max(n, 24)))
        heights = list(self._bar_item._heights) or [0.0] * 24
        self._bar_item.set_data(xs, heights, 0.62, colors[:len(xs)], animate=animate)

    def _on_mouse_moved(self, pos) -> None:
        if not self._hourly_rows or not self._bar_item._heights:
            return

        mouse_point = self._plot.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        idx = int(round(x))

        heights = self._bar_item._heights
        if 0 <= idx < len(self._hourly_rows) and abs(x - idx) <= 0.4:
            h = heights[idx] if idx < len(heights) else 0.0
            if 0 <= mouse_point.y() <= max(h, 0.5) and h > 0:
                hour_str = self._hourly_rows[idx].get("hour", f"{idx:02d}:00")
                total_s = float(self._hourly_rows[idx].get("total_s", 0.0))
                mins = int(total_s // 60)
                secs = int(total_s % 60)
                tooltip_text = f"<b>{hour_str}</b><br/>Active: {mins}m {secs}s"
                screen_pos = self._plot.mapToGlobal(self._plot.mapFromScene(pos))
                QToolTip.showText(screen_pos, tooltip_text, self._plot)
                return

        QToolTip.hideText()

    def update_data(self, hourly_rows: List[dict]) -> None:
        """Update chart with list of 24 dicts containing 'hour' and 'total_s'."""
        if not hourly_rows or len(hourly_rows) != 24:
            return

        self._hourly_rows = hourly_rows
        heights = [max(0.0, float(r.get("total_s", 0.0)) / 60.0) for r in hourly_rows]

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        accent = QColor(tm.color('accent'))
        self._bar_item.set_data(list(range(24)), heights, 0.62, [QColor(accent) for _ in range(24)], animate=True)

        max_val = max(heights) if heights else 0.0
        upper = max(10.0, max_val * 1.15)
        self._plot.setYRange(0, upper, padding=0)
        self._plot.getViewBox().setLimits(yMin=0, yMax=upper * 1.5)

        self._update_empty_state(max_val)


class DailyScreenTimeChart(_BaseAppleBarChart):
    """7/30-Day Screen Time Comparison Chart with click-to-select."""

    day_selected = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("dense_card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(320)
        self._day_strings: List[str] = []
        self._raw_heights: List[float] = []
        self._selected_idx: Optional[int] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self._title_lbl = QLabel("Daily Screen Time")
        self._title_lbl.setObjectName("section_header")

        self._subtitle_lbl = QLabel("Active screen time trend analysis")
        self._subtitle_lbl.setObjectName("page_subtitle")

        title_box.addWidget(self._title_lbl)
        title_box.addWidget(self._subtitle_lbl)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self._setup_plot()
        self._plot.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        self._plot.getViewBox().setLimits(yMin=0, xMin=-0.8, xMax=6.8)
        self._plot.setXRange(-0.6, 6.6, padding=0)
        self._plot.setYRange(0, 8.0, padding=0)

        layout.addWidget(self._plot)

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool) -> None:
        self._style_axes()
        self._restyle_bars(animate=False)

    def _restyle_bars(self, animate: bool = False) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        accent = QColor(tm.color('accent'))
        dim = QColor(accent)
        dim.setAlpha(int(255 * 0.45))

        heights = list(self._bar_item._heights)
        n = len(heights)
        if n == 0:
            return

        colors: List[QColor] = []
        for i in range(n):
            if self._selected_idx is not None and i != self._selected_idx:
                colors.append(QColor(dim))
            else:
                colors.append(QColor(accent))

        self._bar_item.set_data(list(range(n)), heights, 0.55 if n <= 7 else 0.4, colors, animate=animate)

    def set_range_title(self, range_name: str) -> None:
        """Dynamically update chart subtitle e.g. 'Past 7 days' or 'Past 30 days'."""
        self._title_lbl.setText(f"Daily Screen Time · {range_name}")

    def _on_mouse_moved(self, pos) -> None:
        if not self._day_strings or not self._bar_item._heights:
            return

        mouse_point = self._plot.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        idx = int(round(x))
        heights = self._bar_item._heights

        if 0 <= idx < len(self._day_strings) and abs(x - idx) <= 0.35:
            h = heights[idx] if idx < len(heights) else 0.0
            if 0 <= mouse_point.y() <= max(h, 0.5) and h > 0:
                day_str = self._day_strings[idx]
                total_s = self._raw_heights[idx]

                from analytics.engine import AnalyticsEngine
                engine = AnalyticsEngine()
                time_str = engine.format_duration(total_s)

                try:
                    dt = datetime.strptime(day_str, "%Y-%m-%d")
                    friendly_day = dt.strftime("%A, %b %d")
                except (ValueError, TypeError):
                    friendly_day = day_str

                from settings.manager import SettingsManager
                limit_s = SettingsManager().get_int("daily_limit_minutes", 480) * 60
                goal_status = "Over Goal" if total_s > limit_s else "Under Goal"

                tooltip_text = f"<b>{friendly_day}</b><br/>Active: {time_str}<br/>{goal_status}"
                screen_pos = self._plot.mapToGlobal(self._plot.mapFromScene(pos))
                QToolTip.showText(screen_pos, tooltip_text, self._plot)
                return

        QToolTip.hideText()

    def _on_mouse_clicked(self, event) -> None:
        if not self._day_strings:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            mouse_point = self._plot.getViewBox().mapSceneToView(pos)
            x = mouse_point.x()
            idx = int(round(x))

            if 0 <= idx < len(self._day_strings) and abs(x - idx) <= 0.35:
                self._selected_idx = idx
                self._restyle_bars(animate=False)
                self.day_selected.emit(self._day_strings[idx])

    def update_data(self, daily_points: List[Any]) -> None:
        """Update chart with list of DailyPoint objects (or dicts) having 'day' and 'active_s'."""
        if not daily_points:
            return

        heights: List[float] = []
        ticks: List[tuple] = []
        max_active_s = 0.0
        n_points = len(daily_points)
        self._selected_idx = None

        for idx, pt in enumerate(daily_points):
            active_s = getattr(pt, "active_s", None)
            if active_s is None and isinstance(pt, dict):
                active_s = float(pt.get("active_s", 0.0))
            active_s = max(0.0, float(active_s or 0.0))
            max_active_s = max(max_active_s, active_s)

            day_str = getattr(pt, "day", None)
            if day_str is None and isinstance(pt, dict):
                day_str = pt.get("day", "")

            formatted_date = str(day_str)
            try:
                dt = datetime.strptime(str(day_str), "%Y-%m-%d")
                formatted_date = dt.strftime("%b %d")
            except (ValueError, TypeError):
                pass

            if n_points > 14:
                if idx % 5 == 0 or idx == n_points - 1:
                    ticks.append((idx, formatted_date))
            else:
                ticks.append((idx, formatted_date))
            heights.append(active_s)

        self._day_strings = [str(getattr(pt, "day", pt.get("day", ""))) if isinstance(pt, dict) else str(getattr(pt, "day", "")) for pt in daily_points]
        self._raw_heights = heights

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        if max_active_s >= 3600.0:
            heights_scaled = [h / 3600.0 for h in heights]
            self._plot.getPlotItem().setLabel("left", "Hours", color=tm.color('text_sub'), size="10pt")
        else:
            heights_scaled = [h / 60.0 for h in heights]
            self._plot.getPlotItem().setLabel("left", "Minutes", color=tm.color('text_sub'), size="10pt")

        accent = QColor(tm.color('accent'))
        bar_width = 0.55 if n_points <= 7 else 0.4
        self._bar_item.set_data(
            list(range(len(heights_scaled))),
            heights_scaled,
            bar_width,
            [QColor(accent) for _ in heights_scaled],
            animate=True,
        )
        self._plot.getPlotItem().getAxis("bottom").setTicks([ticks, []])

        max_val = max(heights_scaled) if heights_scaled else 0.0
        upper = max(2.0, max_val * 1.15)
        self._plot.setYRange(0, upper, padding=0)
        self._plot.getViewBox().setLimits(yMin=0, xMin=-0.8, xMax=max(6.8, len(heights_scaled) - 0.2), yMax=upper * 1.5)

        self._update_empty_state(max_active_s)
