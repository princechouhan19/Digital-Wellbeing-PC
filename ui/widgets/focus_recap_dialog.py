"""
focus_recap_dialog.py — Post-session recap and recent Focus history.

Shows the just-finished session (blocked apps/sites, fragmentation vs. the
seven-day baseline, and the best next focus window) plus today/yesterday/7-day
history from the local `focus_sessions` table.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from database.repository import Repository
from ui.primitives import Card
from ui.theme import ThemeManager


MODE_LABELS = {
    "deep": "Deep Focus",
    "work": "Work",
    "study": "Study",
    "movie": "Media",
    "custom": "Custom",
}


def _duration(seconds: float) -> str:
    minutes = int(max(0, seconds) // 60)
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m" if hours else f"{mins}m"


class _Metric(Card):
    def __init__(self, title: str, value: str, sub: str = "", parent=None) -> None:
        super().__init__("recap_metric", padding=(16, 13, 16, 13), spacing=2, parent=parent)
        layout = self.body
        title_lbl = QLabel(title)
        title_lbl.setObjectName("recap_metric_title")
        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("recap_metric_value")
        self.sub_lbl = QLabel(sub)
        self.sub_lbl.setObjectName("recap_metric_sub")
        self.sub_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.sub_lbl)


class _SessionRow(QFrame):
    def __init__(self, session: dict, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("recap_session_row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        mode = MODE_LABELS.get(str(session.get("mode", "")), str(session.get("mode", "")).title())
        started = str(session.get("started_at", ""))
        try:
            start_dt = datetime.fromisoformat(started)
            time_text = start_dt.strftime("%a %H:%M")
        except ValueError:
            time_text = started[:16]

        left = QVBoxLayout()
        left.setSpacing(1)
        mode_lbl = QLabel(mode)
        mode_lbl.setObjectName("recap_session_mode")
        meta = QLabel(
            f"{time_text} · {_duration(float(session.get('actual_s') or 0))}"
        )
        meta.setObjectName("recap_session_meta")
        left.addWidget(mode_lbl)
        left.addWidget(meta)
        layout.addLayout(left, 1)

        counts = QLabel(
            f"{int(session.get('blocked_apps') or 0)} apps · "
            f"{int(session.get('blocked_sites') or 0)} sites"
        )
        counts.setObjectName("recap_session_counts")
        layout.addWidget(counts)

        status = "Completed" if session.get("was_completed") else "Ended early"
        status_lbl = QLabel(status)
        status_lbl.setObjectName("recap_session_status")
        layout.addWidget(status_lbl)


class FocusRecapDialog(QDialog):
    """Recap for the just-finished session; history is queryable by period."""

    def __init__(self, recap: Optional[dict] = None, parent=None) -> None:
        super().__init__(parent)
        self._recap = recap or {}
        self._repo = Repository()
        self._period = "today"
        self.setWindowTitle("Focus recap")
        self.setMinimumSize(720, 620)
        self.setModal(False)
        self._setup_ui()
        self._load_history()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 22)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title = QLabel("Session recap")
        title.setObjectName("dialog_title")
        subtitle = QLabel("What this session protected, and when to focus next.")
        subtitle.setObjectName("dialog_subtitle")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        close_btn = QPushButton("Done")
        close_btn.setObjectName("primary_pill_btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        # Current session metrics
        metrics = QGridLayout()
        metrics.setSpacing(10)
        self._duration_metric = _Metric("FOCUS TIME", _duration(self._recap.get("actual_s", 0)))
        self._blocked_metric = _Metric(
            "INTERRUPTIONS BLOCKED",
            str(int(self._recap.get("interruptions", 0) or 0)),
            "Apps and sites stopped during this session",
        )
        self._apps_metric = _Metric(
            "APPS BLOCKED",
            str(int(self._recap.get("blocked_apps", 0) or 0)),
        )
        self._sites_metric = _Metric(
            "SITES BLOCKED",
            str(int(self._recap.get("blocked_sites", 0) or 0)),
        )
        metrics.addWidget(self._duration_metric, 0, 0)
        metrics.addWidget(self._blocked_metric, 0, 1)
        metrics.addWidget(self._apps_metric, 1, 0)
        metrics.addWidget(self._sites_metric, 1, 1)
        root.addLayout(metrics)

        # Fragmentation comparison + next window
        insight_row = QHBoxLayout()
        insight_row.setSpacing(10)
        self._fragmentation = QLabel("")
        self._fragmentation.setObjectName("recap_insight")
        self._fragmentation.setWordWrap(True)
        insight_row.addWidget(self._fragmentation, 1)

        self._next_window = QLabel("")
        self._next_window.setObjectName("recap_next_window")
        self._next_window.setAlignment(Qt.AlignmentFlag.AlignCenter)
        insight_row.addWidget(self._next_window)
        root.addLayout(insight_row)

        idx = float(self._recap.get("fragmentation_index", 0) or 0)
        baseline = float(self._recap.get("baseline_index", 0) or 0)
        delta = self._recap.get("fragmentation_delta_pct")
        if baseline > 0 and delta is not None:
            direction = "lower" if delta < 0 else "higher"
            self._fragmentation.setText(
                f"Fragmentation: {idx:.1f} switches/hr · {abs(float(delta)):.0f}% "
                f"{direction} than your 7-day baseline ({baseline:.1f})."
            )
        else:
            self._fragmentation.setText(
                f"Fragmentation: {idx:.1f} switches/hr. A baseline will appear after a few days."
            )
        best = self._recap.get("best_next_window") or {}
        self._next_window.setText(
            ("Best next window\n" + best.get("label", "Next 2 hours"))
            if best else "Best next window\nNext 2 hours"
        )

        # History period selector
        period_row = QHBoxLayout()
        period_row.setSpacing(6)
        history_lbl = QLabel("HISTORY")
        history_lbl.setObjectName("recap_history_title")
        period_row.addWidget(history_lbl)
        period_row.addStretch()
        self._period_buttons = []
        for key, label in (("today", "Today"), ("yesterday", "Yesterday"), ("week", "Previous 7 days")):
            btn = QPushButton(label)
            btn.setObjectName("recap_period_btn")
            btn.setCheckable(True)
            btn.setChecked(key == self._period)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, k=key: self._set_period(k))
            period_row.addWidget(btn)
            self._period_buttons.append((key, btn))
        root.addLayout(period_row)

        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._history_container = QWidget()
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(0, 0, 0, 0)
        self._history_layout.setSpacing(6)
        self._history_layout.addStretch()
        self._history_scroll.setWidget(self._history_container)
        root.addWidget(self._history_scroll, 1)

    def _set_period(self, period: str) -> None:
        self._period = period
        for key, btn in self._period_buttons:
            btn.setChecked(key == period)
        self._load_history()

    def _load_history(self) -> None:
        while self._history_layout.count() > 1:
            item = self._history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today = date.today()
        if self._period == "today":
            sessions = self._repo.get_focus_sessions(20, today, today)
        elif self._period == "yesterday":
            yesterday = today - timedelta(days=1)
            sessions = self._repo.get_focus_sessions(20, yesterday, yesterday)
        else:
            sessions = self._repo.get_focus_sessions(30, today - timedelta(days=7), today - timedelta(days=1))

        if not sessions:
            empty = QLabel("No sessions in this period.")
            empty.setObjectName("recap_empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._history_layout.insertWidget(0, empty)
            return
        for index, session in enumerate(sessions):
            self._history_layout.insertWidget(index, _SessionRow(session))

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 24px; font-weight: 700; }}
            QLabel#dialog_subtitle {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QFrame#recap_metric {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 14px; }}
            QLabel#recap_metric_title {{ color: {tm.color('text_muted')}; font-size: 10px; font-weight: 700; letter-spacing: 1.1px; }}
            QLabel#recap_metric_value {{ color: {tm.color('text_main')}; font-size: 22px; font-weight: 700; }}
            QLabel#recap_metric_sub {{ color: {tm.color('text_sub')}; font-size: 10px; }}
            QLabel#recap_insight {{ color: {tm.color('text_main')}; font-size: 12px; font-weight: 500; padding: 8px 0; }}
            QLabel#recap_next_window {{ color: {tm.color('accent_tint_text')}; font-size: 11px; font-weight: 700; background: {tm.color('accent_tint_bg')}; border: 1px solid {tm.color('accent_tint_border')}; border-radius: 12px; padding: 8px 14px; }}
            QLabel#recap_history_title {{ color: {tm.color('text_muted')}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; }}
            QPushButton#recap_period_btn {{ background: transparent; border: 1px solid transparent; border-radius: 9px; color: {tm.color('text_sub')}; padding: 5px 10px; font-size: 11px; font-weight: 600; }}
            QPushButton#recap_period_btn:hover {{ color: {tm.color('text_main')}; background: {tm.color('surface_hover')}; }}
            QPushButton#recap_period_btn:checked {{ color: {tm.color('accent_tint_text')}; background: {tm.color('accent_tint_bg')}; border-color: {tm.color('accent_tint_border')}; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 999px; padding: 8px 20px; font-size: 12px; font-weight: 700; }}
            QPushButton#primary_pill_btn:hover {{ background: {tm.color('accent_hover')}; }}
            QFrame#recap_session_row {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; }}
            QLabel#recap_session_mode {{ color: {tm.color('text_main')}; font-size: 12px; font-weight: 600; }}
            QLabel#recap_session_meta {{ color: {tm.color('text_muted')}; font-size: 10px; }}
            QLabel#recap_session_counts {{ color: {tm.color('text_sub')}; font-size: 10px; }}
            QLabel#recap_session_status {{ color: {tm.color('text_muted')}; font-size: 10px; }}
            QLabel#recap_empty {{ color: {tm.color('text_muted')}; font-size: 12px; padding: 24px; }}
        """)
