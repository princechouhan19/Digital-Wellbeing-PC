"""
blocked_app_dialog.py — Polished feedback modal displayed when an app is restricted by Focus Mode.
"""
from __future__ import annotations

import time
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect
)

from utils.icon_provider import AppIconProvider
from utils.win_utils import clean_fallback_name
from ui.icons import get_icon
from ui.theme import ThemeManager


class BlockedAppFeedbackDialog(QDialog):
    """
    Polished, clear modal dialog informing the user that an application
    was restricted by active Focus Mode, with actions to return to focus or cancel.
    """
    return_to_focus = Signal()
    cancel_focus = Signal()

    def __init__(
        self,
        process_name: str,
        mode_name: str,
        seconds_remaining: int,
        parent=None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog,
        )
        self.process_name = process_name
        self.mode_name = mode_name
        self.seconds_remaining = seconds_remaining
        
        self.setFixedSize(440, 390)
        self.setWindowTitle("App Blocked by Focus")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Smooth fade-in animation
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(200)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._bg_frame = QFrame()
        self._bg_frame.setObjectName("dialog_bg")
        layout = QVBoxLayout(self._bg_frame)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Top Header Row: Badge and close button
        top_row = QHBoxLayout()
        
        mode_formatted = self.mode_name.title()
        if mode_formatted.lower() == "deep":
            mode_formatted = "Deep Focus"
        elif not mode_formatted.endswith("Focus") and mode_formatted.lower() != "custom":
            mode_formatted = f"{mode_formatted} Mode"
            
        badge = QLabel(f"●  FOCUS MODE ACTIVE — {mode_formatted.upper()}")
        badge.setObjectName("focus_badge")
        top_row.addWidget(badge)
        top_row.addStretch()

        btn_close = QPushButton("×")
        btn_close.setObjectName("btn_dismiss_x")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        top_row.addWidget(btn_close)
        layout.addLayout(top_row)

        # App Icon
        icon_lbl = QLabel()
        icon = AppIconProvider().get_icon(self.process_name)
        if icon and not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(48, 48))
        else:
            ico = get_icon("lock", color="#FF9F0A", size=40)
            icon_lbl.setPixmap(ico.pixmap(40, 40))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        # App Name
        friendly_name = clean_fallback_name(self.process_name)
        self.name_lbl = QLabel(friendly_name)
        self.name_lbl.setObjectName("app_name")
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_lbl)

        # Explanation
        self.desc_lbl = QLabel(
            "This app is blocked because Focus Mode is currently active.\n\n"
            "If you want to use this app, cancel Focus Mode first."
        )
        self.desc_lbl.setObjectName("desc_text")
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.desc_lbl)

        # Mode & Time Card
        info_card = QFrame()
        info_card.setObjectName("info_card")
        info_card_layout = QHBoxLayout(info_card)
        info_card_layout.setContentsMargins(14, 8, 14, 8)
        info_card_layout.setSpacing(8)
        info_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        mins_rem = max(1, (self.seconds_remaining + 59) // 60)
        time_str = f"{mins_rem} min remaining in session" if mins_rem > 0 else "Finishing session"

        mode_lbl = QLabel(f"<span style='font-weight: 700; color: #0A84FF;'>{mode_formatted}</span> &nbsp;·&nbsp; {time_str}")
        mode_lbl.setObjectName("mode_info_lbl")
        mode_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_card_layout.addWidget(mode_lbl)
        layout.addWidget(info_card)

        layout.addSpacing(4)

        # Actions: Back to Focus and Cancel Focus
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_back = QPushButton("Back to Focus")
        self.btn_back.setObjectName("btn_primary")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self._on_back_to_focus)
        btn_layout.addWidget(self.btn_back)

        self.btn_cancel = QPushButton("Cancel Focus")
        self.btn_cancel.setObjectName("btn_secondary")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel_focus)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        main_layout.addWidget(self._bg_frame)

    def _on_back_to_focus(self) -> None:
        self.return_to_focus.emit()
        self.accept()

    def _on_cancel_focus(self) -> None:
        self.cancel_focus.emit()
        self.reject()

    def _apply_theme(self, is_dark: bool = True) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#dialog_bg {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 16px;
            }}
            QLabel#focus_badge {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('accent_amber')};
                letter-spacing: 0.8px;
            }}
            QPushButton#btn_dismiss_x {{
                background: transparent;
                border: none;
                color: {tm.color('text_muted')};
                font-size: 18px;
                font-weight: 700;
            }}
            QPushButton#btn_dismiss_x:hover {{
                color: {tm.color('text_main')};
            }}
            QLabel#app_name {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#desc_text {{
                font-size: 13px;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QFrame#info_card {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#mode_info_lbl {{
                font-size: 13px;
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_primary {{
                background: {tm.color('primary_btn_gradient')};
                color: #FFFFFF;
                border: 1px solid {tm.color('accent')};
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#btn_primary:hover {{
                background: {tm.color('primary_btn_hover')};
                border-color: {tm.color('accent_hover')};
            }}
        """)
