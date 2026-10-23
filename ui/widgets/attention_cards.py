"""
attention_cards.py — Apple-style attention-quality cards.

Two cards live here:
  * FocusFragmentationCard — 24 hourly bars of task switches.
  * FlowContinuityCard — sustained >=45-minute productive runs.

Both are pure presentation widgets; AnalyticsEngine supplies the data.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from tracker.categorizer import display_name as friendly_name
from ui.theme import ThemeManager


class FragmentationBars(QWidget):
    """Compact 24-hour switch-frequency bars (QPainter, no pyqtgraph)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(68)
        self._hourly: List[dict] = []
        self._peak_hour = ""

    def set_data(self, hourly: List[dict], peak_hour: str = "") -> None:
        self._hourly = list(hourly or [])
        self._peak_hour = peak_hour
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tm = ThemeManager.instance()

        width = max(1, self.width())
        height = max(1, self.height())
        count = 24
        gap = 3.0
        bar_w = max(1.0, (width - gap * (count - 1)) / count)
        max_switches = max([int(b.get("switches", 0)) for b in self._hourly] or [0])

        base_color = QColor(tm.color("accent"))
        peak_color = QColor("#FF9F0A")
        empty_color = QColor(tm.color("border"))

        for index in range(count):
            row = self._hourly[index] if index < len(self._hourly) else {}
            switches = int(row.get("switches", 0))
            x = index * (bar_w + gap)
            if max_switches <= 0:
                bar_h = 3.0
                color = empty_color
            else:
                bar_h = max(3.0, (switches / max_switches) * (height - 8.0))
                color = peak_color if row.get("hour") == self._peak_hour and switches > 0 else base_color
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(
                int(x),
                int(height - bar_h),
                max(1, int(bar_w)),
                int(bar_h),
                2,
                2,
            )

        # Baseline
        painter.setPen(QPen(QColor(tm.color("border")), 1))
        painter.drawLine(0, height - 1, width, height - 1)
        painter.end()


class FocusFragmentationCard(QFrame):
    """Shows switches/hour and the hourly distribution."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("attention_card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 17, 20, 16)
        layout.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel("FOCUS FRAGMENTATION")
        title.setObjectName("attention_eyebrow")
        header.addWidget(title)
        header.addStretch()
        self._badge = QLabel("Today")
        self._badge.setObjectName("attention_badge")
        header.addWidget(self._badge)
        layout.addLayout(header)

        self._value = QLabel("—")
        self._value.setObjectName("attention_value")
        layout.addWidget(self._value)

        self._sub = QLabel("Task switches per active hour")
        self._sub.setObjectName("attention_sub")
        layout.addWidget(self._sub)

        self._chart = FragmentationBars()
        layout.addWidget(self._chart)

        self._legend = QLabel("")
        self._legend.setObjectName("attention_legend")
        layout.addWidget(self._legend)

    def update_data(self, data: dict) -> None:
        hourly = data.get("hourly", [])
        index = float(data.get("fragmentation_index", 0.0))
        switches = int(data.get("total_switches", 0))
        peak_hour = data.get("peak_hour", "")
        peak_switches = int(data.get("peak_switches", 0))

        if switches == 0:
            self._value.setText("No switches yet")
            self._sub.setText("Task switches per active hour")
            self._legend.setText("Start using apps to build your attention profile.")
        else:
            self._value.setText(f"{index:.1f} switches / hr")
            self._sub.setText(f"{switches} switches across {data.get('active_hours', 0):.1f} active hours")
            self._legend.setText(f"Peak {peak_hour} · {peak_switches} switches")
        self._chart.set_data(hourly, peak_hour)


class FlowContinuityCard(QFrame):
    """Shows the longest sustained productive block and recent flow runs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("attention_card")
        self._rows_container = QVBoxLayout()
        self._rows_container.setSpacing(7)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 17, 20, 16)
        layout.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel("FLOW CONTINUITY")
        title.setObjectName("attention_eyebrow")
        header.addWidget(title)
        header.addStretch()
        self._badge = QLabel("7 days")
        self._badge.setObjectName("attention_badge")
        header.addWidget(self._badge)
        layout.addLayout(header)

        self._value = QLabel("—")
        self._value.setObjectName("attention_value")
        layout.addWidget(self._value)

        self._sub = QLabel("Longest uninterrupted productive run")
        self._sub.setObjectName("attention_sub")
        layout.addWidget(self._sub)
        layout.addLayout(self._rows_container)

    def _clear_rows(self) -> None:
        while self._rows_container.count():
            item = self._rows_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _format_range(start: datetime, end: datetime) -> str:
        if start.date() == end.date():
            return f"{start.strftime('%a')} {start.strftime('%H:%M')}–{end.strftime('%H:%M')}"
        return f"{start.strftime('%b %d %H:%M')}–{end.strftime('%b %d %H:%M')}"

    def update_data(self, data: dict) -> None:
        self._clear_rows()
        longest = data.get("longest")
        if not longest:
            self._value.setText("No 45+ min flow yet")
            self._sub.setText("Sustained productive runs appear here")
            hint = QLabel("Programming, writing, and study sessions are merged across 2-minute gaps.")
            hint.setObjectName("attention_empty")
            hint.setWordWrap(True)
            self._rows_container.addWidget(hint)
            return

        minutes = int(longest["duration_s"] // 60)
        hours, mins = divmod(minutes, 60)
        duration_text = f"{hours}h {mins:02d}m" if hours else f"{mins} min"
        self._value.setText(duration_text)
        self._sub.setText(f"Longest flow · {friendly_name(longest['primary_app'])}")

        recent = data.get("blocks", [])[:3]
        for block in recent:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)

            dot = QLabel("●")
            dot.setObjectName("flow_dot")
            row_layout.addWidget(dot)

            label = QLabel(friendly_name(block["primary_app"]))
            label.setObjectName("flow_app")
            row_layout.addWidget(label, 1)

            when = QLabel(self._format_range(block["start"], block["end"]))
            when.setObjectName("flow_time")
            row_layout.addWidget(when)
            self._rows_container.addWidget(row)
