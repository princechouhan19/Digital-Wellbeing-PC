"""
countdown_dialog.py — PySide6 Power Action Warning Countdown Dialog for SleepGuard in Digital Wellbeing v2.4.

v2.4 changes:
- Displays and carries the configured action type (shutdown/sleep/hibernate/lock)
- shutdown_accepted signal now carries the action string
- Emits shutdown_cancelled on closeEvent for safety
- Redesigned in the Aurora frosted warning design language.
"""

from __future__ import annotations

import logging
import time

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

logger = logging.getLogger("digital_wellbeing.ui.countdown")

# Human-readable labels for each action type
_ACTION_LABELS = {
    "shutdown": "Shut Down",
    "sleep": "Sleep",
    "hibernate": "Hibernate",
    "lock": "Lock",
    "cancel": "Cancel",
}

# SVG icon (ui/icons.py) for each action type
_ACTION_SVG_ICONS = {
    "shutdown": "power",
    "sleep": "moon",
    "hibernate": "snowflake",
    "lock": "lock",
    "cancel": "close",
}


class ShutdownCountdownDialog(QDialog):
    """Modal countdown dialog warning the user before an automatic PC power action."""

    # Signal carries the action string so the handler knows what to execute
    shutdown_accepted = Signal(str)
    shutdown_cancelled = Signal()
    test_completed = Signal()

    def __init__(
        self,
        countdown_seconds: int = 60,
        action: str = "lock",
        parent=None,
        is_test: bool = False,
    ) -> None:
        super().__init__(parent)
        self._action = action.lower().strip() or "lock"
        self._action_label = _ACTION_LABELS.get(self._action, self._action.title())
        self._is_test = bool(is_test)

        if self._is_test:
            self.setWindowTitle(f"SleepGuard — Test Warning Preview ({self._action_label})")
        else:
            self.setWindowTitle(f"SleepGuard — Automatic {self._action_label} Warning")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.Dialog
        )
        self.setFixedSize(460, 270)

        self._remaining_s = countdown_seconds
        self._cancelled = False
        self._completed = False

        logger.info(
            "[SLEEPGUARD_DIALOG] Constructed. countdown=%d, action='%s', is_test=%s",
            countdown_seconds, self._action, self._is_test,
        )

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self._setup_ui()
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _apply_theme(self, is_dark: bool = True) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('warning_border')};
                border-radius: 14px;
            }}
            QLabel#hdr {{
                color: {tm.color('text_main')};
                font-size: 16px;
                font-weight: 700;
                letter-spacing: -0.3px;
            }}
            QLabel#msg {{
                color: {tm.color('text_sub')};
                font-size: 13px;
            }}
            QLabel#timer_display {{
                color: {tm.color('accent_amber')};
                font-size: 52px;
                font-weight: 700;
                font-family: 'Segoe UI', monospace;
                letter-spacing: 2px;
                margin: 4px 0;
            }}
            QPushButton#primary_action_btn {{
                background: {tm.color('accent_amber')};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 20px;
                border: 1px solid {tm.color('accent_amber')};
                border-radius: 8px;
            }}
            QPushButton#primary_action_btn:hover {{
                background: {tm.color('accent_amber_hover')};
                border-color: {tm.color('accent_amber_hover')};
            }}
            QPushButton#secondary_action_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 10px 20px;
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
            }}
            QPushButton#secondary_action_btn:hover {{
                background-color: {tm.color('surface_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('border_hover')};
            }}
        """)

    def _setup_ui(self) -> None:

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(8)

        # Warning capsule header
        hdr_row = QHBoxLayout()
        hdr_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from ui.icons import get_pixmap
        icon_name = _ACTION_SVG_ICONS.get(self._action, "moon")
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap(icon_name, "#FF9F0A", 20))
        icon_lbl.setStyleSheet("margin-right: 6px;")
        hdr_row.addWidget(icon_lbl)

        hdr_text = "SLEEPGUARD WARNING" if self._is_test else "SleepGuard — Inactivity Warning"
        hdr = QLabel(hdr_text)
        hdr.setObjectName("hdr")
        hdr_row.addWidget(hdr)
        layout.addLayout(hdr_row)

        msg_text = (
            f"The system is preparing to perform:\n{self._action_label}"
            if self._is_test
            else f"Your PC will automatically {self._action_label.lower()} in"
        )
        msg = QLabel(msg_text)
        msg.setObjectName("msg")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        m, s = divmod(self._remaining_s, 60)
        self._timer_lbl = QLabel(f"{m:02d}:{s:02d}")
        self._timer_lbl.setObjectName("timer_display")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._timer_lbl)

        if self._is_test:
            desc = QLabel("This is a test preview. No power action will be performed.")
            desc.setObjectName("msg")
            desc.setStyleSheet("color: #FF9F0A; font-size: 12px; font-weight: 600;")
        else:
            desc = QLabel("Any keyboard or mouse input will automatically abort the power action.")
            desc.setObjectName("msg")
            desc.setStyleSheet("color: #6E6E73; font-size: 12px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(10)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("secondary_action_btn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        if self._is_test:
            self._confirm_btn = QPushButton("Close Preview")
            self._confirm_btn.setObjectName("primary_action_btn")
            self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._confirm_btn.clicked.connect(self._on_test_accept)
        else:
            self._confirm_btn = QPushButton(f"{self._action_label} Now")
            self._confirm_btn.setObjectName("primary_action_btn")
            self._confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._confirm_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(btn_row)

    def start_countdown(self) -> None:
        self._deadline = time.monotonic() + self._remaining_s
        self._timer.start()
        logger.info(
            "[SLEEPGUARD_DIALOG] Countdown started. action='%s', remaining=%ds, is_test=%s, timer_active=%s",
            self._action, self._remaining_s, self._is_test, self._timer.isActive(),
        )

    def _on_tick(self) -> None:
        # User-activity detection is handled by SleepGuardController which
        # calls cancel_warning() and emits programmatic_shutdown_cancelled.
        if hasattr(self, "_deadline"):
            calc_s = max(0, int(round(self._deadline - time.monotonic())))
            if calc_s < self._remaining_s:
                self._remaining_s = calc_s
            else:
                self._remaining_s = max(0, self._remaining_s - 1)
                self._deadline = time.monotonic() + self._remaining_s
        elif self._remaining_s > 0:
            self._remaining_s -= 1

        m, s = divmod(self._remaining_s, 60)
        self._timer_lbl.setText(f"{m:02d}:{s:02d}")
        logger.debug("[SLEEPGUARD_DIALOG] Tick: remaining=%ds", self._remaining_s)

        # Complete on the tick which displays 00:00.
        if self._remaining_s <= 0:
            self._timer.stop()
            if self._is_test:
                self._on_test_accept()
            else:
                self._on_accept()

    def force_cancel(self) -> None:
        """Slot called by the SleepGuardController when it detects user activity.
        This allows the controller -- not the dialog -- to own activity detection.
        """
        if not self._cancelled and not self._completed:
            logger.info("[SLEEPGUARD_DIALOG] force_cancel() called by controller.")
            self._on_cancel()

    def _on_accept(self) -> None:
        if self._cancelled or self._completed:
            return
        if self._is_test:
            self._on_test_accept()
            return
        self._completed = True
        self._timer.stop()
        logger.info(
            "[SLEEPGUARD_DIALOG] Countdown expired or action accepted. Executing action='%s'",
            self._action,
        )
        self.shutdown_accepted.emit(self._action)
        self.accept()

    def _on_test_accept(self) -> None:
        if self._cancelled or self._completed:
            return
        self._completed = True
        self._timer.stop()
        logger.info("[SLEEPGUARD_DIALOG] Test preview finished safely. No power action performed.")
        self.test_completed.emit()
        self.accept()

    def _on_cancel(self) -> None:
        self._cancelled = True
        self._timer.stop()
        logger.info("[SLEEPGUARD_DIALOG] User clicked Cancel.")
        self.shutdown_cancelled.emit()
        self.reject()

    def closeEvent(self, event) -> None:
        """Treat closing the dialog (e.g. Alt+F4) as cancellation for safety."""
        if not self._cancelled and not self._completed:
            self._cancelled = True
            self._timer.stop()
            logger.info("[SLEEPGUARD_DIALOG] Dialog closed via closeEvent — treating as cancel.")
            self.shutdown_cancelled.emit()
        super().closeEvent(event)

    def paintEvent(self, event):
        if not getattr(self, "_logged_paint", False):
            logger.info("[SLEEPGUARD_DIALOG] First paintEvent — dialog is visible on screen.")
            self._logged_paint = True
        super().paintEvent(event)


ShutdownWarningDialog = ShutdownCountdownDialog
