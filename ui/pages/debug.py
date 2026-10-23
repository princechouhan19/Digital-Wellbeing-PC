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
from database.repository import Repository
from tracker.categorizer import display_name as get_display_name


class DebugPage(QWidget):
    """Developer & Debug page displaying raw app session logs and diagnostic tools."""

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

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Developer & Debug Logs")
        title.setObjectName("page_title")
        subtitle = QLabel("Raw session activity records and system log inspection")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self._export_btn = QPushButton("Export Raw CSV")
        self._export_btn.setObjectName("secondary_btn")
        self._export_btn.clicked.connect(self._export_csv)
        header.addWidget(self._export_btn)

        layout.addLayout(header)
        self._setup_live_inspector(layout)

        filters_frame = QFrame()
        filters_frame.setObjectName("v2_card")
        filters_layout = QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(16, 12, 16, 12)
        filters_layout.setSpacing(12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search process or window title...")
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
        filters_layout.addWidget(QLabel("Category:"))
        filters_layout.addWidget(self._category_combo)
        filters_layout.addWidget(QLabel("From:"))
        filters_layout.addWidget(self._start_date)
        filters_layout.addWidget(QLabel("To:"))
        filters_layout.addWidget(self._end_date)

        layout.addWidget(filters_frame)

        self._result_label = QLabel("")
        self._result_label.setObjectName("result_lbl")
        layout.addWidget(self._result_label)

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
        self._table.setAlternatingRowColors(False)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table, 1)

    def _setup_live_inspector(self, parent_layout: QVBoxLayout) -> None:
        live_frame = QFrame()
        live_frame.setObjectName("v2_card")
        live_layout = QVBoxLayout(live_frame)
        live_layout.setContentsMargins(18, 16, 18, 16)
        live_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        live_title = QLabel("🔴 Live Tracking Inspector (1Hz Update)")
        live_title.setObjectName("live_title")
        self._lbl_debug_status = QLabel("")
        self._lbl_debug_status.setObjectName("debug_status")
        header_layout.addWidget(live_title)
        header_layout.addStretch()
        header_layout.addWidget(self._lbl_debug_status)
        live_layout.addLayout(header_layout)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(10)

        def make_row(row: int, label_text: str) -> QLabel:
            lbl = QLabel(label_text)
            lbl.setObjectName("live_key")
            val = QLabel("—")
            val.setObjectName("live_val")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(val, row, 1)
            return val

        def make_row_col2(row: int, label_text: str) -> QLabel:
            lbl = QLabel(label_text)
            lbl.setObjectName("live_key")
            val = QLabel("—")
            val.setObjectName("live_val")
            val.setWordWrap(True)
            grid.addWidget(lbl, row, 2)
            grid.addWidget(val, row, 3)
            return val

        self._lbl_process = make_row(0, "Foreground Process:")
        self._lbl_exe = make_row(1, "Executable Path:")
        self._lbl_title = make_row(2, "Window Title:")
        self._lbl_category = make_row(3, "Detected Category:")
        self._lbl_timer = make_row(4, "Current Session Timer:")

        self._lbl_idle = make_row_col2(0, "Idle Status:")
        self._lbl_fullscreen = make_row_col2(1, "Fullscreen Detection:")
        self._lbl_game_reason = make_row_col2(2, "Game Detect Reason:")
        self._lbl_launcher_reason = make_row_col2(3, "Launcher Detect Reason:")
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(3, 2)

        live_layout.addLayout(grid)
        parent_layout.addWidget(live_frame)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 28px; font-weight: 700; color: {tm.color('text_main')}; }}
            QLabel#page_subtitle {{ font-size: 15px; font-weight: 600; color: {tm.color('text_sub')}; }}
            QLabel#result_lbl {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
            QLabel#live_title {{ font-weight: 700; font-size: 15px; color: {tm.color('text_main')}; }}
            QLabel#live_key {{ color: {tm.color('text_sub')}; font-size: 12px; font-weight: 600; }}
            QLabel#live_val {{ color: {tm.color('text_main')}; font-size: 12px; font-weight: 500; font-family: monospace; }}
            QPushButton#secondary_btn {{
                background-color: {tm.color('card_bg')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton#secondary_btn:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
        """)
        
        # Trigger update for dynamic status styles
        self._update_live_inspector()

    def _update_live_inspector(self) -> None:
        if self._tracker is None or not hasattr(self._tracker, "get_debug_state"):
            self._lbl_debug_status.setText("TrackingManager disconnected")
            return

        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        
        state = self._tracker.get_debug_state()
        debug_on = state.get("debug_enabled", False)
        self._lbl_debug_status.setText("🟢 Diagnostics Enabled" if debug_on else "⚪ Diagnostics Disabled (Enable in Settings)")
        self._lbl_debug_status.setStyleSheet(
            f"font-size: 12px; font-weight: 600; color: {tm.color('success_text')};" if debug_on else f"font-size: 12px; font-weight: 600; color: {tm.color('text_muted')};"
        )

        self._lbl_process.setText(state.get("process_name", "None"))
        self._lbl_exe.setText(state.get("exe_path", "—") or "—")
        self._lbl_title.setText(state.get("window_title", "—") or "—")
        self._lbl_category.setText(state.get("category", "None"))

        duration = state.get("session_timer_s", 0.0)
        mins = int(duration) // 60
        secs = int(duration) % 60
        self._lbl_timer.setText(f"{mins:02d}:{secs:02d} ({duration:.1f}s)")

        self._lbl_idle.setText("💤 IDLE" if state.get("is_idle") else "🟢 ACTIVE")
        self._lbl_fullscreen.setText("Fullscreen (exclusive / borderless)" if state.get("is_fullscreen") else "Windowed")
        self._lbl_game_reason.setText(state.get("game_reason", "—") or "—")
        self._lbl_launcher_reason.setText(state.get("launcher_reason", "—") or "—")

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

    def _refresh(self) -> None:
        query, category, start, end = self._get_filter_values()
        sessions = self._repo.search_sessions(query, category, start, end, limit=500)

        self._result_label.setText(f"{len(sessions)} raw session(s) logged")
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
                    session.end_time.strftime("%H:%M:%S") if session.end_time else "—"
                ),
                QTableWidgetItem(session.duration_formatted),
            ]
            items[1].setBackground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor(cat_color + "25"))

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
