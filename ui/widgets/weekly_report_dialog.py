"""
weekly_report_dialog.py — Weekly attention report with heatmap + exports.

The report is derived entirely from local session history. CSV and PDF exports
are generated on demand; "Copy summary" puts a plain-text digest on the
clipboard for manual sharing.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPageSize, QPainter, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from analytics.engine import AnalyticsEngine
from tracker.categorizer import display_name as friendly_name
from ui.primitives import Card
from ui.theme import ThemeManager


def _duration(seconds: float) -> str:
    minutes = int(max(0, seconds) // 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


class AttentionHeatmap(QWidget):
    """7 days × 24 hours switch-intensity heatmap."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(210)
        self._days: List[dict] = []

    def set_data(self, days: List[dict]) -> None:
        self._days = days or []
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        tm = ThemeManager.instance()
        is_dark = tm.is_dark

        left = 42.0
        top = 20.0
        width = max(1.0, self.width() - left - 8.0)
        height = max(1.0, self.height() - top - 8.0)
        cols = 24
        rows = max(1, len(self._days))
        cell_w = width / cols
        cell_h = height / rows
        max_switches = max(
            [int(h.get("switches", 0)) for day in self._days for h in day.get("hours", [])] or [0]
        )

        base = QColor(tm.color("surface_secondary"))
        hot = QColor("#FF453A" if is_dark else "#FF3B30")
        warm = QColor("#FF9F0A")

        painter.setPen(QColor(tm.color("text_muted")))
        font = painter.font()
        font.setPointSizeF(8.5)
        painter.setFont(font)

        for hour in range(0, 24, 3):
            painter.drawText(
                QRectF(left + hour * cell_w, 0, cell_w * 3, top - 2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{hour:02d}",
            )

        for row, day in enumerate(self._days):
            y = top + row * cell_h
            painter.setPen(QColor(tm.color("text_muted")))
            painter.drawText(
                QRectF(0, y, left - 6, cell_h),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(day.get("label", "")),
            )
            for hour in range(24):
                cell = day.get("hours", [{}] * 24)[hour] if hour < len(day.get("hours", [])) else {}
                switches = int(cell.get("switches", 0))
                if max_switches <= 0:
                    color = base
                else:
                    ratio = min(1.0, switches / max_switches)
                    if ratio < 0.5:
                        color = QColor(
                            int(base.red() + (warm.red() - base.red()) * ratio * 2),
                            int(base.green() + (warm.green() - base.green()) * ratio * 2),
                            int(base.blue() + (warm.blue() - base.blue()) * ratio * 2),
                        )
                    else:
                        r2 = (ratio - 0.5) * 2
                        color = QColor(
                            int(warm.red() + (hot.red() - warm.red()) * r2),
                            int(warm.green() + (hot.green() - warm.green()) * r2),
                            int(warm.blue() + (hot.blue() - warm.blue()) * r2),
                        )
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawRoundedRect(
                    QRectF(left + hour * cell_w + 1, y + 1, max(1.0, cell_w - 2), max(1.0, cell_h - 2)),
                    3,
                    3,
                )

        painter.setPen(QColor(tm.color("text_muted")))
        painter.drawText(
            QRectF(left, top + height + 2, width, 14),
            Qt.AlignmentFlag.AlignRight,
            "switches per hour · low → high",
        )
        painter.end()


class _Stat(Card):
    def __init__(self, title: str, value: str, sub: str = "", parent=None) -> None:
        super().__init__("report_stat", padding=(14, 11, 14, 11), spacing=2, parent=parent)
        layout = self.body
        t = QLabel(title)
        t.setObjectName("report_stat_title")
        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("report_stat_value")
        self.sub_lbl = QLabel(sub)
        self.sub_lbl.setObjectName("report_stat_sub")
        layout.addWidget(t)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.sub_lbl)


