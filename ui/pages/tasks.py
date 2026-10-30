"""
tasks.py — Smart To-Do List Page for Digital Wellbeing.

Connects personal task planning with active system tracking:
- Tasks specify estimated time and target application/domain toolchains.
- Starting a task triggers an intentional Focus session with guardrails.
- Actual active time spent inside target applications is automatically logged.
- Calibrates task estimation accuracy over time.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.repository import Repository
from protection.focus_manager import FocusManager
from ui import design_system as ds
from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager


class TaskCreateDialog(QDialog):
    """Clean dialog to create a new Smart Task."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Smart Task")
        self.setFixedWidth(420)
        self.setObjectName("task_dialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title_lbl = QLabel("Task Title")
        title_lbl.setObjectName("field_label")
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g., Complete Biology Assignment")
        layout.addWidget(title_lbl)
        layout.addWidget(self._title_edit)

        est_row = QHBoxLayout()
        est_lbl = QLabel("Estimated Duration")
        est_lbl.setObjectName("field_label")
        self._est_spin = QSpinBox()
        self._est_spin.setRange(5, 240)
        self._est_spin.setValue(25)
        self._est_spin.setSuffix(" min")
        est_row.addWidget(est_lbl)
        est_row.addStretch()
        est_row.addWidget(self._est_spin)
        layout.addLayout(est_row)

        prio_row = QHBoxLayout()
        prio_lbl = QLabel("Priority")
        prio_lbl.setObjectName("field_label")
        self._prio_combo = QComboBox()
        self._prio_combo.addItem("High Priority", 1)
        self._prio_combo.addItem("Normal Priority", 2)
        self._prio_combo.addItem("Low Priority", 3)
        self._prio_combo.setCurrentIndex(1)
        prio_row.addWidget(prio_lbl)
        prio_row.addStretch()
        prio_row.addWidget(self._prio_combo)
        layout.addLayout(prio_row)

        target_lbl = QLabel("Target Applications (comma-separated exe)")
        target_lbl.setObjectName("field_label")
        self._target_edit = QLineEdit()
        self._target_edit.setPlaceholderText("e.g., word.exe, excel.exe, code.exe")
        layout.addWidget(target_lbl)
        layout.addWidget(self._target_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("secondary_btn")
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_create = QPushButton("Add Task")
        self._btn_create.setObjectName("primary_btn")
        self._btn_create.clicked.connect(self._on_create)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_create)
        layout.addLayout(btn_row)

        self._apply_theme()

    def _on_create(self) -> None:
        if not self._title_edit.text().strip():
            QMessageBox.warning(self, "Invalid Title", "Please enter a task title.")
            return
        self.accept()

    def get_data(self) -> dict:
        procs_raw = self._target_edit.text().split(",")
        procs = [p.strip().lower() for p in procs_raw if p.strip()]
        return {
            "title": self._title_edit.text().strip(),
            "estimated_minutes": self._est_spin.value(),
            "priority": self._prio_combo.currentData(),
            "target_processes": procs,
        }

    def _apply_theme(self) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog#task_dialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#field_label {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('text_main')};
            }}
            QLineEdit, QSpinBox, QComboBox {{
                background: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 6px 10px;
                color: {tm.color('text_main')};
                font-size: 12px;
            }}
            QPushButton#primary_btn {{
                background-color: {tm.color('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton#secondary_btn {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                color: {tm.color('text_sub')};
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
            }}
        """)


class TaskCard(QFrame):
    """Item card for a single Smart Task."""

    start_task = Signal(int)
    complete_task = Signal(int)
    delete_task = Signal(int)

    def __init__(self, task: dict, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("task_card")
        self._task = task
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Status checkbox / button
        self._btn_check = QPushButton()
        self._btn_check.setObjectName("task_check_btn")
        self._btn_check.setFixedSize(22, 22)
        self._btn_check.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        is_done = self._task.get("status") == "completed"
        if is_done:
            self._btn_check.setIcon(get_icon("check", "#34C759", 12))
        self._btn_check.clicked.connect(lambda: self.complete_task.emit(self._task["id"]))
        layout.addWidget(self._btn_check)

        # Title and details column
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        title = QLabel(self._task.get("title", ""))
        title.setObjectName("task_title_completed" if is_done else "task_title")
        text_col.addWidget(title)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)

        est_m = self._task.get("estimated_minutes", 25)
        act_s = self._task.get("actual_active_s", 0.0)
        act_m = int(act_s // 60)

        dur_lbl = QLabel(f"⏱ Est: {est_m}m · Actual: {act_m}m")
        dur_lbl.setObjectName("task_meta")
        meta_row.addWidget(dur_lbl)

        targets = self._task.get("target_processes") or []
        if targets:
            target_pill = QLabel(f"Tools: {', '.join(targets)}")
            target_pill.setObjectName("task_pill")
            meta_row.addWidget(target_pill)

        meta_row.addStretch()
        text_col.addLayout(meta_row)
        layout.addLayout(text_col, 1)

        # Actions
        if not is_done:
            self._btn_start = QPushButton("Focus ▶")
            self._btn_start.setObjectName("task_btn_start")
            self._btn_start.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._btn_start.clicked.connect(lambda: self.start_task.emit(self._task["id"]))
            layout.addWidget(self._btn_start)

        self._btn_del = QPushButton("✕")
        self._btn_del.setObjectName("task_btn_del")
        self._btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_del.clicked.connect(lambda: self.delete_task.emit(self._task["id"]))
        layout.addWidget(self._btn_del)


class TasksPage(QWidget):
    """Smart To-Do List Page."""

    request_navigate = Signal(int)

    def __init__(self, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._protection_manager = protection_manager
        self._repo = Repository()
        self._fm = FocusManager.instance()

        self._setup_ui()
        self.refresh()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("page_scroll")

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(32, 28, 32, 28)
        self._layout.setSpacing(20)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Page Header
        header = QHBoxLayout()
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        title = QLabel("Smart To-Do List")
        title.setObjectName("page_title")
        subtitle = QLabel("Task management linked to real-time process tracking and automated Focus sessions.")
        subtitle.setObjectName("page_subtitle")
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        header.addLayout(text_box, 1)

        self._btn_add = QPushButton("+ Add Smart Task")
        self._btn_add.setObjectName("accent_btn")
        self._btn_add.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_add.clicked.connect(self._open_add_dialog)
        header.addWidget(self._btn_add)
        self._layout.addLayout(header)

        # Overview KPI Card
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(14)
        self._kpi_active = self._create_kpi_card("IN-PROGRESS", "0", "clock", kpi_row)
        self._kpi_pending = self._create_kpi_card("PENDING TASKS", "0", "activity", kpi_row)
        self._kpi_completed = self._create_kpi_card("COMPLETED", "0", "sparkles", kpi_row)
        self._layout.addLayout(kpi_row)

        # Section Header
        lbl_list = QLabel("Tasks Queue")
        lbl_list.setObjectName("section_header")
        self._layout.addWidget(lbl_list)

        # Task Cards Container
        self._tasks_layout = QVBoxLayout()
        self._tasks_layout.setSpacing(10)
        self._layout.addLayout(self._tasks_layout)

        self._layout.addStretch()

    def _create_kpi_card(self, title: str, default_val: str, icon_name: str, layout: QHBoxLayout) -> QLabel:
        card = QFrame()
        card.setObjectName("v2_card")
        l = QVBoxLayout(card)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(6)

        top_h = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setObjectName("metric_hdr")
        top_h.addWidget(lbl_title)
        top_h.addStretch()

        ico = QLabel()
        ico.setPixmap(get_pixmap(icon_name, ThemeManager.instance().color("text_muted"), 15))
        top_h.addWidget(ico)
        l.addLayout(top_h)

        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val")
        l.addWidget(lbl_val)

        layout.addWidget(card, 1)
        return lbl_val

    def _sync_notch(self) -> None:
        main_win = self.window()
        if main_win and hasattr(main_win, "sync_ambient_notch"):
            main_win.sync_ambient_notch()

    def _open_add_dialog(self) -> None:
        dialog = TaskCreateDialog(self.window())
        if dialog.exec():
            data = dialog.get_data()
            self._repo.add_smart_task(
                title=data["title"],
                priority=data["priority"],
                estimated_minutes=data["estimated_minutes"],
                target_processes=data["target_processes"],
            )
            self.refresh()
            self._sync_notch()

    def refresh(self) -> None:
        # Clear existing cards
        while self._tasks_layout.count():
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = self._repo.get_smart_tasks()
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        in_prog = sum(1 for t in tasks if t.get("status") == "in_progress")
        completed = sum(1 for t in tasks if t.get("status") == "completed")

        self._kpi_active.setText(str(in_prog))
        self._kpi_pending.setText(str(pending))
        self._kpi_completed.setText(str(completed))

        if not tasks:
            empty = QLabel("No tasks in your queue.\nClick '+ Add Smart Task' to link your goals with Focus guardrails.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("empty_state_lbl")
            self._tasks_layout.addWidget(empty)
            return

        for task in tasks:
            card = TaskCard(task)
            card.start_task.connect(self._on_start_task)
            card.complete_task.connect(self._on_complete_task)
            card.delete_task.connect(self._on_delete_task)
            self._tasks_layout.addWidget(card)

    def _on_start_task(self, task_id: int) -> None:
        # Set task in_progress
        self._repo.update_smart_task_status(task_id, "in_progress")
        task = self._repo.get_smart_task(task_id)
        if task:
            mins = task.get("estimated_minutes", 25)
            # Launch focus session matching task duration
            self._fm.start_focus(minutes=mins)
        self.refresh()
        self._sync_notch()

    def _on_complete_task(self, task_id: int) -> None:
        task = self._repo.get_smart_task(task_id)
        if task:
            new_status = "pending" if task.get("status") == "completed" else "completed"
            self._repo.update_smart_task_status(task_id, new_status)
        self.refresh()
        self._sync_notch()

    def _on_delete_task(self, task_id: int) -> None:
        self._repo.delete_smart_task(task_id)
        self.refresh()
        self._sync_notch()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 26px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle {{ font-size: 13px; color: {tm.color('text_sub')}; }}
            QLabel#section_header {{ font-size: 11px; font-weight: 700; color: {tm.color('text_muted')}; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px; }}
            QPushButton#accent_btn {{
                background-color: {tm.color('accent')};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton#accent_btn:hover {{ background-color: {tm.color('accent_hover')}; }}
            QFrame#v2_card {{ background-color: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; }}
            QLabel#metric_hdr {{ color: {tm.color('text_muted')}; font-size: 10px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; }}
            QLabel#metric_val {{ font-size: 20px; font-weight: 700; color: {tm.color('text_main')}; }}
            QFrame#task_card {{
                background-color: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
            }}
            QFrame#task_card:hover {{
                background-color: {tm.color('card_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QLabel#task_title {{ font-size: 14px; font-weight: 600; color: {tm.color('text_main')}; }}
            QLabel#task_title_completed {{ font-size: 14px; font-weight: 600; color: {tm.color('text_muted')}; text-decoration: line-through; }}
            QLabel#task_meta {{ font-size: 11px; color: {tm.color('text_sub')}; }}
            QLabel#task_pill {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
                color: {tm.color('text_sub')};
            }}
            QPushButton#task_check_btn {{
                background: {tm.color('surface_secondary')};
                border: 1.5px solid {tm.color('border')};
                border-radius: 6px;
            }}
            QPushButton#task_btn_start {{
                background-color: {tm.color('accent_tint_bg')};
                border: 1px solid {tm.color('accent_tint_border')};
                border-radius: 8px;
                color: {tm.color('accent')};
                font-weight: 700;
                font-size: 11px;
                padding: 6px 12px;
            }}
            QPushButton#task_btn_del {{
                background: transparent;
                border: none;
                color: {tm.color('text_muted')};
                font-size: 12px;
                padding: 4px;
            }}
            QPushButton#task_btn_del:hover {{ color: #FF453A; }}
            QLabel#empty_state_lbl {{
                font-size: 13px;
                color: {tm.color('text_sub')};
                padding: 40px;
                line-height: 1.6;
            }}
        """)
