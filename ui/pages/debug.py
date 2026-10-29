from __future__ import annotations

from datetime import date
from typing import Any, Optional

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QFrame, QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.constants import AppCategory
from analytics.engine import AnalyticsEngine
from database.repository import Repository
from tracker.categorizer import display_name as get_display_name


class DebugPage(QWidget):
    """Session Logs page — displays raw application session records and system diagnostic tools."""

    def __init__(self, tracker: Optional[Any] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._repo = Repository()
        self._setup_ui()
        self._refresh()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(60_000)
        self._refresh_timer.timeout.connect(self._refresh)
        self._refresh_timer.start()

        self._live_timer = QTimer(self)
        self._live_timer.setInterval(1000)
        self._live_timer.timeout.connect(self._update_live_inspector)
        self._live_timer.start()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # ── Page header ──────────────────────────────────────────────────────
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("Session Logs")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "Inspect raw application session records, run live system diagnostics, and export tracking data."
        )
        subtitle.setObjectName("page_subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self._export_btn = QPushButton("Export to CSV")
        self._export_btn.setObjectName("secondary_btn")
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self._export_csv)
        header.addWidget(self._export_btn)

        layout.addLayout(header)

        # ── System Diagnostics card ──────────────────────────────────────────
        self._setup_live_inspector(layout)

        # ── Filter bar ───────────────────────────────────────────────────────
        filters_frame = QFrame()
        filters_frame.setObjectName("v2_card")
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(16, 12, 16, 12)
        filters_layout.setSpacing(12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter by process name or window title")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(220)
        self._search.textChanged.connect(self._on_filter_changed)

        self._category_combo = QComboBox()
        self._category_combo.addItem("All Categories", None)
        for cat in AppCategory:
            self._category_combo.addItem(cat.value, cat)
        self._category_combo.currentIndexChanged.connect(self._on_filter_changed)

        today = date.today()
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDate(QDate(today.year, today.month, 1))
        self._start_date.dateChanged.connect(self._on_filter_changed)

        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDate(QDate(today.year, today.month, today.day))
        self._end_date.dateChanged.connect(self._on_filter_changed)

        filters_layout.addWidget(self._search, 2)
        filters_layout.addWidget(QLabel("Category"))
        filters_layout.addWidget(self._category_combo)
        filters_layout.addWidget(QLabel("Start"))
        filters_layout.addWidget(self._start_date)
        filters_layout.addWidget(QLabel("End"))
        filters_layout.addWidget(self._end_date)

        self._reset_btn = QPushButton("Reset Filters")
        self._reset_btn.setObjectName("secondary_btn")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._reset_filters)
        filters_layout.addWidget(self._reset_btn)

        layout.addWidget(filters_frame)

        # ── Result summary labels ─────────────────────────────────────────────
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summary_lbl")
        layout.addWidget(self._summary_label)

        self._result_label = QLabel("")
        self._result_label.setObjectName("result_lbl")
        layout.addWidget(self._result_label)

        # ── Session log table ─────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Application", "Category", "Window Title", "Start Time", "End Time", "Duration",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(34)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table, 1)

    def _setup_live_inspector(self, parent_layout: QVBoxLayout) -> None:
        live_frame = QFrame()
        live_frame.setObjectName("v2_card")
        live_layout = QVBoxLayout(live_frame)
        live_layout.setContentsMargins(18, 16, 18, 16)
        live_layout.setSpacing(14)

        # Section header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        live_title = QLabel("System Diagnostics")
        live_title.setObjectName("live_title")

        # Live pulse indicator badge
        self._live_dot = QLabel("LIVE")
        self._live_dot.setObjectName("live_dot")

        live_hint = QLabel("Refreshes every second")
        live_hint.setObjectName("live_hint")

        self._lbl_debug_status = QLabel("")
        self._lbl_debug_status.setObjectName("debug_status")

        header_layout.addWidget(live_title)
        header_layout.addWidget(self._live_dot)
        header_layout.addWidget(live_hint)
        header_layout.addStretch()
        header_layout.addWidget(self._lbl_debug_status)
        live_layout.addLayout(header_layout)

        # Diagnostic data grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)

        def make_row(row: int, label_text: str) -> QLabel:
            lbl = QLabel(label_text)
            lbl.setObjectName("live_key")
            lbl.setMinimumWidth(140)
            val = QLabel("\u2014")
            val.setObjectName("live_val")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        def make_row_col2(row: int, label_text: str) -> QLabel:
            lbl = QLabel(label_text)
            lbl.setObjectName("live_key")
            lbl.setMinimumWidth(140)
            val = QLabel("\u2014")
            val.setObjectName("live_val")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 2)
            grid.addWidget(val, row, 3)
            return val

        self._lbl_process = make_row(0, "Foreground process")
        self._lbl_exe = make_row(1, "Executable path")
        self._lbl_title = make_row(2, "Window title")
        self._lbl_category = make_row(3, "Detected category")
        self._lbl_timer = make_row(4, "Session elapsed")

        self._lbl_idle = make_row_col2(0, "Idle state")
        self._lbl_fullscreen = make_row_col2(1, "Display mode")
        self._lbl_game_reason = make_row_col2(2, "Game detection")
        self._lbl_launcher_reason = make_row_col2(3, "Launcher detection")
        self._lbl_engine = make_row_col2(4, "Tracking engine")
        self._lbl_media = make_row_col2(5, "SleepGuard media check")

        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(3, 2)
        grid.setRowStretch(6, 1)

        live_layout.addLayout(grid)
        parent_layout.addWidget(live_frame)

    def _apply_theme(self, is_dark: bool) -> None:
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
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#result_lbl {{
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 600;
            }}
            QLabel#summary_lbl {{
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#live_title {{
                font-weight: 700;
                font-size: 14px;
                color: {tm.color('text_main')};
            }}
            QLabel#live_dot {{
                background-color: #1a7f3c;
                color: #ffffff;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.6px;
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QLabel#live_hint {{
                color: {tm.color('text_muted')};
                font-size: 11px;
            }}
            QLabel#live_key {{
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 600;
                min-width: 140px;
            }}
            QLabel#live_val {{
                color: {tm.color('text_main')};
                font-size: 11px;
                font-weight: 500;
                font-family: Consolas, monospace;
            }}
            QPushButton#secondary_btn {{
                background-color: {tm.color('surface')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#secondary_btn:hover {{
                background-color: {tm.color('surface_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QFrame#v2_card {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLineEdit, QComboBox, QDateEdit {{
                background: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 9px;
                color: {tm.color('text_main')};
                padding: 6px 9px;
                font-size: 11px;
            }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{
                border-color: {tm.color('accent')};
            }}
            QTableWidget {{
                background: {tm.color('surface')};
                alternate-background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                color: {tm.color('text_main')};
                gridline-color: {tm.color('border')};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background: {tm.color('surface_secondary')};
                color: {tm.color('text_muted')};
                border: none;
                border-bottom: 1px solid {tm.color('border')};
                padding: 10px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QTableWidget::item {{ padding: 6px; }}
            QTableWidget::item:selected {{
                background: {tm.color('accent_tint_bg')};
                color: {tm.color('text_main')};
            }}
        """)

        # Trigger update for dynamic status styles
        self._update_live_inspector()

    def _update_live_inspector(self) -> None:
        if self._tracker is None or not hasattr(self._tracker, "get_debug_state"):
            self._lbl_debug_status.setText("Tracker disconnected")
            return

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        state = self._tracker.get_debug_state()
        debug_on = state.get("debug_enabled", False)
        self._lbl_debug_status.setText(
            "Diagnostics active" if debug_on else "Diagnostics inactive"
        )
        self._lbl_debug_status.setStyleSheet(
            f"font-size: 12px; font-weight: 700; color: {tm.color('success_text')};"
            if debug_on
            else f"font-size: 12px; font-weight: 700; color: {tm.color('text_muted')};"
        )

        self._lbl_process.setText(state.get("process_name", "None") or "None")
        self._lbl_exe.setText(state.get("exe_path", "\u2014") or "\u2014")
        self._lbl_title.setText(state.get("window_title", "\u2014") or "\u2014")
        self._lbl_category.setText(state.get("category", "None") or "None")

        try:
            from tracker.media_awareness import detect_foreground_media, describe_state
            self._lbl_media.setText(describe_state(detect_foreground_media(force=True)))
        except Exception:
            self._lbl_media.setText("Unavailable")

        duration = state.get("session_timer_s", 0.0)
        mins = int(duration) // 60
        secs = int(duration) % 60
        self._lbl_timer.setText(f"{mins:02d}:{secs:02d}  \u00b7  {duration:.1f}s")

        self._lbl_idle.setText("Idle" if state.get("is_idle") else "Active")
        self._lbl_fullscreen.setText(
            "Fullscreen" if state.get("is_fullscreen") else "Windowed"
        )
        self._lbl_game_reason.setText(state.get("game_reason", "\u2014") or "\u2014")
        self._lbl_launcher_reason.setText(state.get("launcher_reason", "\u2014") or "\u2014")

        try:
            stats = self._tracker.get_performance_stats()
            mode = "Event-driven" if stats.get("event_driven") else "Polling"
            self._lbl_engine.setText(
                f"{mode} \u00b7 {stats.get('foreground_queries', 0)} fg reads / "
                f"{stats.get('ticks', 0)} ticks \u00b7 {stats.get('wakeups_from_events', 0)} event wakes"
            )
        except Exception:
            self._lbl_engine.setText("\u2014")

    def _on_filter_changed(self) -> None:
        QTimer.singleShot(300, self._refresh)

    def _get_filter_values(self) -> tuple:
        query = self._search.text().strip()
        category = self._category_combo.currentData()
        qsd = self._start_date.date()
        qed = self._end_date.date()
        start = date(qsd.year(), qsd.month(), qsd.day())
        end = date(qed.year(), qed.month(), qed.day())
        return query, category, start, end

    def _reset_filters(self) -> None:
        today = date.today()
        self._search.clear()
        self._category_combo.setCurrentIndex(0)
        self._start_date.setDate(QDate(today.year, today.month, 1))
        self._end_date.setDate(QDate(today.year, today.month, today.day))
        self._refresh()

    def _refresh(self) -> None:
        query, category, start, end = self._get_filter_values()
        sessions = self._repo.search_sessions(query, category, start, end, limit=500)

        total_s = sum(float(s.duration_s or 0) for s in sessions)
        unique_apps = len({s.process_name for s in sessions})
        self._summary_label.setText(
            f"{len(sessions)} records  \u00b7  {unique_apps} applications  \u00b7  "
            f"{AnalyticsEngine.format_duration_short(total_s)} tracked  \u00b7  "
            f"{start.strftime('%b %d')} \u2013 {end.strftime('%b %d')}"
        )
        self._result_label.setText(
            "Showing the 500 most recent matching records"
            if len(sessions) >= 500
            else f"{len(sessions)} matching record{'s' if len(sessions) != 1 else ''}"
        )

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._table.setRowCount(len(sessions))

        from core.constants import CATEGORY_COLORS
        for row_idx, session in enumerate(sessions):
            name = get_display_name(session.process_name)
            cat_color = CATEGORY_COLORS.get(session.category, "#8E8E93")

            items = [
                QTableWidgetItem(name),
                QTableWidgetItem(session.category.value),
                QTableWidgetItem(session.window_title[:80]),
                QTableWidgetItem(session.start_time.strftime("%Y-%m-%d %H:%M:%S")),
                QTableWidgetItem(
                    session.end_time.strftime("%H:%M:%S") if session.end_time else "\u2014"
                ),
                QTableWidgetItem(session.duration_formatted),
            ]
            items[1].setBackground(
                __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(cat_color + "25")
            )

            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table.setItem(row_idx, col, item)

        self._table.setSortingEnabled(True)

    def _export_csv(self) -> None:
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from utils.csv_exporter import CSVExporter

        _, _, start, end = self._get_filter_values()

        default_path = str(
            Path.home() / "Documents" / f"digital_wellbeing_raw_sessions_{start}_{end}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Raw CSV", default_path, "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            exporter = CSVExporter()
            out = exporter.export_sessions(start, end, Path(path))
            QMessageBox.information(self, "Export Complete", f"Exported to:\n{out}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def on_data_changed(self) -> None:
        self._refresh()
