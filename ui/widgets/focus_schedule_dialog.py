"""
focus_schedule_dialog.py — Create and manage recurring Focus blocks.
"""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from protection.focus_schedule import FocusSchedule, FocusScheduleEngine
from ui.icons import get_icon
from ui.theme import ThemeManager

MODE_LABELS = {
    "deep": "Deep Focus",
    "work": "Work",
    "study": "Study",
    "movie": "Media",
    "custom": "Custom",
}
DAY_LABELS = ["M", "T", "W", "T", "F", "S", "S"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _format_days(days: List[int]) -> str:
    if days == [0, 1, 2, 3, 4]:
        return "Weekdays"
    if days == [5, 6]:
        return "Weekends"
    if days == list(range(7)):
        return "Every day"
    return ", ".join(DAY_NAMES[d] for d in days if 0 <= d <= 6)


class ScheduleEditDialog(QDialog):
    def __init__(self, schedule: Optional[FocusSchedule] = None, parent=None) -> None:
        super().__init__(parent)
        self._schedule = schedule
        self.setWindowTitle("Edit Focus block" if schedule else "New Focus block")
        self.setMinimumWidth(480)
        self.setModal(True)
        self._setup_ui()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 20)
        root.setSpacing(12)

        title = QLabel("Edit Focus block" if self._schedule else "New Focus block")
        title.setObjectName("dialog_title")
        root.addWidget(title)

        self._name = QLineEdit()
        self._name.setPlaceholderText("Morning deep work")
        if self._schedule:
            self._name.setText(self._schedule.name)
        root.addWidget(QLabel("Name"))
        root.addWidget(self._name)

        mode_row = QHBoxLayout()
        mode_col = QVBoxLayout()
        mode_col.addWidget(QLabel("Mode"))
        self._mode = QComboBox()
        for key, label in MODE_LABELS.items():
            self._mode.addItem(label, key)
        if self._schedule:
            idx = self._mode.findData(self._schedule.mode)
            self._mode.setCurrentIndex(max(0, idx))
        mode_col.addWidget(self._mode)
        mode_row.addLayout(mode_col, 1)

        time_col = QVBoxLayout()
        time_col.addWidget(QLabel("Start"))
        self._time = QTimeEdit()
        self._time.setDisplayFormat("HH:mm")
        if self._schedule:
            h, m = (int(p) for p in self._schedule.start.split(":")[:2])
            self._time.setTime(QTime(h, m))
        else:
            self._time.setTime(QTime(9, 0))
        time_col.addWidget(self._time)
        mode_row.addLayout(time_col, 0)

        duration_col = QVBoxLayout()
        duration_col.addWidget(QLabel("Duration"))
        self._duration = QSpinBox()
        self._duration.setRange(5, 180)
        self._duration.setSuffix(" min")
        self._duration.setValue(self._schedule.duration_min if self._schedule else 50)
        duration_col.addWidget(self._duration)
        mode_row.addLayout(duration_col, 0)
        root.addLayout(mode_row)

        root.addWidget(QLabel("Repeat on"))
        days_row = QHBoxLayout()
        days_row.setSpacing(4)
        self._days: List[QCheckBox] = []
        selected = set(self._schedule.weekdays if self._schedule else [0, 1, 2, 3, 4])
        for index, label in enumerate(DAY_LABELS):
            box = QCheckBox(label)
            box.setObjectName("weekday_box")
            box.setChecked(index in selected)
            days_row.addWidget(box)
            self._days.append(box)
        days_row.addStretch()
        root.addLayout(days_row)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("preset_btn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save block")
        save.setObjectName("primary_pill_btn")
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        root.addLayout(buttons)

    def _save(self) -> None:
        days = [i for i, box in enumerate(self._days) if box.isChecked()]
        if not days:
            self._days[0].setFocus()
            return
        name = self._name.text().strip() or "Focus block"
        schedule = FocusSchedule(
            id=self._schedule.id if self._schedule else "",
            name=name,
            mode=self._mode.currentData() or "work",
            start=self._time.time().toString("HH:mm"),
            duration_min=self._duration.value(),
            weekdays=days,
            enabled=self._schedule.enabled if self._schedule else True,
        )
        if not schedule.id:
            import uuid

            schedule.id = uuid.uuid4().hex[:12]
        self._result = schedule
        self.accept()

    @property
    def result_schedule(self) -> FocusSchedule:
        return self._result

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 22px; font-weight: 700; }}
            QLineEdit, QComboBox, QTimeEdit, QSpinBox {{
                background: {tm.color('input_bg')}; border: 1px solid {tm.color('input_border')};
                border-radius: 10px; color: {tm.color('text_main')}; padding: 6px 9px; font-size: 12px;
            }}
            QCheckBox#weekday_box {{ color: {tm.color('text_sub')}; font-size: 12px; spacing: 4px; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 999px; padding: 8px 18px; font-weight: 700; }}
            QPushButton#preset_btn {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 10px; color: {tm.color('text_sub')}; padding: 8px 16px; font-weight: 600; }}
        """)


class _ScheduleRow(QFrame):
    def __init__(self, schedule: FocusSchedule, on_edit, on_delete, on_toggle, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("schedule_row")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 12, 10)
        layout.setSpacing(10)

        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(schedule.name)
        name.setObjectName("schedule_name")
        meta = QLabel(
            f"{_format_days(schedule.weekdays)} · {schedule.start} · "
            f"{schedule.duration_min}m · {MODE_LABELS.get(schedule.mode, schedule.mode)}"
        )
        meta.setObjectName("schedule_meta")
        text.addWidget(name)
        text.addWidget(meta)
        layout.addLayout(text, 1)

        toggle = QPushButton("On" if schedule.enabled else "Off")
        toggle.setObjectName("schedule_toggle")
        toggle.setCheckable(True)
        toggle.setChecked(schedule.enabled)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.clicked.connect(lambda checked: on_toggle(schedule, checked))
        layout.addWidget(toggle)

        edit = QPushButton()
        edit.setObjectName("schedule_icon_btn")
        edit.setIcon(get_icon("edit", color=ThemeManager.instance().color("text_sub"), size=14))
        edit.setToolTip("Edit")
        edit.setFixedSize(28, 28)
        edit.clicked.connect(lambda: on_edit(schedule))
        layout.addWidget(edit)

        delete = QPushButton()
        delete.setObjectName("schedule_icon_btn")
        delete.setIcon(get_icon("trash", color=ThemeManager.instance().color("text_muted"), size=14))
        delete.setToolTip("Delete")
        delete.setFixedSize(28, 28)
        delete.clicked.connect(lambda: on_delete(schedule))
        layout.addWidget(delete)


class FocusScheduleDialog(QDialog):
    def __init__(self, engine: Optional[FocusScheduleEngine] = None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine or FocusScheduleEngine()
        self.setWindowTitle("Focus schedules")
        self.setMinimumSize(620, 560)
        self.setModal(True)
        self._setup_ui()
        self._reload()
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        header = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel("Focus schedules")
        title.setObjectName("dialog_title")
        subtitle = QLabel("Start a Focus block automatically on selected days.")
        subtitle.setObjectName("dialog_subtitle")
        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text, 1)
        add = QPushButton("New block")
        add.setObjectName("primary_pill_btn")
        add.setCursor(Qt.CursorShape.PointingHandCursor)
        add.setIcon(get_icon("plus", "#FFFFFF", 13))
        add.clicked.connect(self._add)
        header.addWidget(add, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

        done = QPushButton("Done")
        done.setObjectName("primary_pill_btn")
        done.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(done)
        root.addLayout(row)

    def _reload(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        schedules = self._engine.load()
        if not schedules:
            empty = QLabel("No focus blocks yet. Add one to make Focus automatic.")
            empty.setObjectName("schedule_empty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, empty)
            return
        for index, schedule in enumerate(schedules):
            row = _ScheduleRow(
                schedule,
                self._edit,
                self._delete,
                self._toggle,
            )
            self._list_layout.insertWidget(index, row)

    def _add(self) -> None:
        dialog = ScheduleEditDialog(parent=self)
        if dialog.exec():
            self._engine.add(dialog.result_schedule)
            self._reload()

    def _edit(self, schedule: FocusSchedule) -> None:
        dialog = ScheduleEditDialog(schedule, parent=self)
        if dialog.exec():
            self._engine.update(dialog.result_schedule)
            self._reload()

    def _delete(self, schedule: FocusSchedule) -> None:
        self._engine.remove(schedule.id)
        self._reload()

    def _toggle(self, schedule: FocusSchedule, enabled: bool) -> None:
        schedule.enabled = enabled
        self._engine.update(schedule)
        self._reload()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog {{ background: {tm.color('bg')}; }}
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#dialog_title {{ color: {tm.color('text_main')}; font-size: 24px; font-weight: 700; }}
            QLabel#dialog_subtitle {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QFrame#schedule_row {{ background: {tm.color('surface')}; border: 1px solid {tm.color('border')}; border-radius: 12px; }}
            QLabel#schedule_name {{ color: {tm.color('text_main')}; font-size: 13px; font-weight: 600; }}
            QLabel#schedule_meta {{ color: {tm.color('text_muted')}; font-size: 11px; }}
            QPushButton#schedule_toggle {{ background: {tm.color('surface_secondary')}; border: 1px solid {tm.color('border')}; border-radius: 999px; color: {tm.color('text_sub')}; padding: 3px 12px; font-size: 10px; font-weight: 700; }}
            QPushButton#schedule_toggle:checked {{ color: #30D158; border-color: rgba(48,209,88,.4); }}
            QPushButton#schedule_icon_btn {{ background: transparent; border: none; border-radius: 8px; }}
            QPushButton#schedule_icon_btn:hover {{ background: {tm.color('surface_hover')}; }}
            QLabel#schedule_empty {{ color: {tm.color('text_muted')}; font-size: 12px; padding: 30px; }}
            QPushButton#primary_pill_btn {{ background: {tm.color('accent')}; color: white; border: none; border-radius: 999px; padding: 8px 18px; font-size: 12px; font-weight: 700; }}
            QPushButton#primary_pill_btn:hover {{ background: {tm.color('accent_hover')}; }}
        """)
