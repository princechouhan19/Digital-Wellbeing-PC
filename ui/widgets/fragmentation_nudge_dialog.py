"""
fragmentation_nudge_dialog.py — Non-intrusive attention reset prompt.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from ui.theme import ThemeManager


class FragmentationNudgeDialog(QDialog):
    def __init__(self, switches: int, focus_manager, parent=None) -> None:
        super().__init__(parent)
        self._switches = switches
        self._fm = focus_manager
        self.setWindowTitle("Attention reset")
        self.setMinimumWidth(460)
        self.setModal(False)
        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(12)

        eyebrow = QLabel("GENTLE NUDGE")
        eyebrow.setObjectName("nudge_eyebrow")
        title = QLabel("Your attention is fragmenting")
        title.setObjectName("dialog_title")
        body = QLabel(
            f"{self._switches} app switches in the last 30 minutes. "
            "A short, deliberate reset can help you settle back into one task."
        )
        body.setObjectName("dialog_subtitle")
        body.setWordWrap(True)
        root.addWidget(eyebrow)
        root.addWidget(title)
        root.addWidget(body)

        hint = QLabel("The reset starts a 10-minute Focus block with your current guardrails.")
        hint.setObjectName("nudge_hint")
        hint.setWordWrap(True)
        root.addWidget(hint)

        row = QHBoxLayout()
        row.addStretch()
        later = QPushButton("Not now")
        later.setObjectName("preset_btn")
        later.setCursor(Qt.CursorShape.PointingHandCursor)
        later.clicked.connect(self.reject)
        row.addWidget(later)
        reset = QPushButton("Start 10-minute reset")
        reset.setObjectName("primary_pill_btn")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(self._start_reset)
        row.addWidget(reset)
        root.addLayout(row)

    def _start_reset(self) -> None:
        mode = self._fm.current_mode if self._fm else "custom"
        if self._fm and not self._fm.is_active:
            self._fm.start_focus(10, mode=mode)
        self.accept()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#nudge_eyebrow {{ color: #FF9F0A; font-size: 9px; font-weight: 700; letter-spacing: 1.3px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 22px; font-weight: 700; }}
            QLabel#dialog_subtitle {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#nudge_hint {{ color: {tm.color('text_muted')}; font-size: 11px; padding: 8px 10px; background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; }}
            QPushButton#preset_btn {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; color: {tm.color('text_sub')}; padding: 8px 16px; font-weight: 600; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 999px; padding: 8px 18px; font-weight: 700; }}
        """)