class WeeklyReportDialog(QDialog):
    def __init__(self, engine: Optional[AnalyticsEngine] = None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine or AnalyticsEngine()
        self._report = self._engine.get_weekly_attention_report()
        self.setWindowTitle("Weekly attention report")
        self.setMinimumSize(900, 720)
        self.setModal(False)
        self._setup_ui()
        self._populate()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel("Weekly attention report")
        title.setObjectName("dialog_title")
        subtitle = QLabel("Where attention fragmented, where flow held, and the best hours to focus.")
        subtitle.setObjectName("dialog_subtitle")
        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text, 1)

        self._copy_btn = QPushButton("Copy summary")
        self._copy_btn.setObjectName("report_btn")
        self._copy_btn.clicked.connect(self._copy_summary)
        header.addWidget(self._copy_btn)
        self._csv_btn = QPushButton("Export CSV")
        self._csv_btn.setObjectName("report_btn")
        self._csv_btn.clicked.connect(self._export_csv)
        header.addWidget(self._csv_btn)
        self._pdf_btn = QPushButton("Export PDF")
        self._pdf_btn.setObjectName("primary_pill_btn")
        self._pdf_btn.clicked.connect(self._export_pdf)
        header.addWidget(self._pdf_btn)
        root.addLayout(header)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self._switches_stat = _Stat("TASK SWITCHES", "—")
        self._index_stat = _Stat("AVG FRAGMENTATION", "—")
        self._flow_stat = _Stat("FLOW TIME", "—")
        self._streak_stat = _Stat("FLOW STREAK", "—")
        stats.addWidget(self._switches_stat)
        stats.addWidget(self._index_stat)
        stats.addWidget(self._flow_stat)
        stats.addWidget(self._streak_stat)
        root.addLayout(stats)

        heat_card = QFrame()
        heat_card.setObjectName("report_card")
        heat_layout = QVBoxLayout(heat_card)
        heat_layout.setContentsMargins(16, 14, 16, 12)
        heat_layout.setSpacing(6)
        heat_title = QLabel("FRAGMENTATION HEATMAP · LAST 7 DAYS")
        heat_title.setObjectName("report_eyebrow")
        heat_layout.addWidget(heat_title)
        self._heatmap = AttentionHeatmap()
        heat_layout.addWidget(self._heatmap, 1)
        root.addWidget(heat_card, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        best_card = QFrame()
        best_card.setObjectName("report_card")
        best_layout = QVBoxLayout(best_card)
        best_layout.setContentsMargins(16, 13, 16, 13)
        best_layout.setSpacing(4)
        best_title = QLabel("BEST & WORST HOURS")
        best_title.setObjectName("report_eyebrow")
        best_layout.addWidget(best_title)
        self._best_lbl = QLabel("—")
        self._best_lbl.setObjectName("report_best")
        self._worst_lbl = QLabel("—")
        self._worst_lbl.setObjectName("report_worst")
        best_layout.addWidget(self._best_lbl)
        best_layout.addWidget(self._worst_lbl)
        best_layout.addStretch()
        bottom.addWidget(best_card, 1)

        flow_card = QFrame()
        flow_card.setObjectName("report_card")
        flow_layout = QVBoxLayout(flow_card)
        flow_layout.setContentsMargins(16, 13, 16, 13)
        flow_layout.setSpacing(4)
        flow_title = QLabel("FLOW CONTINUITY")
        flow_title.setObjectName("report_eyebrow")
        flow_layout.addWidget(flow_title)
        self._flow_detail = QLabel("—")
        self._flow_detail.setObjectName("report_flow_detail")
        self._flow_detail.setWordWrap(True)
        flow_layout.addWidget(self._flow_detail)
        flow_layout.addStretch()
        bottom.addWidget(flow_card, 1)
        root.addLayout(bottom)

        done_row = QHBoxLayout()
        done_row.addStretch()
        done = QPushButton("Done")
        done.setObjectName("report_btn")
        done.clicked.connect(self.accept)
        done_row.addWidget(done)
        root.addLayout(done_row)

    def _populate(self) -> None:
        report = self._report
        self._switches_stat.value_lbl.setText(str(report["total_switches"]))
        self._switches_stat.sub_lbl.setText(f"{_duration(report['total_active_s'])} active")
        self._index_stat.value_lbl.setText(f"{report['average_index']:.1f}/hr")
        self._index_stat.sub_lbl.setText("Switches per active hour")
        flow = report["flow"]
        self._flow_stat.value_lbl.setText(_duration(flow["total_flow_s"]))
        self._flow_stat.sub_lbl.setText(f"{flow['count']} flow blocks")
        self._streak_stat.value_lbl.setText(f"{flow['current_streak']} days")
        self._streak_stat.sub_lbl.setText(f"Best {flow['best_streak']} days")

        self._heatmap.set_data(report["days"])

        best = report.get("best_hour")
        worst = report.get("worst_hour")
        self._best_lbl.setText(
            f"Best: {best['hour']:02d}:00 · {best['index']:.1f}/hr" if best else "Best: not enough history"
        )
        self._worst_lbl.setText(
            f"Worst: {worst['hour']:02d}:00 · {worst['index']:.1f}/hr" if worst else "Worst: not enough history"
        )

        longest = flow.get("longest")
        if longest:
            self._flow_detail.setText(
                f"Longest: {_duration(longest['duration_s'])} in "
                f"{friendly_name(longest['primary_app'])}. "
                f"Current streak: {flow['current_streak']} day(s)."
            )
        else:
            self._flow_detail.setText("No 45+ minute flow block yet. Productive sessions appear here.")

    def _summary_text(self) -> str:
        r = self._report
        flow = r["flow"]
        best = r.get("best_hour")
        worst = r.get("worst_hour")
        lines = [
            "Digital Wellbeing — Weekly Attention Report",
            f"{r['start'].isoformat()} to {r['end'].isoformat()}",
            f"Task switches: {r['total_switches']}",
            f"Average fragmentation: {r['average_index']:.1f} switches/active hour",
            f"Flow time: {_duration(flow['total_flow_s'])} across {flow['count']} blocks",
            f"Flow streak: {flow['current_streak']} days (best {flow['best_streak']})",
        ]
        if best:
            lines.append(f"Best hour: {best['hour']:02d}:00 ({best['index']:.1f}/hr)")
        if worst:
            lines.append(f"Worst hour: {worst['hour']:02d}:00 ({worst['index']:.1f}/hr)")
        return "\n".join(lines)

    def _copy_summary(self) -> None:
        QApplication.clipboard().setText(self._summary_text())

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export weekly attention CSV",
            f"attention-report-{self._report['end'].isoformat()}.csv",
            "CSV files (*.csv)",
        )
        if not path:
            return
        import csv

        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "day", "hour", "switches", "active_seconds"])
            for day in self._report["days"]:
                for hour, cell in enumerate(day["hours"]):
                    writer.writerow(
                        [
                            day["date"].isoformat(),
                            day["label"],
                            f"{hour:02d}:00",
                            cell["switches"],
                            round(cell["active_s"], 1),
                        ]
                    )

    def _export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export weekly attention PDF",
            f"attention-report-{self._report['end'].isoformat()}.pdf",
            "PDF files (*.pdf)",
        )
        if not path:
            return
        r = self._report
        flow = r["flow"]
        best = r.get("best_hour")
        worst = r.get("worst_hour")
        rows = "".join(
            f"<tr><td>{day['date'].isoformat()}</td><td>{day['label']}</td>"
            f"<td>{day['switches']}</td><td>{day['index']:.1f}</td></tr>"
            for day in r["days"]
        )
        html = f"""
        <html><head><style>
        body {{ font-family: Segoe UI, Arial, sans-serif; color: #1d1d1f; }}
        h1 {{ font-size: 24px; margin-bottom: 2px; }}
        h2 {{ font-size: 14px; color: #6e6e73; margin-top: 18px; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
        th, td {{ border-bottom: 1px solid #ddd; padding: 6px; text-align: left; font-size: 11px; }}
        .muted {{ color: #6e6e73; }}
        </style></head><body>
        <h1>Digital Wellbeing — Weekly Attention Report</h1>
        <div class="muted">{r['start'].isoformat()} to {r['end'].isoformat()}</div>
        <h2>Summary</h2>
        <p>Task switches: <b>{r['total_switches']}</b><br/>
        Average fragmentation: <b>{r['average_index']:.1f} switches/active hour</b><br/>
        Flow time: <b>{_duration(flow['total_flow_s'])}</b> across {flow['count']} blocks<br/>
        Flow streak: <b>{flow['current_streak']} days</b> (best {flow['best_streak']})</p>
        <h2>Best & worst hours</h2>
        <p>Best: {f"{best['hour']:02d}:00 — {best['index']:.1f}/hr" if best else 'Not enough history'}<br/>
        Worst: {f"{worst['hour']:02d}:00 — {worst['index']:.1f}/hr" if worst else 'Not enough history'}</p>
        <h2>Daily breakdown</h2>
        <table><tr><th>Date</th><th>Day</th><th>Switches</th><th>Index</th></tr>{rows}</table>
        </body></html>
        """
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(96)
        painter = QPainter(writer)
        doc = QTextDocument()
        doc.setHtml(html)
        doc.setTextWidth(writer.width())
        doc.drawContents(painter, QRectF(0, 0, writer.width(), writer.height()))
        painter.end()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 24px; font-weight: 700; }}
            QLabel#dialog_subtitle {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QFrame#report_card {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 14px; }}
            QFrame#report_stat {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; }}
            QLabel#report_stat_title, QLabel#report_eyebrow {{ color: {tm.color('text_muted')}; font-size: 9px; font-weight: 700; letter-spacing: 1.1px; }}
            QLabel#report_stat_value {{ color: {tm.color('text_main')}; font-size: 19px; font-weight: 700; }}
            QLabel#report_stat_sub {{ color: {tm.color('text_sub')}; font-size: 10px; }}
            QLabel#report_best {{ color: #30D158; font-size: 11px; font-weight: 600; }}
            QLabel#report_worst {{ color: #FF9F0A; font-size: 11px; font-weight: 600; }}
            QLabel#report_flow_detail {{ color: {tm.color('text_sub')}; font-size: 11px; }}
            QPushButton#report_btn {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; color: {tm.color('text_sub')}; padding: 8px 14px; font-size: 11px; font-weight: 600; }}
            QPushButton#report_btn:hover {{ color: {tm.color('text_main')}; border-color: {tm.color('accent')}; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 999px; padding: 8px 16px; font-size: 11px; font-weight: 700; }}
            QPushButton#primary_pill_btn:hover {{ background: {tm.color('accent_hover')}; }}
        """)
