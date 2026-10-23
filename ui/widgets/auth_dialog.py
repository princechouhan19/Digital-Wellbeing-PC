"""
auth_dialog.py — Premium Windows Hello + PIN authentication dialog for App Locker.

Handles all authentication states gracefully:
  - Windows Hello available       → show primary Hello button
  - Windows Hello unavailable     → show PIN only
  - Hello in progress             → spinner + status text
  - Hello success                 → accept (close with QDialog.Accepted)
  - Hello canceled/failed         → offer retry or PIN fallback
  - Wrong PIN                     → error label, clear field, stay open
  - Correct PIN                   → accept
  - Cancel                        → reject

Theme compliance: 100% ThemeManager.color() tokens — works in dark AND light mode.
Enter key: triggers unlock when PIN field is focused.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QWidget, QSizePolicy,
)
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QGraphicsOpacityEffect

from protection.windows_hello import WindowsHelloAuth, HelloAvailability, HelloResult
from core.logger import logger


class AppLockerAuthDialog(QDialog):
    """Premium authentication dialog for App Locker.

    Shows Windows Hello button when available, PIN as fallback.
    Call exec() — returns QDialog.Accepted on success, QDialog.Rejected on cancel.
    """

    def __init__(
        self,
        process_name: str,
        display_name: str,
        pin_manager,                   # protection.pin.PINManager
        auth_method: str = "hello_pin",  # "hello" | "pin" | "hello_pin"
        parent=None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        self._process_name = process_name
        self._display_name = display_name
        self._pin_manager = pin_manager
        self._auth_method = auth_method

        self._hello = WindowsHelloAuth(self)
        self._hello.result_ready.connect(self._on_hello_result)

        self._hello_available = (
            self._hello.check_availability() == HelloAvailability.AVAILABLE
            and auth_method in ("hello", "hello_pin")
        )

        self._hello_timer = QTimer(self)
        self._hello_timer.setInterval(200)
        self._hello_timer.timeout.connect(self._force_hello_foreground)

        self.setFixedWidth(380)
        self.setMinimumHeight(180)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._fade_in = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade_in.setDuration(220)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        self._apply_theme()
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        from ui.theme import ThemeManager, apply_mica
        apply_mica(int(self.winId()), ThemeManager.instance().is_dark)

        self._update_state_idle()

    # ─── show event ──────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fade_in.start()

    # ─── UI build ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._bg = QFrame()
        self._bg.setObjectName("auth_bg")

        inner = QVBoxLayout(self._bg)
        inner.setContentsMargins(28, 28, 28, 24)
        inner.setSpacing(0)

        # ── Lock icon + title ──────────────────────────────────────────────
        from ui.icons import get_pixmap
        icon_box = QHBoxLayout()
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge = QFrame()
        icon_badge.setFixedSize(52, 52)
        icon_badge.setStyleSheet("""
            QFrame {
                background: rgba(255, 159, 10, 0.14);
                border: 1px solid rgba(255, 159, 10, 0.32);
                border-radius: 20px;
            }
        """)
        ib_layout = QVBoxLayout(icon_badge)
        ib_layout.setContentsMargins(0, 0, 0, 0)
        ib_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_pixmap("lock", "#FF9F0A", 24))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ib_layout.addWidget(icon_lbl)
        
        icon_box.addWidget(icon_badge)
        inner.addLayout(icon_box)

        inner.addSpacing(12)

        title_lbl = QLabel("Application Locked")
        title_lbl.setObjectName("auth_title")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(title_lbl)

        inner.addSpacing(4)

        app_lbl = QLabel(self._display_name)
        app_lbl.setObjectName("auth_app_name")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(app_lbl)

        inner.addSpacing(6)

        desc_lbl = QLabel("This app is protected by Digital Wellbeing.")
        desc_lbl.setObjectName("auth_desc")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        inner.addWidget(desc_lbl)

        inner.addSpacing(20)

        # ── Status label (spinner text / error / instruction) ──────────────
        self._status_lbl = QLabel()
        self._status_lbl.setObjectName("auth_status")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setWordWrap(True)
        inner.addWidget(self._status_lbl)

        inner.addSpacing(14)

        # ── Windows Hello button ───────────────────────────────────────────
        self._hello_btn = QPushButton("Use Windows Hello")
        self._hello_btn.setObjectName("auth_hello_btn")
        self._hello_btn.setMinimumHeight(44)
        self._hello_btn.clicked.connect(self._do_hello_auth)
        self._hello_btn.setVisible(self._hello_available)
        inner.addWidget(self._hello_btn)

        if self._hello_available:
            inner.addSpacing(10)

        # ── PIN section ────────────────────────────────────────────────────
        show_pin_initially = (
            not self._hello_available or self._auth_method == "pin"
        )

        self._pin_widget = QWidget()
        pin_layout = QVBoxLayout(self._pin_widget)
        pin_layout.setContentsMargins(0, 0, 0, 0)
        pin_layout.setSpacing(8)

        # "Use PIN instead" toggle (shown when Hello is available)
        self._pin_toggle_btn = QPushButton("Use PIN instead")
        self._pin_toggle_btn.setObjectName("auth_link_btn")
        self._pin_toggle_btn.setFlat(True)
        self._pin_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pin_toggle_btn.clicked.connect(self._show_pin_section)
        # Show toggle only if Hello is available AND pin is a fallback option
        self._pin_toggle_btn.setVisible(
            self._hello_available and self._auth_method == "hello_pin"
        )
        inner.addWidget(self._pin_toggle_btn)

        self._pin_input = QLineEdit()
        self._pin_input.setPlaceholderText("Enter your PIN")
        self._pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pin_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pin_input.setMaxLength(8)
        self._pin_input.returnPressed.connect(self._do_pin_auth)
        pin_layout.addWidget(self._pin_input)

        self._pin_error_lbl = QLabel()
        self._pin_error_lbl.setObjectName("auth_error")
        self._pin_error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pin_layout.addWidget(self._pin_error_lbl)

        self._pin_unlock_btn = QPushButton("Unlock with PIN")
        self._pin_unlock_btn.setObjectName("auth_pin_btn")
        self._pin_unlock_btn.setMinimumHeight(40)
        self._pin_unlock_btn.clicked.connect(self._do_pin_auth)
        pin_layout.addWidget(self._pin_unlock_btn)

        self._pin_widget.setVisible(show_pin_initially)
        inner.addWidget(self._pin_widget)

        inner.addStretch()

        # ── Cancel button ──────────────────────────────────────────────────
        inner.addSpacing(12)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("auth_cancel_btn")
        self._cancel_btn.setMinimumHeight(36)
        self._cancel_btn.clicked.connect(self.reject)
        inner.addWidget(self._cancel_btn)

        outer.addWidget(self._bg)

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()

        self.setStyleSheet(f"""
            QFrame#auth_bg {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#auth_icon {{
                font-size: 28px;
            }}
            QLabel#auth_title {{
                font-size: 17px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#auth_app_name {{
                font-size: 13px;
                font-weight: 700;
                color: {tm.color('accent')};
            }}
            QLabel#auth_desc {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QLabel#auth_status {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('text_sub')};
            }}
            QLabel#auth_error {{
                font-size: 11px;
                font-weight: 600;
                color: {tm.color('danger_text')};
            }}
            QPushButton#auth_hello_btn {{
                background-color: {tm.color('accent')};
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                border: none;
                border-radius: 10px;
                padding: 10px 16px;
            }}
            QPushButton#auth_hello_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#auth_hello_btn:disabled {{
                background-color: {tm.color('border')};
                color: {tm.color('text_muted')};
            }}
            QPushButton#auth_pin_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 600;
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                padding: 9px 16px;
            }}
            QPushButton#auth_pin_btn:hover {{
                background-color: {tm.color('card_hover')};
            }}
            QPushButton#auth_cancel_btn {{
                background-color: transparent;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 8px 14px;
            }}
            QPushButton#auth_cancel_btn:hover {{
                background-color: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#auth_link_btn {{
                color: {tm.color('accent')};
                font-size: 11px;
                font-weight: 600;
                border: none;
                background: transparent;
                text-align: center;
                padding: 2px 0;
            }}
            QPushButton#auth_link_btn:hover {{
                color: {tm.color('accent_hover')};
            }}
            QLineEdit {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 10px;
                color: {tm.color('text_main')};
                font-size: 16px;
                font-weight: 700;
                letter-spacing: 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {tm.color('accent')};
            }}
        """)

    # ─── State helpers ────────────────────────────────────────────────────────

    def _update_state_idle(self) -> None:
        if self._hello_available:
            self._status_lbl.setText("Use your face, fingerprint, or Windows Hello PIN.")
        elif self._pin_manager and self._pin_manager.is_enabled():
            self._status_lbl.setText("Enter your PIN to unlock.")
        else:
            self._status_lbl.setText("No authentication method configured.")

    def _update_state_verifying(self) -> None:
        self._status_lbl.setText("Waiting for Windows Hello...\n\nThe native Windows security interface handles authentication.")
        self._hello_btn.setVisible(False)
        self._pin_toggle_btn.setVisible(False)
        self._cancel_btn.setVisible(False)
        self.adjustSize()
        
        # Drop Always-On-Top so Windows Hello can take foreground cleanly without Qt window recreation
        try:
            import win32gui
            import win32con
            win32gui.SetWindowPos(int(self.winId()), win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            logger.warning(f"Failed to drop topmost flag: {e}")

    def _update_state_error(self, msg: str) -> None:
        # Restore Always-On-Top to re-secure the blocked application
        try:
            import win32gui
            import win32con
            win32gui.SetWindowPos(int(self.winId()), win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            logger.warning(f"Failed to restore topmost flag: {e}")
            
        self._status_lbl.setText(msg)
        self._hello_btn.setVisible(True)
        self._hello_btn.setEnabled(True)
        self._pin_toggle_btn.setVisible(self._hello_available and self._auth_method == "hello_pin")
        self._cancel_btn.setVisible(True)
        self.adjustSize()

    def _force_hello_foreground(self) -> None:
        try:
            import win32gui
            def enum_cb(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    cls = win32gui.GetClassName(hwnd)
                    txt = win32gui.GetWindowText(hwnd)
                    if "Credential Dialog" in cls or "Windows Security" in txt:
                        results.append(hwnd)
            hwnds = []
            win32gui.EnumWindows(enum_cb, hwnds)
            if hwnds:
                win32gui.SetForegroundWindow(hwnds[0])
                self._hello_timer.stop()
        except Exception as e:
            pass

    def _show_pin_section(self) -> None:
        self._pin_widget.setVisible(True)
        self._pin_toggle_btn.setVisible(False)
        self._pin_input.setFocus()

    # ─── Windows Hello auth ───────────────────────────────────────────────────

    def _do_hello_auth(self) -> None:
        if self._hello.is_busy():
            return
        self._update_state_verifying()
        self._hello_timer.start()
        self._hello.request_verification(
            f"Unlock {self._display_name}"
        )

    def _on_hello_result(self, result_int: int) -> None:
        self._hello_timer.stop()
        result = HelloResult(result_int)
        logger.info("Windows Hello result for %s: %s", self._process_name, result.name)

        if result == HelloResult.VERIFIED:
            self.accept()
        elif result == HelloResult.CANCELED:
            self._update_state_error("Windows Hello canceled.")
        elif result == HelloResult.NOT_CONFIGURED:
            self._update_state_error("Windows Hello not configured for this account.")
            if self._auth_method == "hello_pin":
                self._show_pin_section()
        elif result == HelloResult.UNAVAILABLE:
            self._update_state_error("Windows Hello is not available on this device.")
            if self._auth_method == "hello_pin":
                self._show_pin_section()
        elif result == HelloResult.DEVICE_BUSY:
            self._update_state_error("Windows Hello device is busy. Please try again.")
        elif result == HelloResult.FAILED:
            self._update_state_error("Windows Hello authentication failed. Try again.")
        else:
            self._update_state_error("An unexpected error occurred. Try your PIN again.")
            if self._auth_method == "hello_pin":
                self._show_pin_section()

    # ─── PIN auth ─────────────────────────────────────────────────────────────

    def _do_pin_auth(self) -> None:
        if not self._pin_manager:
            self._pin_error_lbl.setText("PIN manager not available.")
            return

        pin = self._pin_input.text().strip()
        if not pin:
            self._pin_error_lbl.setText("PIN cannot be empty.")
            return

        if self._pin_manager.verify_pin(pin):
            self.accept()
        else:
            self._pin_error_lbl.setText("Incorrect PIN. Try again.")
            self._pin_input.clear()
            self._pin_input.setFocus()
