"""
process_picker.py — App picker dialog for App Locker.

Two tabs:
  1. Running processes — live list of running user processes (SYSTEM_SAFE filtered)
  2. Browse executable — QFileDialog to pick a .exe directly

Selecting a process populates process_name, display_name, exe_path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import psutil
from PySide6.QtCore import Qt, QSortFilterProxyModel, QTimer, QSize
from PySide6.QtGui import QIcon, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QListView, QLineEdit, QFileDialog, QFrame, QWidget,
    QGraphicsOpacityEffect,
)
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

from protection.app_locker import SYSTEM_SAFE
from core.logger import logger


class ProcessPickerDialog(QDialog):
    """Dialog for selecting an application to add to App Locker, App Timer, or Focus Mode.

    Caller modes:
        mode="locker" -> Title: "Add Application to App Locker", Button: "Add to App Locker"
        mode="timer"  -> Title: "Add Application to App Timer", Button: "Add to App Timer"
        mode="focus"  -> Title: "Add Application to Focus Session", Button: "Add to Focus Session"

    After exec() returns Accepted, read:
        dialog.selected_process_name   (str, lowercase e.g. 'brave.exe')
        dialog.selected_display_name   (str, e.g. 'Brave Browser')
        dialog.selected_exe_path       (str, full path or '')
    """

    def __init__(
        self,
        parent=None,
        mode: str = "locker",
        action_text: Optional[str] = None,
        title_text: Optional[str] = None,
    ) -> None:
        super().__init__(
            parent,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint,
        )
        self.mode = mode.lower()
        if self.mode == "timer":
            default_title = "Add Application to App Timer"
            default_action = "Add to App Timer"
            self.browse_desc_text = "Select the application's .exe file to set a daily time limit."
        elif self.mode == "focus":
            default_title = "Add Application to Focus Session"
            default_action = "Add to Focus Session"
            self.browse_desc_text = "Select an allowed application's .exe file directly."
        else:  # "locker" or default
            default_title = "Add Application to App Locker"
            default_action = "Add to App Locker"
            self.browse_desc_text = "Select the application's .exe file directly."

        self.title_text = title_text if title_text is not None else default_title
        self.action_text = action_text if action_text is not None else default_action
        self.selected_process_name: str = ""
        self.selected_display_name: str = ""
        self.selected_exe_path: str = ""

        self.setFixedSize(520, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._opacity_eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_eff)
        self._fade_in = QPropertyAnimation(self._opacity_eff, b"opacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._setup_ui()
        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        self._refresh_process_list()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fade_in.start()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._bg = QFrame()
        self._bg.setObjectName("picker_bg")

        inner = QVBoxLayout(self._bg)
        inner.setContentsMargins(28, 24, 28, 24)
        inner.setSpacing(0)

        # Header
        hdr_row = QHBoxLayout()
        title = QLabel(self.title_text)
        title.setObjectName("picker_title")
        hdr_row.addWidget(title, 1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("picker_close_btn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.reject)
        hdr_row.addWidget(close_btn)
        inner.addLayout(hdr_row)

        inner.addSpacing(16)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setObjectName("picker_tabs")

        # ── Tab 1: Running processes ──────────────────────────────────────
        proc_tab = QWidget()
        proc_layout = QVBoxLayout(proc_tab)
        proc_layout.setContentsMargins(0, 12, 0, 0)
        proc_layout.setSpacing(10)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search applications…")
        self._search_box.setObjectName("picker_search")
        self._search_box.textChanged.connect(self._on_search)
        proc_layout.addWidget(self._search_box)

        self._model = QStandardItemModel()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setFilterKeyColumn(0)

        self._list_view = QListView()
        self._list_view.setObjectName("picker_list")
        self._list_view.setModel(self._proxy)
        self._list_view.setIconSize(QSize(24, 24))
        self._list_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self._list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_view.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._list_view.doubleClicked.connect(self._on_list_double_click)
        self._list_view.clicked.connect(self._on_list_click)
        proc_layout.addWidget(self._list_view, 1)

        refresh_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("picker_refresh_btn")
        refresh_btn.clicked.connect(self._refresh_process_list)
        refresh_row.addWidget(refresh_btn)

        refresh_row.addStretch()
        proc_layout.addLayout(refresh_row)

        self._tabs.addTab(proc_tab, "Applications")

        # ── Tab 2: Browse executable ──────────────────────────────────────
        browse_tab = QWidget()
        browse_layout = QVBoxLayout(browse_tab)
        browse_layout.setContentsMargins(0, 20, 0, 0)
        browse_layout.setSpacing(12)

        browse_desc = QLabel(self.browse_desc_text)
        browse_desc.setObjectName("picker_desc")
        browse_desc.setWordWrap(True)
        browse_layout.addWidget(browse_desc)

        self._exe_path_lbl = QLabel("No file selected.")
        self._exe_path_lbl.setObjectName("picker_exe_path")
        self._exe_path_lbl.setWordWrap(True)
        browse_layout.addWidget(self._exe_path_lbl)

        browse_btn = QPushButton("📂  Browse Executable…")
        browse_btn.setObjectName("picker_browse_btn")
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self._browse_exe)
        browse_layout.addWidget(browse_btn)
        browse_layout.addStretch()

        self._tabs.addTab(browse_tab, "Browse .exe File")

        inner.addWidget(self._tabs, 1)

        inner.addSpacing(16)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("picker_cancel_btn")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._add_btn = QPushButton(self.action_text)
        self._add_btn.setObjectName("picker_add_btn")
        self._add_btn.setMinimumHeight(36)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)
        inner.addLayout(btn_row)

        outer.addWidget(self._bg)

    # ─── Theme ───────────────────────────────────────────────────────────────

    def _apply_theme(self, is_dark: bool = True) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        scroll_handle = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.16)"
        self.setStyleSheet(f"""
            QFrame#picker_bg {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 14px;
            }}
            QLabel#picker_title {{
                font-size: 16px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#picker_desc, QLabel#picker_exe_path {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QPushButton#picker_close_btn {{
                background: transparent;
                color: {tm.color('text_muted')};
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton#picker_close_btn:hover {{
                background: rgba(255, 69, 58, 0.16);
                color: #FF453A;
            }}
            QLineEdit#picker_search {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 8px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
            }}
            QLineEdit#picker_search:focus {{
                border-color: {tm.color('accent')};
                background-color: {tm.color('surface_elevated')};
            }}
            QListView#picker_list {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_main')};
                font-size: 13px;
                padding: 4px;
                outline: none;
            }}
            QListView#picker_list::item {{
                padding: 8px 12px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListView#picker_list::item:hover {{
                background-color: {tm.color('surface_hover')};
            }}
            QListView#picker_list::item:selected {{
                background-color: {tm.color('accent_emerald_bg')};
                color: {tm.color('accent')};
                border: 1px solid {tm.color('accent_emerald_bg')};
                font-weight: 600;
            }}
            QPushButton#picker_refresh_btn {{
                background: transparent;
                color: {tm.color('accent')};
                border: none;
                font-size: 12px;
                font-weight: 700;
                padding: 4px 8px;
            }}
            QPushButton#picker_refresh_btn:hover {{
                color: {tm.color('accent_hover')};
            }}
            QPushButton#picker_browse_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 16px;
            }}
            QPushButton#picker_browse_btn:hover {{
                background-color: {tm.color('surface_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#picker_cancel_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton#picker_cancel_btn:hover {{
                background-color: {tm.color('surface_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#picker_add_btn {{
                background: {tm.color('primary_btn_gradient')};
                color: #ffffff;
                border: 1px solid {tm.color('accent')};
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#picker_add_btn:hover {{
                background: {tm.color('primary_btn_hover')};
                border-color: {tm.color('accent_hover')};
            }}
            QPushButton#picker_add_btn:disabled {{
                background: {tm.color('surface_secondary')};
                color: {tm.color('text_muted')};
                border: 1px solid {tm.color('border')};
            }}
            QTabWidget#picker_tabs::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {tm.color('text_sub')};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {tm.color('accent')};
                border-bottom: 2px solid {tm.color('accent')};
                font-weight: 700;
            }}
            QTabBar::tab:hover:!selected {{
                color: {tm.color('text_main')};
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle};
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {tm.color('accent')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                height: 0px;
                background: transparent;
            }}
        """)

    # ─── Logic ───────────────────────────────────────────────────────────────

    def _refresh_process_list(self) -> None:
        self._model.clear()
        try:
            from utils.win_utils import get_all_discoverable_applications
            from utils.icon_provider import AppIconProvider
            icon_provider = AppIconProvider()
            apps = get_all_discoverable_applications()
            for name, display, exe in apps:
                icon = icon_provider.get_icon(name, exe)
                item = QStandardItem(icon, f"{display}  ({name})")
                item.setData(name, Qt.ItemDataRole.UserRole)            # process_name
                item.setData(display, Qt.ItemDataRole.UserRole + 1)     # display_name
                item.setData(exe, Qt.ItemDataRole.UserRole + 2)         # exe_path
                self._model.appendRow(item)
        except Exception as exc:
            logger.warning("process_picker refresh error: %s", exc)

    def _on_search(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)

    def _on_list_click(self, index) -> None:
        src_idx = self._proxy.mapToSource(index)
        item = self._model.itemFromIndex(src_idx)
        if item:
            self.selected_process_name = item.data(Qt.ItemDataRole.UserRole)
            self.selected_display_name = item.data(Qt.ItemDataRole.UserRole + 1)
            self.selected_exe_path = item.data(Qt.ItemDataRole.UserRole + 2) or ""
            self._add_btn.setEnabled(True)

    def _on_list_double_click(self, index) -> None:
        self._on_list_click(index)
        if self.selected_process_name:
            self._on_add()

    def _browse_exe(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Application", "C:/Program Files", "Executables (*.exe)"
        )
        if path:
            p = Path(path)
            from utils.win_utils import is_safe_lock_target, get_executable_product_name, clean_fallback_name
            if not is_safe_lock_target(str(path), p.name):
                from PySide6.QtWidgets import QMessageBox
                target_action = "added to App Timer" if self.mode == "timer" else "locked"
                QMessageBox.warning(
                    self,
                    "Invalid Application",
                    f"This file is a protected system component, hidden file, or unsupported executable and cannot be {target_action}."
                )
                return
            self.selected_process_name = p.name.lower()
            
            display = get_executable_product_name(str(path))
            if not display:
                display = clean_fallback_name(p.name)
            self.selected_display_name = display
            self.selected_exe_path = path
            self._exe_path_lbl.setText(f"Selected: {display} ({p.name})")
            self._add_btn.setEnabled(True)

    def _on_add(self) -> None:
        if self.selected_process_name:
            self.accept()
