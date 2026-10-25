"""
emergency_exit_dialog.py — Deliberate lockout exit.

The process is intentionally slow:
  1. hold the button for 10 seconds;
  2. enter the security PIN;
  3. wait through a 15-minute cooldown.

This keeps a deliberate escape hatch for safety while making a casual,
impulsive exit impossible.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ui.theme import ThemeManager


class EmergencyExitDialog(QDialog):
    def __init__(self, focus_manager, parent=None) -> None:
        super().__init__(parent)
        self._fm = focus_manager
        self._hold = 0.0
        self._hold_timer = QTimer(self)
        self._hold_timer.setInterval(100)
        self._hold_timer.timeout.connect(self._on_hold_tick)
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setInterval(1000)
        self._cooldown_timer.timeout.connect(self._on_cooldown_tick)
        self._cooldown_total = 15 * 60
        self.setWindowTitle("Emergency lockout exit")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        self._refresh_state()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        title = QLabel("Emergency exit")
        title.setObjectName("dialog_title")
        subtitle = QLabel(
            "Lockout is designed to be hard to leave. If you need to stop for safety, "
            "hold the button, confirm your PIN, and wait through the cooldown."
        )
        subtitle.setObjectName("dialog_subtitle")
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        self._status_card = QFrame()
        self._status_card.setObjectName("emergency_card")
        status_layout = QVBoxLayout(self._status_card)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(7)
        self._status = QLabel("Hold for 10 seconds to begin.")
        self._status.setObjectName("emergency_status")
        self._status.setWordWrap(True)
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        status_layout.addWidget(self._status)
        status_layout.addWidget(self._progress)
        root.addWidget(self._status_card)

        self._hold_btn = QPushButton("Hold to request exit · 10s")
        self._hold_btn.setObjectName("emergency_hold_btn")
        self._hold_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hold_btn.setMinimumHeight(46)
        self._hold_btn.pressed.connect(self._start_hold)
        self._hold_btn.released.connect(self._cancel_hold)
        root.addWidget(self._hold_btn)

        self._end_btn = QPushButton("End session now")
        self._end_btn.setObjectName("emergency_end_btn")
        self._end_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._end_btn.clicked.connect(self._end_now)
        self._end_btn.setVisible(False)
        root.addWidget(self._end_btn)

        footer = QHBoxLayout()
        footer.addStretch()
        close = QPushButton("Keep focusing")
        close.setObjectName("preset_btn")
        close.clicked.connect(self.reject)
        footer.addWidget(close)
        root.addLayout(footer)

    def _refresh_state(self) -> None:
        if not self._fm.is_active or not self._fm.is_lockout:
            self._status.setText("This session is no longer locked.")
            self._hold_btn.setEnabled(False)
            return
        if self._fm.is_emergency_pending:
            remaining = self._fm.emergency_unlock_remaining
            self._hold_btn.setVisible(False)
            self._status.setText(
                f"Emergency exit approved. The lockout remains for {remaining // 60}:{remaining % 60:02d}."
            )
            self._progress.setValue(
                int(100 * max(0, self._cooldown_total - remaining) / max(1, self._cooldown_total))
            )
            self._end_btn.setVisible(remaining <= 0)
            if not self._cooldown_timer.isActive():
                self._cooldown_timer.start()
        else:
            self._status.setText("Hold the button below for 10 seconds to begin.")
            self._progress.setValue(0)

    def _start_hold(self) -> None:
        self._hold = 0.0
        self._progress.setValue(0)
        self._status.setText("Keep holding…")
        self._hold_timer.start()

    def _cancel_hold(self) -> None:
        if self._hold_timer.isActive():
            self._hold_timer.stop()
            self._hold = 0.0
            self._progress.setValue(0)
            self._status.setText("Hold cancelled. Nothing changed.")

    def _on_hold_tick(self) -> None:
        self._hold += 0.1
        self._progress.setValue(int(min(100, self._hold / 10.0 * 100)))
        if self._hold >= 10.0:
            self._hold_timer.stop()
            self._status.setText("Hold complete. Confirm your PIN.")
            self._request_pin()

    def _request_pin(self) -> None:
        from ui.widgets.pin_dialog import PinDialog

        if not self._fm._pin_manager.is_enabled():
            self._status.setText("No PIN is configured. Set one in Settings before using Lockout.")
            self._hold_btn.setEnabled(False)
            return
        dialog = PinDialog(self._fm._pin_manager, self)
        if dialog.exec():
            if self._fm.request_emergency_exit(15):
                self._refresh_state()
        else:
            self._status.setText("PIN not confirmed. Lockout remains active.")
            self._hold_btn.setEnabled(True)
            self._progress.setValue(0)

    def _on_cooldown_tick(self) -> None:
        if not self._fm.is_active:
            self._cooldown_timer.stop()
            self.accept()
            return
        remaining = self._fm.emergency_unlock_remaining
        self._status.setText(
            f"Emergency exit approved. The lockout remains for {remaining // 60}:{remaining % 60:02d}."
        )
        self._progress.setValue(
            int(100 * max(0, self._cooldown_total - remaining) / max(1, self._cooldown_total))
        )
        if remaining <= 0:
            self._cooldown_timer.stop()
            self._end_btn.setVisible(True)
            self._status.setText("Cooldown complete. You can end the session now.")
            self._end_now()

    def _end_now(self) -> None:
        if self._fm.stop_focus():
            self.accept()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 22px; font-weight: 700; }}
            QLabel#dialog_subtitle {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QFrame#emergency_card {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 14px; }}
            QLabel#emergency_status {{ color: {tm.color('text_main')}; font-size: 12px; font-weight: 600; }}
            QProgressBar {{ background: {tm.color('surface_secondary')}; border: none; border-radius: 5px; height: 8px; }}
            QProgressBar::chunk {{ background: #FF9F0A; border-radius: 5px; }}
            QPushButton#emergency_hold_btn {{ background: rgba(255,159,10,.14); border: 1px solid rgba(255,159,10,.45); border-radius: 999px; color: #FF9F0A; font-size: 13px; font-weight: 700; }}
            QPushButton#emergency_hold_btn:hover {{ background: rgba(255,159,10,.24); }}
            QPushButton#emergency_end_btn {{ background: rgba(255,69,58,.14); border: 1px solid rgba(255,69,58,.4); border-radius: 999px; color: #FF453A; font-size: 12px; font-weight: 700; padding: 10px; }}
            QPushButton#preset_btn {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; color: {tm.color('text_sub')}; padding: 8px 16px; font-weight: 600; }}
        """)
