"""
adult_motivation_dialog.py — Apple-style Motivational Intervention Modal.

Displayed immediately over the browser when adult search queries or explicit
content are detected, empowering the user with cognitive reflection,
breathing prompts, and positive reinforcement to quit.
"""
from __future__ import annotations

import random
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)

from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager


MOTIVATIONAL_AFFIRMATIONS = [
    (
        "Discipline is choosing between what you want now and what you want most.",
        "Abraham Lincoln"
    ),
    (
        "The urge will pass in 5 minutes. Your self-respect, energy, and peace of mind will last forever.",
        "Mindful Focus"
    ),
    (
        "Every time you say NO to an impulse, you rewire your neural pathways for genuine strength.",
        "Neuroplasticity Principle"
    ),
    (
        "Pause and take 3 slow, deep breaths. Reconnect with who you want to be tomorrow.",
        "Breath & Clarity"
    ),
    (
        "Momentary dopamine spikes always lead to regret. True peace comes from mastery over your impulses.",
        "Stoic Wisdom"
    ),
    (
        "You are in full control of your mind and actions. Choose strength, dignity, and clarity today.",
        "Self-Mastery"
    ),
]


class AdultContentMotivationDialog(QDialog):
    """
    Apple Design System motivational dialog displayed over the active browser.
    Provides immediate positive psychology, affirmations, and box breathing.
    """
    start_focus_requested = Signal()

    def __init__(self, reason: str = "", title_context: str = "", parent=None):
        super().__init__(parent, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.reason = reason
        self.title_context = title_context
        self._drag_pos = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 420)
        self.setWindowTitle("Pause & Reflect — Digital Wellbeing")

        # Smooth fade-in
        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._anim = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos") and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)

        self.container = QFrame()
        self.container.setObjectName("dialogContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 1. Header Row
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(36, 36)
        icon_frame.setObjectName("shield_icon_frame")
        if_layout = QVBoxLayout(icon_frame)
        if_layout.setContentsMargins(0, 0, 0, 0)
        if_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shield_icon = QLabel()
        shield_icon.setPixmap(get_pixmap("shield", color="#0A84FF", size=20))
        if_layout.addWidget(shield_icon)
        hdr_row.addWidget(icon_frame)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("Pause & Reflect")
        title.setObjectName("titleLbl")
        subtitle = QLabel("Restricted adult search or site blocked.")
        subtitle.setObjectName("subLbl")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr_row.addLayout(title_box, 1)

        btn_close = QPushButton()
        btn_close.setObjectName("apple_close_btn")
        btn_close.setFixedSize(26, 26)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setIcon(get_icon("close", color="#8E8E93", size=10))
        btn_close.clicked.connect(self.accept)
        hdr_row.addWidget(btn_close)

        layout.addLayout(hdr_row)

        # 2. Main Motivational Affirmation Card
        quote_card = QFrame()
        quote_card.setObjectName("apple_inset_card")
        q_layout = QVBoxLayout(quote_card)
        q_layout.setContentsMargins(18, 16, 18, 16)
        q_layout.setSpacing(8)

        quote_text, author = random.choice(MOTIVATIONAL_AFFIRMATIONS)

        lbl_quote = QLabel(f"“{quote_text}”")
        lbl_quote.setObjectName("quote_lbl")
        lbl_quote.setWordWrap(True)
        lbl_quote.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q_layout.addWidget(lbl_quote)

        lbl_author = QLabel(f"— {author}")
        lbl_author.setObjectName("author_lbl")
        lbl_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q_layout.addWidget(lbl_author)

        layout.addWidget(quote_card)

        # 3. Calming Box Breathing Tip Card
        breath_card = QFrame()
        breath_card.setObjectName("breath_card")
        b_layout = QHBoxLayout(breath_card)
        b_layout.setContentsMargins(14, 10, 14, 10)
        b_layout.setSpacing(10)

        calm_icon = QLabel()
        calm_icon.setPixmap(get_pixmap("sparkles", color="#30D158", size=16))
        b_layout.addWidget(calm_icon)

        b_text = QLabel("Box Breathing Reset: Inhale for 4s · Hold for 4s · Exhale for 4s")
        b_text.setObjectName("breath_lbl")
        b_layout.addWidget(b_text, 1)
        layout.addWidget(breath_card)

        layout.addStretch()

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_focus = QPushButton("Start 5-min Focus Reset")
        self.btn_focus.setObjectName("apple_btn_secondary")
        self.btn_focus.setFixedHeight(36)
        self.btn_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_focus.clicked.connect(self._on_start_focus)
        btn_layout.addWidget(self.btn_focus)

        self.btn_control = QPushButton("I Choose Self-Control")
        self.btn_control.setObjectName("apple_btn_primary")
        self.btn_control.setFixedHeight(36)
        self.btn_control.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_control.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_control)

        layout.addLayout(btn_layout)
        main_layout.addWidget(self.container)

    def _on_start_focus(self):
        self.start_focus_requested.emit()
        self.accept()

    def _apply_theme(self, is_dark: bool):
        tm = ThemeManager.instance()
        dialog_bg = "#1C1C1E" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
        card_bg = "#2C2C2E" if is_dark else "#F2F2F7"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        breath_bg = "rgba(48, 209, 88, 0.12)" if is_dark else "rgba(48, 209, 88, 0.15)"
        breath_text = "#30D158" if is_dark else "#248A3D"
        text_main = "#F5F5F7" if is_dark else "#1D1D1F"
        text_sub = "#8E8E93" if is_dark else "#6E6E73"
        close_bg = "#2C2C2E" if is_dark else "#E5E5EA"
        close_hover = "#3A3A3C" if is_dark else "#D1D1D6"
        btn_sec_bg = "#2C2C2E" if is_dark else "#E5E5EA"
        btn_sec_hover = "#3A3A3C" if is_dark else "#D1D1D6"
        accent = tm.color("accent", "#0A84FF")
        accent_hover = "#0071E3"

        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {dialog_bg};
                border: 1px solid {border_col};
                border-radius: 18px;
            }}
            QFrame#shield_icon_frame {{
                background-color: rgba(10, 132, 255, 0.15);
                border-radius: 10px;
            }}
            QLabel#titleLbl {{
                font-size: 17px;
                font-weight: 700;
                color: {text_main};
                font-family: -apple-system, "SF Pro Display", "Inter", sans-serif;
            }}
            QLabel#subLbl {{
                font-size: 12px;
                color: {text_sub};
            }}
            QPushButton#apple_close_btn {{
                background-color: {close_bg};
                border: none;
                border-radius: 13px;
            }}
            QPushButton#apple_close_btn:hover {{
                background-color: {close_hover};
            }}
            QFrame#apple_inset_card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 14px;
            }}
            QLabel#quote_lbl {{
                font-size: 14px;
                font-weight: 600;
                line-height: 1.4;
                color: {text_main};
                font-style: italic;
            }}
            QLabel#author_lbl {{
                font-size: 12px;
                font-weight: 500;
                color: {accent};
            }}
            QFrame#breath_card {{
                background-color: {breath_bg};
                border-radius: 10px;
            }}
            QLabel#breath_lbl {{
                font-size: 12px;
                font-weight: 600;
                color: {breath_text};
            }}
            QPushButton#apple_btn_secondary {{
                background-color: {btn_sec_bg};
                border: 1px solid {card_border};
                border-radius: 10px;
                padding: 0 14px;
                color: {text_main};
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#apple_btn_secondary:hover {{
                background-color: {btn_sec_hover};
            }}
            QPushButton#apple_btn_primary {{
                background-color: {accent};
                border: none;
                border-radius: 10px;
                padding: 0 16px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#apple_btn_primary:hover {{
                background-color: {accent_hover};
            }}
        """)
