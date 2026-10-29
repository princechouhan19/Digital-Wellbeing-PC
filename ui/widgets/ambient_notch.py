"""
ambient_notch.py — Physics-animated desktop Notch / Dynamic Island for Digital Wellbeing.

Inspired by Nectar (https://github.com/kua8/Nectar) / Bloom:
- Docked flush against the upper bezel of the primary screen.
- Resting compact pill state with live timer, active task name, and reactive flow indicator.
- Smooth spring physics animation on mouse hover, expanding downwards to reveal:
    * Active task details & controls (Mark Done, +5m, Pause/Resume)
    * Guardrails status & continuous flow continuity
    * Quick task switcher
- Respects fullscreen media / games via MediaAwarenessState.
"""
from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.repository import Repository
from protection.focus_manager import FocusManager
from settings.manager import SettingsManager
from tracker.media_awareness import detect_foreground_media
from ui import design_system as ds
from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager


class AmbientNotch(QWidget):
    """Screen-edge dynamic island / notch overlay."""

    task_completed = Signal(int)

    REST_WIDTH = 260
    REST_HEIGHT = 32
    EXPANDED_WIDTH = 440
    EXPANDED_HEIGHT = 200
    BORDER_RADIUS_REST = 16
    BORDER_RADIUS_EXP = 20

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        self._repo = Repository()
        self._fm = FocusManager.instance()
        self._sm = SettingsManager()

        self._is_expanded = False
        self._active_task: Optional[dict] = None
        self._active_task_id: int = 0
        self._is_target_active: bool = True
        self._drift_seconds: int = 0

        # Connect FocusManager signals
        self._fm.tick.connect(self._on_focus_tick)
        self._fm.focus_state_changed.connect(self._on_focus_state_changed)
        self._fm.focus_completed.connect(self._on_focus_completed)

        self._setup_ui()
        self._setup_animations()
        self._update_position(expanded=False)

        # Polling timer for drift checks and active task sync (1 sec)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._on_poll_tick)
        self._poll_timer.start()

        # Connect theme
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

        # Initial task sync
        self.sync_active_task()

    def _setup_ui(self) -> None:
        self._container = QFrame(self)
        self._container.setObjectName("notch_container")
        self._container.setMouseTracking(True)

        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(12, 4, 12, 10)
        self._main_layout.setSpacing(8)

        # ── 1. Compact Resting Bar (Always visible in resting state) ─────────
        self._compact_bar = QWidget()
        self._compact_bar.setObjectName("compact_bar")
        self._compact_layout = QHBoxLayout(self._compact_bar)
        self._compact_layout.setContentsMargins(0, 0, 0, 0)
        self._compact_layout.setSpacing(8)

        self._flow_dot = QLabel("●")
        self._flow_dot.setObjectName("flow_dot")
        self._flow_dot.setFixedSize(14, 14)
        self._compact_layout.addWidget(self._flow_dot)

        self._compact_timer = QLabel("25:00")
        self._compact_timer.setObjectName("compact_timer")
        self._compact_layout.addWidget(self._compact_timer)

        self._compact_divider = QLabel("·")
        self._compact_divider.setObjectName("compact_divider")
        self._compact_layout.addWidget(self._compact_divider)

        self._compact_title = QLabel("Ready to Focus")
        self._compact_title.setObjectName("compact_title")
        self._compact_title.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._compact_layout.addWidget(self._compact_title, 1)

        self._main_layout.addWidget(self._compact_bar)

        # ── 2. Expanded Detail Panel (Hidden in resting state) ─────────────────
        self._expanded_panel = QWidget()
        self._expanded_panel.setObjectName("expanded_panel")
        self._expanded_layout = QVBoxLayout(self._expanded_panel)
        self._expanded_layout.setContentsMargins(4, 2, 4, 2)
        self._expanded_layout.setSpacing(10)

        # Top row in expansion: controls
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_done = QPushButton("Mark Done")
        self._btn_done.setObjectName("notch_btn_done")
        self._btn_done.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_done.clicked.connect(self._on_mark_done_clicked)
        btn_row.addWidget(self._btn_done)

        self._btn_plus5 = QPushButton("+5m")
        self._btn_plus5.setObjectName("notch_btn_action")
        self._btn_plus5.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_plus5.clicked.connect(self._on_plus5_clicked)
        btn_row.addWidget(self._btn_plus5)

        self._btn_toggle = QPushButton("Pause")
        self._btn_toggle.setObjectName("notch_btn_action")
        self._btn_toggle.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_toggle.clicked.connect(self._on_toggle_focus_clicked)
        btn_row.addWidget(self._btn_toggle)

        btn_row.addStretch()

        self._btn_close = QPushButton("✕")
        self._btn_close.setObjectName("notch_btn_close")
        self._btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_close.clicked.connect(lambda: self.set_expanded(False))
        btn_row.addWidget(self._btn_close)

        self._expanded_layout.addLayout(btn_row)

        # Details info row
        self._details_label = QLabel("Shield active · Distractions blocked")
        self._details_label.setObjectName("notch_details")
        self._details_label.setWordWrap(True)
        self._expanded_layout.addWidget(self._details_label)

        # Next Task queue preview
        self._next_task_label = QLabel("Next up: No pending tasks")
        self._next_task_label.setObjectName("notch_next_task")
        self._next_task_label.setWordWrap(True)
        self._expanded_layout.addWidget(self._next_task_label)

        self._main_layout.addWidget(self._expanded_panel)
        self._expanded_panel.setVisible(False)

    def _setup_animations(self) -> None:
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _update_position(self, expanded: bool) -> None:
        screen = self.screen() or QWidget().screen()
        if not screen:
            return
        geo = screen.geometry()
        target_w = self.EXPANDED_WIDTH if expanded else self.REST_WIDTH
        target_h = self.EXPANDED_HEIGHT if expanded else self.REST_HEIGHT
        x = geo.x() + (geo.width() - target_w) // 2
        y = geo.y()  # Flush against the very top edge

        if self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self.setGeometry(x, y, target_w, target_h)
        self._container.setGeometry(0, 0, target_w, target_h)

    def set_expanded(self, expanded: bool) -> None:
        if self._is_expanded == expanded:
            return
        self._is_expanded = expanded

        screen = self.screen() or QWidget().screen()
        if not screen:
            return
        geo = screen.geometry()
        target_w = self.EXPANDED_WIDTH if expanded else self.REST_WIDTH
        target_h = self.EXPANDED_HEIGHT if expanded else self.REST_HEIGHT
        target_x = geo.x() + (geo.width() - target_w) // 2
        target_y = geo.y()

        self._expanded_panel.setVisible(expanded)

        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(QRect(target_x, target_y, target_w, target_h))
        self._anim.start()

        # Update container size simultaneously
        self._container.resize(target_w, target_h)
        self._update_container_style()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.set_expanded(True)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        # Check if cursor is truly outside the widget boundary
        pos = QCursor.pos()
        if not self.geometry().contains(pos):
            self.set_expanded(False)

    # ── Signal & Event Handlers ───────────────────────────────────────────────

    def _on_focus_tick(self, seconds_left: int) -> None:
        mins = seconds_left // 60
        secs = seconds_left % 60
        self._compact_timer.setText(f"{mins:02d}:{secs:02d}")

        if self._active_task_id > 0:
            self._repo.add_smart_task_active_time(self._active_task_id, 1.0)

    def _on_focus_state_changed(self, is_active: bool) -> None:
        self._btn_toggle.setText("Pause" if is_active else "Resume")
        if not is_active:
            self._flow_dot.setStyleSheet("color: #8E8E93;")
            if not self._active_task:
                self._compact_title.setText("Ready to Focus")
        else:
            self._flow_dot.setStyleSheet("color: #34C759;")

    def _on_focus_completed(self) -> None:
        self._compact_timer.setText("00:00")
        self._compact_title.setText("Session Complete!")
        self._flow_dot.setStyleSheet("color: #30D158;")

    def _on_poll_tick(self) -> None:
        # Check fullscreen state (games / movies) — fade notch out if fullscreen
        try:
            fg_media = detect_foreground_media()
            if getattr(fg_media, "is_fullscreen", False):
                self.hide()
                return
            elif not self.isVisible() and self._sm.get_bool("ambient_notch_enabled", True):
                self.show()
        except Exception:
            pass

        # Check drift if active task has target processes
        if self._fm.is_active and self._active_task:
            targets = self._active_task.get("target_processes") or []
            if targets:
                # Basic foreground process check
                from tracker.idle import get_last_input_tick
                # If target processes defined, verify foreground match
                try:
                    import win32gui, win32process, psutil
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        p_name = psutil.Process(pid).name().lower() if pid else ""
                        matches = any(t.lower() in p_name for t in targets)
                        self._is_target_active = matches
                        if matches:
                            self._drift_seconds = 0
                            self._flow_dot.setStyleSheet("color: #34C759;")
                        else:
                            self._drift_seconds += 1
                            if self._drift_seconds > 45:
                                self._flow_dot.setStyleSheet("color: #FF9F0A;")
                except Exception:
                    pass

    def sync_active_task(self) -> None:
        """Fetch active in-progress task from repository."""
        tasks = self._repo.get_smart_tasks()
        in_prog = [t for t in tasks if t.get("status") == "in_progress"]
        if in_prog:
            self._active_task = in_prog[0]
            self._active_task_id = self._active_task["id"]
            self._compact_title.setText(self._active_task["title"][:26])
            self._details_label.setText(
                f"Task: {self._active_task['title']} · Target: {', '.join(self._active_task.get('target_processes') or ['Any'])}"
            )
        else:
            self._active_task = None
            self._active_task_id = 0
            if not self._fm.is_active:
                self._compact_title.setText("Ready to Focus")
                self._details_label.setText("No active task. Click to launch Focus or choose a task.")

        # Preview next task in queue
        pending = [t for t in tasks if t.get("status") == "pending"]
        if pending:
            self._next_task_label.setText(f"Next up: {pending[0]['title']} ({pending[0]['estimated_minutes']}m)")
        else:
            self._next_task_label.setText("Next up: No pending tasks")

    def _on_mark_done_clicked(self) -> None:
        if self._active_task_id > 0:
            self._repo.update_smart_task_status(self._active_task_id, "completed")
            self.task_completed.emit(self._active_task_id)
            self.sync_active_task()

    def _on_plus5_clicked(self) -> None:
        if self._fm.is_active:
            self._fm._seconds_remaining += 300
            self._fm.tick.emit(self._fm._seconds_remaining)

    def _on_toggle_focus_clicked(self) -> None:
        if self._fm.is_active:
            self._fm.stop_focus()
        else:
            self._fm.start_focus(minutes=25)

    # ── Theme & Styling ───────────────────────────────────────────────────────

    def _update_container_style(self) -> None:
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        radius = self.BORDER_RADIUS_EXP if self._is_expanded else self.BORDER_RADIUS_REST
        bg_col = "rgba(22, 22, 26, 0.94)" if is_dark else "rgba(248, 248, 250, 0.95)"
        border_col = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.12)"
        accent = tm.color("accent")
        text_main = tm.color("text_main")
        text_sub = tm.color("text_sub")

        self._container.setStyleSheet(f"""
            QFrame#notch_container {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-top: none;
                border-bottom-left-radius: {radius}px;
                border-bottom-right-radius: {radius}px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
            QLabel#compact_timer {{
                font-size: 13px;
                font-weight: 700;
                font-family: Consolas, monospace;
                color: {text_main};
            }}
            QLabel#compact_title {{
                font-size: 12px;
                font-weight: 600;
                color: {text_main};
            }}
            QLabel#compact_divider {{
                font-size: 14px;
                font-weight: 700;
                color: {text_sub};
            }}
            QLabel#notch_details {{
                font-size: 11px;
                color: {text_sub};
                font-weight: 500;
            }}
            QLabel#notch_next_task {{
                font-size: 11px;
                color: {accent};
                font-weight: 600;
            }}
            QPushButton#notch_btn_done {{
                background-color: {accent};
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#notch_btn_action {{
                background-color: {tm.color('surface_secondary')};
                color: {text_main};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#notch_btn_action:hover, QPushButton#notch_btn_done:hover {{
                opacity: 0.88;
            }}
            QPushButton#notch_btn_close {{
                background: transparent;
                border: none;
                color: {text_sub};
                font-size: 12px;
                font-weight: 700;
                padding: 2px 6px;
            }}
        """)

    def _apply_theme(self, is_dark: bool) -> None:
        self._update_container_style()
        self._flow_dot.setStyleSheet("color: #34C759;" if self._fm.is_active else "color: #8E8E93;")
