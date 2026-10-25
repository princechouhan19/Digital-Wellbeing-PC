"""
command_palette.py — Spotlight-style quick actions (Ctrl+K).

The palette is deliberately small: it exposes navigation, Focus starts,
schedules, URL rules, the weekly report, and the last session recap.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from ui.theme import ThemeManager

Command = Tuple[str, str, Callable[[], None]]


class CommandPalette(QDialog):
    def __init__(self, commands: List[Command], parent=None) -> None:
        super().__init__(parent)
        self._commands = commands
        self._selected_callback = None
        self.setWindowTitle("Quick actions")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self._setup_ui()
        self._populate("")
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(8)

        self._input = QLineEdit()
        self._input.setObjectName("palette_input")
        self._input.setPlaceholderText("Search actions…  (Esc to close)")
        self._input.textChanged.connect(self._populate)
        self._input.returnPressed.connect(self._accept_current)
        root.addWidget(self._input)

        frame = QFrame()
        frame.setObjectName("palette_frame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.setObjectName("palette_list")
        self._list.itemActivated.connect(lambda _: self._accept_current())
        frame_layout.addWidget(self._list)
        root.addWidget(frame, 1)

        hint = QLabel("↑ ↓ to navigate    ↵ to run    Esc to close")
        hint.setObjectName("palette_hint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(hint)

        self._input.setFocus()

    def _populate(self, text: str) -> None:
        query = (text or "").strip().lower()
        self._list.clear()
        for title, subtitle, callback in self._commands:
            haystack = f"{title} {subtitle}".lower()
            if query and query not in haystack:
                continue
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, callback)
            item.setData(Qt.ItemDataRole.UserRole + 1, subtitle)
            item.setToolTip(subtitle)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _accept_current(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self._selected_callback = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

    def selected_callback(self):
        return self._selected_callback

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; border: 1px solid {tm.color('border_strong')}; border-radius: 18px; }}
            QLineEdit#palette_input {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; color: {tm.color('text_main')}; padding: 10px 13px; font-size: 14px; }}
            QFrame#palette_frame {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; }}
            QListWidget#palette_list {{ background: transparent; border: none; outline: none; color: {tm.color('text_main')}; font-size: 13px; }}
            QListWidget#palette_list::item {{ padding: 9px 12px; border-radius: 8px; }}
            QListWidget#palette_list::item:selected {{ background: {tm.color('accent_tint_bg')}; color: {tm.color('accent_tint_text')}; }}
            QLabel#palette_hint {{ color: {tm.color('text_muted')}; font-size: 10px; }}
        """)
