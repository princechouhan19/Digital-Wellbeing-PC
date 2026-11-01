"""
tasks.py — Smart Routine & Tasks Page for Digital Wellbeing.

Features:
- Strict Start & End Time scheduling (e.g. 5:50 PM – 7:00 PM).
- Pre-filled editable template presets (Gym, College/Lecture, Bath, Sleep, Coding).
- Weekday repeat selector (M, T, W, Th, F, Sa, Su).
- Per-day custom notes matrix (e.g. Mon Chest+Bi, Tue Back+Tri, or Lecture project notes).
- Apple Design System analytics:
  * DailyActivityRingWidget (circular completion %)
  * MonthlyTrendLineGraphWidget (Apple Health-style 30-day spline)
  * WaterIntakeWidget (hydration with 0.5L and 1.0L checkpoints)
- Direct editing of existing tasks.
- Target application selection without manual typing.
- Real-time synchronization with Dynamic Island.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import List, Optional

import psutil
from PySide6.QtCore import Qt, Signal, QTime
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.repository import Repository
from protection.focus_manager import FocusManager
from ui import design_system as ds
from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager
from ui.widgets.process_picker import ProcessPickerDialog
from ui.widgets.apple_task_charts import (
    DailyActivityRingWidget,
    MonthlyTrendLineGraphWidget,
    WaterIntakeWidget,
)

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_SHORT = ["M", "T", "W", "T", "F", "S", "S"]


class TaskEditDialog(QDialog):
    """Dialog to create or edit a Smart Task with strict scheduling, weekday repeats, and day notes."""

    def __init__(self, parent=None, task: Optional[dict] = None) -> None:
        super().__init__(parent)
        self._task = task
        self.is_edit_mode = task is not None
        self.setWindowTitle("Edit Task" if self.is_edit_mode else "New Smart Task")
        self.setMinimumWidth(680)
        self.setMinimumHeight(640)
        self.resize(700, 720)
        self.setObjectName("task_dialog")

        self._selected_apps: List[dict] = []
        self._day_buttons: List[QPushButton] = []
        self._day_note_edits: List[QLineEdit] = []

        self._setup_ui()
        if self._task:
            self._load_existing_task()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_w = QWidget()
        content_w.setObjectName("dialog_content")
        layout = QVBoxLayout(content_w)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        scroll.setWidget(content_w)
        outer_layout.addWidget(scroll, 1)

        # 0. Quick Preset Templates Bar (Only shown in creation mode)
        if not self.is_edit_mode:
            tpl_box = QVBoxLayout()
            tpl_box.setSpacing(4)
            tpl_hdr = QLabel("QUICK ROUTINE PRESETS")
            tpl_hdr.setObjectName("section_mini_hdr")
            tpl_box.addWidget(tpl_hdr)

            tpl_row = QHBoxLayout()
            tpl_row.setSpacing(6)
            templates = [
                ("🏋️‍♂️ Gym", self._apply_gym_template),
                ("📚 College", self._apply_college_template),
                ("🚿 Bath", self._apply_bath_template),
                ("💻 Coding", self._apply_coding_template),
                ("😴 Sleep", self._apply_sleep_template),
            ]
            for label, fn in templates:
                btn = QPushButton(label)
                btn.setObjectName("template_chip")
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn.clicked.connect(fn)
                tpl_row.addWidget(btn)
            tpl_row.addStretch()
            tpl_box.addLayout(tpl_row)
            layout.addLayout(tpl_box)

        # 1. Task Title & Category
        title_cat_row = QHBoxLayout()
        title_cat_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_lbl = QLabel("Task Title")
        title_lbl.setObjectName("field_label")
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g., Gym Session, Instagram Backend Lecture")
        title_col.addWidget(title_lbl)
        title_col.addWidget(self._title_edit)
        title_cat_row.addLayout(title_col, 3)

        cat_col = QVBoxLayout()
        cat_col.setSpacing(4)
        cat_lbl = QLabel("Category")
        cat_lbl.setObjectName("field_label")
        self._cat_combo = QComboBox()
        self._cat_combo.addItems(["Health", "Study", "Work", "Routine", "Personal", "Other"])
        self._cat_combo.setMinimumWidth(130)
        cat_col.addWidget(cat_lbl)
        cat_col.addWidget(self._cat_combo)
        title_cat_row.addLayout(cat_col, 1)

        layout.addLayout(title_cat_row)

        # 2. Strict Start & End Time Scheduling
        sched_group = QGroupBox("Strict Time Window (Start & End Time)")
        sched_group.setObjectName("sched_group")
        sched_layout = QVBoxLayout(sched_group)
        sched_layout.setContentsMargins(14, 12, 14, 12)
        sched_layout.setSpacing(10)

        time_hdr = QHBoxLayout()
        self._time_check = QCheckBox("Enforce Strict Time Window")
        self._time_check.setObjectName("field_check")
        self._time_check.setChecked(True)
        self._time_check.toggled.connect(self._on_time_toggled)
        time_hdr.addWidget(self._time_check)
        time_hdr.addStretch()
        sched_layout.addLayout(time_hdr)

        times_row = QHBoxLayout()
        times_row.setSpacing(12)

        start_col = QVBoxLayout()
        start_col.setSpacing(3)
        start_col.addWidget(QLabel("Start Time", styleSheet="color: #8E8E93; font-size: 11px;"))
        self._start_edit = QTimeEdit()
        self._start_edit.setDisplayFormat("h:mm AP")
        self._start_edit.setTime(QTime(17, 50))  # Default 5:50 PM
        self._start_edit.timeChanged.connect(self._on_times_changed)
        start_col.addWidget(self._start_edit)
        times_row.addLayout(start_col, 2)

        arrow_lbl = QLabel("➔")
        arrow_lbl.setStyleSheet("color: #8E8E93; font-size: 14px; margin-top: 14px;")
        arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        times_row.addWidget(arrow_lbl)

        end_col = QVBoxLayout()
        end_col.setSpacing(3)
        end_col.addWidget(QLabel("End Time", styleSheet="color: #8E8E93; font-size: 11px;"))
        self._end_edit = QTimeEdit()
        self._end_edit.setDisplayFormat("h:mm AP")
        self._end_edit.setTime(QTime(19, 0))  # Default 7:00 PM
        self._end_edit.timeChanged.connect(self._on_times_changed)
        end_col.addWidget(self._end_edit)
        times_row.addLayout(end_col, 2)

        dur_col = QVBoxLayout()
        dur_col.setSpacing(3)
        dur_col.addWidget(QLabel("Duration", styleSheet="color: #8E8E93; font-size: 11px;"))
        self._est_spin = QSpinBox()
        self._est_spin.setRange(5, 720)
        self._est_spin.setValue(70)
        self._est_spin.setSuffix(" min")
        self._est_spin.setMinimumWidth(95)
        dur_col.addWidget(self._est_spin)
        times_row.addLayout(dur_col, 1)

        sched_layout.addLayout(times_row)
        layout.addWidget(sched_group)

        # 3. Weekly Repeat Day Selector (M, T, W, Th, F, Sa, Su)
        repeat_group = QGroupBox("Weekly Schedule (Repeat Days)")
        repeat_group.setObjectName("sched_group")
        repeat_layout = QVBoxLayout(repeat_group)
        repeat_layout.setContentsMargins(14, 12, 14, 12)
        repeat_layout.setSpacing(10)

        days_row = QHBoxLayout()
        days_row.setSpacing(6)
        for i in range(7):
            btn = QPushButton(f"{DAY_SHORT[i]}\n{DAY_LABELS[i]}")
            btn.setObjectName("day_pill_btn")
            btn.setCheckable(True)
            btn.setChecked(i < 6)  # Default Mon-Sat
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(0)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.toggled.connect(self._on_day_toggled)
            self._day_buttons.append(btn)
            days_row.addWidget(btn)
        repeat_layout.addLayout(days_row)

        # Quick preset buttons for days
        quick_days = QHBoxLayout()
        quick_days.setSpacing(6)
        presets_days = [
            ("Every Day", lambda: self._set_days([0, 1, 2, 3, 4, 5, 6])),
            ("Mon – Fri", lambda: self._set_days([0, 1, 2, 3, 4])),
            ("Mon – Sat", lambda: self._set_days([0, 1, 2, 3, 4, 5])),
            ("Weekends", lambda: self._set_days([5, 6])),
            ("Clear", lambda: self._set_days([])),
        ]
        for p_name, p_cb in presets_days:
            pb = QPushButton(p_name)
            pb.setObjectName("quick_day_chip")
            pb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            pb.clicked.connect(p_cb)
            quick_days.addWidget(pb)
        quick_days.addStretch()
        repeat_layout.addLayout(quick_days)

        layout.addWidget(repeat_group)

        # 4. Per-Day Specific Routine / Notes Matrix (Organized 2-Column Grid)
        notes_group = QGroupBox("Day-Specific Routine / Lecture Notes (Optional)")
        notes_group.setObjectName("sched_group")
        self._notes_layout = QVBoxLayout(notes_group)
        self._notes_layout.setContentsMargins(14, 12, 14, 12)
        self._notes_layout.setSpacing(8)

        grid_notes = QGridLayout()
        grid_notes.setHorizontalSpacing(14)
        grid_notes.setVerticalSpacing(8)

        default_gym_notes = [
            "Chest + Biceps + Forearms",
            "Back + Triceps + Traps",
            "Shoulder + Legs + Abs",
            "Active Recovery / Cardio",
            "Chest + Back Supersets",
            "Arms + Core Focus",
            "Full Rest & Mobility",
        ]
        for i, day in enumerate(DAY_LABELS):
            row_box = QHBoxLayout()
            row_box.setSpacing(6)
            lbl = QLabel(day)
            lbl.setFixedWidth(32)
            lbl.setStyleSheet("font-weight: 700; color: #0A84FF; font-size: 11px;")
            edit = QLineEdit()
            edit.setPlaceholderText(f"{day}: e.g. {default_gym_notes[i]}")
            self._day_note_edits.append(edit)
            row_box.addWidget(lbl)
            row_box.addWidget(edit, 1)

            r = i // 2
            c = i % 2
            if i == 6:  # Sunday spans both columns
                grid_notes.addLayout(row_box, r, 0, 1, 2)
            else:
                grid_notes.addLayout(row_box, r, c)

        self._notes_layout.addLayout(grid_notes)
        layout.addWidget(notes_group)

        # 5. Priority
        prio_row = QHBoxLayout()
        prio_lbl = QLabel("Priority Level")
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

        # 6. Target Application Selector (visual picker)
        target_box = QVBoxLayout()
        target_box.setSpacing(6)
        target_lbl = QLabel("Target Applications (Choose from list)")
        target_lbl.setObjectName("field_label")
        target_box.addWidget(target_lbl)

        self._chips_container = QWidget()
        self._chips_layout = QHBoxLayout(self._chips_container)
        self._chips_layout.setContentsMargins(0, 0, 0, 0)
        self._chips_layout.setSpacing(6)
        self._chips_layout.addStretch()
        target_box.addWidget(self._chips_container)

        app_picker_row = QHBoxLayout()
        app_picker_row.setSpacing(8)

        self._quick_apps_combo = QComboBox()
        self._quick_apps_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._populate_quick_apps()
        app_picker_row.addWidget(self._quick_apps_combo, 1)

        btn_add_quick = QPushButton("+ Add")
        btn_add_quick.setObjectName("secondary_btn")
        btn_add_quick.clicked.connect(self._on_add_quick_app)
        app_picker_row.addWidget(btn_add_quick)

        self._btn_browse_app = QPushButton("App List 🗂")
        self._btn_browse_app.setObjectName("secondary_btn")
        self._btn_browse_app.clicked.connect(self._open_process_picker)
        app_picker_row.addWidget(self._btn_browse_app)

        target_box.addLayout(app_picker_row)
        layout.addLayout(target_box)

        # 7. Fixed Action Footer (Always visible)
        footer = QWidget()
        footer.setObjectName("dialog_footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 14)
        footer_layout.setSpacing(12)
        footer_layout.addStretch()

        self._btn_cancel = QPushButton("Cancel")
        self._btn_cancel.setObjectName("secondary_btn")
        self._btn_cancel.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_cancel.clicked.connect(self.reject)

        btn_title = "Save Changes" if self.is_edit_mode else "Create Smart Task"
        self._btn_save = QPushButton(btn_title)
        self._btn_save.setObjectName("primary_btn")
        self._btn_save.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_save.clicked.connect(self._on_save)

        footer_layout.addWidget(self._btn_cancel)
        footer_layout.addWidget(self._btn_save)
        outer_layout.addWidget(footer)

        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet("""
            QDialog#task_dialog {
                background-color: #161618;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
            QWidget#dialog_footer {
                background-color: #1a1a1e;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLabel#field_label {
                font-size: 12px;
                font-weight: 700;
                color: #FFFFFF;
            }
            QLabel#section_mini_hdr {
                font-size: 10px;
                font-weight: 700;
                color: #8E8E93;
                letter-spacing: 1px;
            }
            QGroupBox#sched_group {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
                color: #8E8E93;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox#sched_group::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QLineEdit, QSpinBox, QComboBox, QTimeEdit {
                background: #202024;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus, QTimeEdit:focus {
                border-color: #0A84FF;
            }
            QPushButton#template_chip {
                background: rgba(10, 132, 255, 0.12);
                border: 1px solid rgba(10, 132, 255, 0.3);
                border-radius: 7px;
                padding: 5px 10px;
                font-size: 11px;
                font-weight: 600;
                color: #0A84FF;
            }
            QPushButton#template_chip:hover {
                background: rgba(10, 132, 255, 0.22);
            }
            QPushButton#day_pill_btn {
                background: #202024;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px 2px;
                font-size: 11px;
                font-weight: 700;
                color: #8E8E93;
            }
            QPushButton#day_pill_btn:checked {
                background: #0A84FF;
                border-color: #0A84FF;
                color: #FFFFFF;
            }
            QPushButton#quick_day_chip {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                color: #8E8E93;
            }
            QPushButton#quick_day_chip:hover {
                color: #0A84FF;
                border-color: rgba(10, 132, 255, 0.3);
            }
            QFrame#app_chip {
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 7px;
            }
            QLabel#chip_text {
                font-size: 11px;
                font-weight: 600;
                color: #0A84FF;
            }
            QPushButton#chip_del_btn {
                background: transparent;
                border: none;
                color: #0A84FF;
                font-size: 10px;
            }
            QPushButton#primary_btn {
                background-color: #0A84FF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton#primary_btn:hover {
                background-color: #0071E3;
            }
            QPushButton#secondary_btn {
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #8E8E93;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 12px;
            }
        """)

    # ── Presets Handler ───────────────────────────────────────────────────────

    def _apply_gym_template(self) -> None:
        self._title_edit.setText("Gym Session")
        self._cat_combo.setCurrentText("Health")
        self._start_edit.setTime(QTime(17, 50))  # 5:50 PM
        self._end_edit.setTime(QTime(19, 0))    # 7:00 PM
        self._set_days([0, 1, 2, 3, 4, 5])      # Mon - Sat
        splits = [
            "Chest + Biceps + Forearms",
            "Back + Triceps + Traps",
            "Shoulder + Legs + Abs",
            "Active Recovery / Cardio",
            "Chest + Back Supersets",
            "Arms + Core Focus",
            "Full Rest & Mobility",
        ]
        for i, sp in enumerate(splits):
            self._day_note_edits[i].setText(sp)
        self._add_app_chip("spotify.exe", "Spotify")

    def _apply_college_template(self) -> None:
        self._title_edit.setText("College Lectures & Labs")
        self._cat_combo.setCurrentText("Study")
        self._start_edit.setTime(QTime(9, 0))   # 9:00 AM
        self._end_edit.setTime(QTime(16, 0))   # 4:00 PM
        self._set_days([0, 1, 2, 3, 4])        # Mon - Fri
        topics = [
            "Project 1 Backend (Instagram API)",
            "Frontend UI (Spotify player)",
            "Data Structures & Algorithms",
            "Database Systems & SQL",
            "Lab Work & Assignments",
            "",
            "",
        ]
        for i, tp in enumerate(topics):
            self._day_note_edits[i].setText(tp)
        self._add_app_chip("code.exe", "Visual Studio Code")
        self._add_app_chip("chrome.exe", "Google Chrome")

    def _apply_bath_template(self) -> None:
        self._title_edit.setText("Bath & Morning Reset")
        self._cat_combo.setCurrentText("Routine")
        self._start_edit.setTime(QTime(8, 0))
        self._end_edit.setTime(QTime(8, 30))
        self._set_days([0, 1, 2, 3, 4, 5, 6])
        for edit in self._day_note_edits:
            edit.setText("Cold shower & morning grooming")

    def _apply_sleep_template(self) -> None:
        self._title_edit.setText("Sleep & Night Recovery")
        self._cat_combo.setCurrentText("Health")
        self._start_edit.setTime(QTime(22, 30))
        self._end_edit.setTime(QTime(6, 30))
        self._set_days([0, 1, 2, 3, 4, 5, 6])
        for edit in self._day_note_edits:
            edit.setText("No blue light screen 30m before bed")

    def _apply_coding_template(self) -> None:
        self._title_edit.setText("Deep Work Coding Block")
        self._cat_combo.setCurrentText("Work")
        self._start_edit.setTime(QTime(14, 0))
        self._end_edit.setTime(QTime(16, 0))
        self._set_days([0, 1, 2, 3, 4])
        self._add_app_chip("code.exe", "Visual Studio Code")

    # ── Days & Times Handlers ────────────────────────────────────────────────

    def _on_time_toggled(self, checked: bool) -> None:
        self._start_edit.setEnabled(checked)
        self._end_edit.setEnabled(checked)
        self._est_spin.setEnabled(checked)

    def _on_times_changed(self) -> None:
        s = self._start_edit.time()
        e = self._end_edit.time()
        s_mins = s.hour() * 60 + s.minute()
        e_mins = e.hour() * 60 + e.minute()
        diff = e_mins - s_mins
        if diff < 0:
            diff += 24 * 60  # Crosses midnight
        if diff > 0:
            self._est_spin.setValue(diff)

    def _set_days(self, days: List[int]) -> None:
        for i, btn in enumerate(self._day_buttons):
            btn.setChecked(i in days)

    def _on_day_toggled(self) -> None:
        for i, btn in enumerate(self._day_buttons):
            is_active = btn.isChecked()
            self._day_note_edits[i].setEnabled(is_active)

    # ── App Picker ───────────────────────────────────────────────────────────

    def _populate_quick_apps(self) -> None:
        self._quick_apps_combo.clear()
        self._quick_apps_combo.addItem("Select from detected apps...", None)
        seen = set()
        presets = [
            ("Google Chrome", "chrome.exe"),
            ("Visual Studio Code", "code.exe"),
            ("Microsoft Edge", "msedge.exe"),
            ("Spotify", "spotify.exe"),
            ("Microsoft Word", "winword.exe"),
            ("Microsoft Excel", "excel.exe"),
            ("Notion", "notion.exe"),
            ("Discord", "discord.exe"),
        ]
        try:
            for p in psutil.process_iter(['name']):
                name = (p.info.get('name') or '').strip().lower()
                if name.endswith(".exe") and name not in seen:
                    if name not in ("svchost.exe", "system", "csrss.exe", "services.exe"):
                        self._quick_apps_combo.addItem(f"{name[:-4].capitalize()} ({name})", name)
                        seen.add(name)
        except Exception:
            pass
        for label, proc in presets:
            if proc.lower() not in seen:
                self._quick_apps_combo.addItem(f"{label} ({proc})", proc.lower())
                seen.add(proc.lower())

    def _on_add_quick_app(self) -> None:
        proc = self._quick_apps_combo.currentData()
        if not proc:
            return
        text = self._quick_apps_combo.currentText().split(" (")[0]
        self._add_app_chip(proc, text)

    def _open_process_picker(self) -> None:
        dialog = ProcessPickerDialog(self, mode="task", title_text="Select Target Application", action_text="Select Application")
        if dialog.exec():
            proc = dialog.selected_process_name
            name = dialog.selected_display_name or proc
            if proc:
                self._add_app_chip(proc, name)

    def _add_app_chip(self, proc: str, name: str) -> None:
        proc = proc.lower()
        if any(a["proc"] == proc for a in self._selected_apps):
            return
        self._selected_apps.append({"proc": proc, "name": name})
        self._render_chips()

    def _remove_app_chip(self, proc: str) -> None:
        self._selected_apps = [a for a in self._selected_apps if a["proc"] != proc]
        self._render_chips()

    def _render_chips(self) -> None:
        while self._chips_layout.count():
            item = self._chips_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for app in self._selected_apps:
            chip = QFrame()
            chip.setObjectName("app_chip")
            cl = QHBoxLayout(chip)
            cl.setContentsMargins(8, 3, 8, 3)
            cl.setSpacing(6)
            lbl = QLabel(app["name"])
            lbl.setObjectName("chip_text")
            cl.addWidget(lbl)
            btn_del = QPushButton("✕")
            btn_del.setObjectName("chip_del_btn")
            btn_del.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            p_val = app["proc"]
            btn_del.clicked.connect(lambda _, p=p_val: self._remove_app_chip(p))
            cl.addWidget(btn_del)
            self._chips_layout.addWidget(chip)
        self._chips_layout.addStretch()

    # ── Edit Mode Loader ─────────────────────────────────────────────────────

    def _load_existing_task(self) -> None:
        t = self._task
        self._title_edit.setText(t.get("title", ""))
        self._cat_combo.setCurrentText(t.get("category", "General"))
        self._est_spin.setValue(t.get("estimated_minutes", 25))
        
        prio = t.get("priority", 2)
        idx = self._prio_combo.findData(prio)
        if idx >= 0:
            self._prio_combo.setCurrentIndex(idx)

        # Start and end times
        s_time_str = t.get("start_time") or t.get("scheduled_time")
        if s_time_str:
            parsed_s = QTime.fromString(s_time_str, "h:mm AP")
            if parsed_s.isValid():
                self._start_edit.setTime(parsed_s)
        
        e_time_str = t.get("end_time")
        if e_time_str:
            parsed_e = QTime.fromString(e_time_str, "h:mm AP")
            if parsed_e.isValid():
                self._end_edit.setTime(parsed_e)

        # Repeat days
        rep_days = t.get("repeat_days", [])
        if rep_days:
            self._set_days(rep_days)

        # Day notes
        day_notes = t.get("day_notes_json", {})
        for i in range(7):
            val = day_notes.get(str(i), "")
            self._day_note_edits[i].setText(val)

        # Target processes
        for p in t.get("target_processes", []):
            self._add_app_chip(p, p.capitalize())

    def _on_save(self) -> None:
        if not self._title_edit.text().strip():
            QMessageBox.warning(self, "Invalid Title", "Please enter a task title.")
            return
        self.accept()

    def get_data(self) -> dict:
        s_time = self._start_edit.time().toString("h:mm AP") if self._time_check.isChecked() else ""
        e_time = self._end_edit.time().toString("h:mm AP") if self._time_check.isChecked() else ""
        sched_label = f"{s_time} – {e_time}" if (s_time and e_time) else s_time

        active_days = [i for i, b in enumerate(self._day_buttons) if b.isChecked()]
        day_notes = {}
        for i, ed in enumerate(self._day_note_edits):
            txt = ed.text().strip()
            if txt:
                day_notes[str(i)] = txt

        return {
            "title": self._title_edit.text().strip(),
            "category": self._cat_combo.currentText(),
            "priority": self._prio_combo.currentData(),
            "estimated_minutes": self._est_spin.value(),
            "start_time": s_time,
            "end_time": e_time,
            "scheduled_time": sched_label,
            "repeat_days": active_days,
            "day_notes_json": day_notes,
            "target_processes": [a["proc"] for a in self._selected_apps],
        }


# Maintain backward compatibility alias
TaskCreateDialog = TaskEditDialog


class TaskCard(QFrame):
    """Item card for a single Smart Task with day note display, time range, and edit action."""

    start_task = Signal(int)
    complete_task = Signal(int)
    edit_task = Signal(int)
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

        # Status checkbox button
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
        text_col.setSpacing(4)

        # Header: Title + Category pill
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel(self._task.get("title", ""))
        title.setObjectName("task_title_completed" if is_done else "task_title")
        title_row.addWidget(title)

        cat = self._task.get("category", "General")
        cat_badge = QLabel(cat.upper())
        cat_badge.setObjectName("task_cat_badge")
        title_row.addWidget(cat_badge)
        title_row.addStretch()
        text_col.addLayout(title_row)

        # Meta row: Strict Time Window + Repeat Days Pills
        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)

        sched_time = self._task.get("scheduled_time") or self._task.get("start_time")
        if sched_time:
            time_pill = QLabel(f"🕒 {sched_time}")
            time_pill.setObjectName("task_time_pill")
            meta_row.addWidget(time_pill)

        # Repeat days mini pills
        repeat_days = self._task.get("repeat_days") or []
        if repeat_days:
            days_w = QWidget()
            dh = QHBoxLayout(days_w)
            dh.setContentsMargins(0, 0, 0, 0)
            dh.setSpacing(3)
            today_idx = datetime.now().weekday()
            for idx, short_name in enumerate(DAY_SHORT):
                d_lbl = QLabel(short_name)
                if idx in repeat_days:
                    if idx == today_idx:
                        d_lbl.setStyleSheet("color: #FFFFFF; background: #0A84FF; border-radius: 4px; padding: 1px 4px; font-weight: 800; font-size: 9px;")
                    else:
                        d_lbl.setStyleSheet("color: #0A84FF; background: rgba(10, 132, 255, 0.15); border-radius: 4px; padding: 1px 4px; font-weight: 700; font-size: 9px;")
                else:
                    d_lbl.setStyleSheet("color: #555555; font-size: 9px;")
                dh.addWidget(d_lbl)
            meta_row.addWidget(days_w)

        est_m = self._task.get("estimated_minutes", 25)
        dur_lbl = QLabel(f"⏱ {est_m}m")
        dur_lbl.setObjectName("task_meta")
        meta_row.addWidget(dur_lbl)

        targets = self._task.get("target_processes") or []
        if targets:
            target_pill = QLabel(f"Tools: {', '.join(targets)}")
            target_pill.setObjectName("task_pill")
            meta_row.addWidget(target_pill)

        meta_row.addStretch()
        text_col.addLayout(meta_row)

        # Today's Specific Note (e.g. Chest + Biceps or Lecture topic)
        today_idx = str(datetime.now().weekday())
        day_notes = self._task.get("day_notes_json") or {}
        today_note = day_notes.get(today_idx)
        if today_note:
            note_row = QHBoxLayout()
            note_row.setSpacing(6)
            day_name = DAY_LABELS[datetime.now().weekday()]
            note_lbl = QLabel(f"📌 Today ({day_name}): {today_note}")
            note_lbl.setObjectName("task_today_note")
            note_row.addWidget(note_lbl)
            note_row.addStretch()
            text_col.addLayout(note_row)

        layout.addLayout(text_col, 1)

        # Actions: Edit, Focus, Delete
        if not is_done:
            self._btn_edit = QPushButton("✏")
            self._btn_edit.setObjectName("task_btn_edit")
            self._btn_edit.setToolTip("Edit Task")
            self._btn_edit.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._btn_edit.clicked.connect(lambda: self.edit_task.emit(self._task["id"]))
            layout.addWidget(self._btn_edit)

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
    """Smart Routine & Tasks Page."""

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

        # 1. Page Header
        header = QHBoxLayout()
        text_box = QVBoxLayout()
        text_box.setSpacing(3)
        title = QLabel("Smart Routine & Tasks")
        title.setObjectName("page_title")
        subtitle = QLabel("Strict time scheduling, per-day routines, hydration tracking, and Dynamic Island synchronization.")
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

        # 2. Apple Design System Visual Analytics Grid
        analytics_card = QFrame()
        analytics_card.setObjectName("analytics_container")
        analytics_layout = QHBoxLayout(analytics_card)
        analytics_layout.setContentsMargins(20, 16, 20, 16)
        analytics_layout.setSpacing(20)

        # A. Daily Activity Ring
        ring_col = QVBoxLayout()
        ring_col.setSpacing(6)
        ring_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ring_widget = DailyActivityRingWidget()
        ring_col.addWidget(self._ring_widget)
        ring_lbl = QLabel("TODAY'S COMPLETION")
        ring_lbl.setObjectName("analytics_hdr")
        ring_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ring_col.addWidget(ring_lbl)
        analytics_layout.addLayout(ring_col)

        # Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        analytics_layout.addWidget(div1)

        # B. Monthly Consistency Line Graph
        trend_col = QVBoxLayout()
        trend_col.setSpacing(8)
        trend_hdr = QLabel("30-DAY COMPLETION CONSISTENCY")
        trend_hdr.setObjectName("analytics_hdr")
        trend_col.addWidget(trend_hdr)
        self._trend_graph = MonthlyTrendLineGraphWidget()
        trend_col.addWidget(self._trend_graph)
        analytics_layout.addLayout(trend_col, 2)

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        analytics_layout.addWidget(div2)

        # C. Water Intake Tracker
        self._water_widget = WaterIntakeWidget(self._repo)
        analytics_layout.addWidget(self._water_widget, 1)

        self._layout.addWidget(analytics_card)

        # 3. Tasks Queue Section Header
        lbl_list = QLabel("Tasks & Routine Schedule")
        lbl_list.setObjectName("section_header")
        self._layout.addWidget(lbl_list)

        # Container for task cards
        self._tasks_layout = QVBoxLayout()
        self._tasks_layout.setSpacing(10)
        self._layout.addLayout(self._tasks_layout)

        self._layout.addStretch()

    def _sync_notch(self) -> None:
        main_win = self.window()
        if main_win and hasattr(main_win, "sync_ambient_notch"):
            main_win.sync_ambient_notch()

    def _open_add_dialog(self) -> None:
        dialog = TaskEditDialog(self.window())
        if dialog.exec():
            data = dialog.get_data()
            self._repo.add_smart_task(
                title=data["title"],
                category=data["category"],
                priority=data["priority"],
                estimated_minutes=data["estimated_minutes"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                scheduled_time=data["scheduled_time"],
                repeat_days=data["repeat_days"],
                day_notes_json=data["day_notes_json"],
                target_processes=data["target_processes"],
            )
            self.refresh()
            self._sync_notch()

    def _on_edit_task(self, task_id: int) -> None:
        task = self._repo.get_smart_task(task_id)
        if not task:
            return
        dialog = TaskEditDialog(self.window(), task=task)
        if dialog.exec():
            data = dialog.get_data()
            self._repo.update_smart_task(
                task_id=task_id,
                title=data["title"],
                category=data["category"],
                priority=data["priority"],
                estimated_minutes=data["estimated_minutes"],
                start_time=data["start_time"],
                end_time=data["end_time"],
                scheduled_time=data["scheduled_time"],
                repeat_days=data["repeat_days"],
                day_notes_json=data["day_notes_json"],
                target_processes=data["target_processes"],
            )
            self.refresh()
            self._sync_notch()

    def refresh(self) -> None:
        while self._tasks_layout.count():
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = self._repo.get_smart_tasks()
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        total = len(tasks)

        # Update Apple visual analytics widgets
        self._ring_widget.set_stats(completed, total)
        monthly_stats = self._repo.get_monthly_task_stats()
        self._trend_graph.set_data(monthly_stats)
        self._water_widget.refresh()

        if not tasks:
            empty = QLabel("No tasks scheduled in your queue.\nClick '+ Add Smart Task' or pick a routine template (Gym, College, Sleep) to start.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("empty_state_lbl")
            self._tasks_layout.addWidget(empty)
            return

        for task in tasks:
            card = TaskCard(task)
            card.start_task.connect(self._on_start_task)
            card.complete_task.connect(self._on_complete_task)
            card.edit_task.connect(self._on_edit_task)
            card.delete_task.connect(self._on_delete_task)
            self._tasks_layout.addWidget(card)

    def _on_start_task(self, task_id: int) -> None:
        self._repo.update_smart_task_status(task_id, "in_progress")
        task = self._repo.get_smart_task(task_id)
        if task:
            mins = task.get("estimated_minutes", 25)
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
        self.setStyleSheet("""
            QLabel#page_title { font-size: 26px; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px; }
            QLabel#page_subtitle { font-size: 13px; color: #8E8E93; }
            QLabel#section_header { font-size: 11px; font-weight: 700; color: #8E8E93; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 6px; }
            QFrame#analytics_container {
                background-color: #161618;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            QLabel#analytics_hdr {
                font-size: 10px;
                font-weight: 700;
                color: #8E8E93;
                letter-spacing: 1.2px;
                text-transform: uppercase;
            }
            QPushButton#accent_btn {
                background-color: #0A84FF;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 9px 18px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton#accent_btn:hover { background-color: #0071E3; }
            QFrame#task_card {
                background-color: #1C1C1E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QFrame#task_card:hover {
                background-color: #242426;
                border-color: rgba(255, 255, 255, 0.15);
            }
            QLabel#task_title { font-size: 15px; font-weight: 600; color: #FFFFFF; }
            QLabel#task_title_completed { font-size: 15px; font-weight: 600; color: #636366; text-decoration: line-through; }
            QLabel#task_cat_badge {
                background: rgba(255, 255, 255, 0.06);
                border-radius: 5px;
                padding: 1px 6px;
                font-size: 9px;
                font-weight: 700;
                color: #8E8E93;
            }
            QLabel#task_time_pill {
                background: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 700;
                color: #0A84FF;
            }
            QLabel#task_today_note {
                color: #30D158;
                font-size: 11px;
                font-weight: 600;
                background: rgba(48, 209, 88, 0.12);
                border-radius: 6px;
                padding: 2px 8px;
            }
            QLabel#task_meta { font-size: 11px; color: #8E8E93; }
            QLabel#task_pill {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 10px;
                font-weight: 600;
                color: #8E8E93;
            }
            QPushButton#task_check_btn {
                background: rgba(255, 255, 255, 0.06);
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
            }
            QPushButton#task_btn_edit {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: #8E8E93;
                font-size: 12px;
                padding: 6px 10px;
            }
            QPushButton#task_btn_edit:hover {
                color: #0A84FF;
                border-color: rgba(10, 132, 255, 0.4);
            }
            QPushButton#task_btn_start {
                background-color: rgba(10, 132, 255, 0.15);
                border: 1px solid rgba(10, 132, 255, 0.35);
                border-radius: 8px;
                color: #0A84FF;
                font-weight: 700;
                font-size: 11px;
                padding: 6px 12px;
            }
            QPushButton#task_btn_start:hover {
                background-color: rgba(10, 132, 255, 0.25);
            }
            QPushButton#task_btn_del {
                background: transparent;
                border: none;
                color: #636366;
                font-size: 12px;
                padding: 4px;
            }
            QPushButton#task_btn_del:hover { color: #FF453A; }
            QLabel#empty_state_lbl {
                font-size: 13px;
                color: #8E8E93;
                padding: 40px;
                line-height: 1.6;
            }
        """)
