"""
ambient_notch.py — Physics-animated desktop Notch / Dynamic Island for Digital Wellbeing.

Features:
- Docked flush against the upper bezel of the primary screen.
- Resting compact pill state with live timer, active task name, and reactive flow indicator.
- Smooth spring physics animation on mouse hover, expanding downwards into a compact,
  focused card:
    * Active task details & controls (Mark Done, +5m, Pause/Resume, Skip/Next)
    * Real-time drift detection comparing foreground app / extension URL against task targets
    * Dynamic queue promotion (marking done advances to the next pending task automatically)
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
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.repository import Repository
from protection.focus_manager import FocusManager
from settings.manager import SettingsManager
from tracker.media_awareness import detect_foreground_media
from ui.theme import ThemeManager


class AmbientNotch(QWidget):
    """Screen-edge dynamic island / notch overlay."""

    task_completed = Signal(int)

    # Ultra-compact dimensions for zero interference with browser tabs & titlebars
    REST_WIDTH = 220
    REST_HEIGHT = 28
    EXPANDED_WIDTH = 340
    EXPANDED_HEIGHT = 120
    BORDER_RADIUS_REST = 14
    BORDER_RADIUS_EXP = 16

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
        self._next_task: Optional[dict] = None
        self._is_target_active: bool = True
        self._drift_seconds: int = 0
        self._poll_count: int = 0

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
        self._main_layout.setContentsMargins(10, 4, 10, 8)
        self._main_layout.setSpacing(6)

        # ── 1. Compact Resting Bar (Always visible in resting state) ─────────
        self._compact_bar = QWidget()
        self._compact_bar.setObjectName("compact_bar")
        self._compact_layout = QHBoxLayout(self._compact_bar)
        self._compact_layout.setContentsMargins(0, 0, 0, 0)
        self._compact_layout.setSpacing(6)

        self._flow_dot = QLabel("●")
        self._flow_dot.setObjectName("flow_dot")
        self._flow_dot.setFixedSize(12, 12)
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
        self._expanded_layout.setContentsMargins(2, 0, 2, 2)
        self._expanded_layout.setSpacing(6)

        # Row 1: Active Task Title + Priority Tag + Close
        r1 = QHBoxLayout()
        r1.setSpacing(6)

        self._exp_title = QLabel("Active Goal")
        self._exp_title.setObjectName("exp_title")
        r1.addWidget(self._exp_title, 1)

        self._priority_tag = QLabel("Normal")
        self._priority_tag.setObjectName("priority_tag")
        r1.addWidget(self._priority_tag)

        self._btn_close = QPushButton("✕")
        self._btn_close.setObjectName("notch_btn_close")
        self._btn_close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_close.clicked.connect(lambda: self.set_expanded(False))
        r1.addWidget(self._btn_close)
        self._expanded_layout.addLayout(r1)

        # Row 2: Target toolchain indicator & Queue status
        r2 = QHBoxLayout()
        r2.setSpacing(8)

        self._target_label = QLabel("🎯 Target: Any app")
        self._target_label.setObjectName("notch_target_label")
        r2.addWidget(self._target_label, 1)

        self._next_task_label = QLabel("Next: None")
        self._next_task_label.setObjectName("notch_next_task")
        r2.addWidget(self._next_task_label)
        self._expanded_layout.addLayout(r2)

        # Row 3: Action Buttons (Done, +5m, Toggle, Skip)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_done = QPushButton("✓ Done")
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

        self._btn_skip = QPushButton("⏭ Next")
        self._btn_skip.setObjectName("notch_btn_action")
        self._btn_skip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_skip.clicked.connect(self._on_skip_task_clicked)
        btn_row.addWidget(self._btn_skip)

        self._expanded_layout.addLayout(btn_row)

        self._main_layout.addWidget(self._expanded_panel)
        self._expanded_panel.setVisible(False)

    def _setup_animations(self) -> None:
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(220)
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

        self._container.resize(target_w, target_h)
        self._update_container_style()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.set_expanded(True)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
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
            self._flow_dot.setStyleSheet("color: #10B981;")
        self.sync_active_task()

    def _on_focus_completed(self) -> None:
        self._compact_timer.setText("00:00")
        self._compact_title.setText("Session Complete!")
        self._flow_dot.setStyleSheet("color: #10B981;")
        self.sync_active_task()

    def _on_poll_tick(self) -> None:
        self._poll_count += 1

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

        # Sync tasks every 2 seconds to keep 100% in sync with desktop app changes
        if self._poll_count % 2 == 0:
            self.sync_active_task()

        # Check drift if active task has target processes or domains
        if self._fm.is_active and self._active_task:
            targets = [t.lower() for t in (self._active_task.get("target_processes") or [])]
            target_doms = [d.lower() for d in (self._active_task.get("target_domains") or [])]

            matches = True
            if targets or target_doms:
                matches = False
                try:
                    # 1. Check foreground process
                    from tracker.foreground import get_foreground_app
                    fg_app, fg_title, hwnd = get_foreground_app()
                    p_name = (fg_app or "").lower()
                    if any(t in p_name for t in targets):
                        matches = True

                    # 2. Check extension reported URL for target domains
                    if not matches and target_doms:
                        try:
                            from protection.extension_bridge import ExtensionBridge
                            candidate = ExtensionBridge.instance().latest_url(p_name, max_age_s=6.0)
                            if any(d in candidate.lower() for d in target_doms):
                                matches = True
                        except Exception:
                            pass
                except Exception:
                    matches = True

            self._is_target_active = matches
            if matches:
                self._drift_seconds = 0
                self._flow_dot.setStyleSheet("color: #10B981;")  # In flow (emerald)
            else:
                self._drift_seconds += 1
                if self._drift_seconds > 45:
                    self._flow_dot.setStyleSheet("color: #F43F5E;")  # Alert (rose)
                elif self._drift_seconds > 15:
                    self._flow_dot.setStyleSheet("color: #F59E0B;")  # Drifting (amber)

    # ── Intelligent Task Prioritization Algorithm ─────────────────────────────

    def sync_active_task(self) -> None:
        """
        Deep Attention & Task Orchestration Algorithm:
        1. Selects explicit in-progress task.
        2. If none, auto-promotes top pending task if Focus is active, or queues it if idle.
        3. Previews the next task in the pipeline.
        4. Keeps live UI synchronized with database state.
        """
        tasks = self._repo.get_smart_tasks()
        in_prog = [t for t in tasks if t.get("status") == "in_progress"]
        pending = [t for t in tasks if t.get("status") == "pending"]

        if in_prog:
            self._active_task = in_prog[0]
            self._active_task_id = self._active_task["id"]
            self._next_task = pending[0] if pending else None
        elif pending:
            # Auto-promote to in_progress if user has Focus active
            if self._fm.is_active:
                self._active_task = pending[0]
                self._active_task_id = self._active_task["id"]
                self._repo.update_smart_task_status(self._active_task_id, "in_progress")
                self._next_task = pending[1] if len(pending) > 1 else None
            else:
                # Top pending task is primed
                self._active_task = pending[0]
                self._active_task_id = self._active_task["id"]
                self._next_task = pending[1] if len(pending) > 1 else None
        else:
            self._active_task = None
            self._active_task_id = 0
            self._next_task = None

        # Update UI labels
        if self._active_task:
            title = self._active_task.get("title", "")
            truncated = title if len(title) <= 18 else title[:16] + ".."
            self._compact_title.setText(truncated)
            self._exp_title.setText(title)

            # Priority badge
            prio = self._active_task.get("priority", 2)
            prio_text = "High" if prio == 1 else ("Normal" if prio == 2 else "Low")
            self._priority_tag.setText(prio_text)

            # Target indicators
            targets = (self._active_task.get("target_processes") or []) + (self._active_task.get("target_domains") or [])
            self._target_label.setText(f"🎯 {', '.join(targets[:2]) if targets else 'Any app'}")
        else:
            if self._fm.is_active:
                self._compact_title.setText("Focus Mode")
                self._exp_title.setText("Focus Session")
            else:
                self._compact_title.setText("Ready to Focus")
                self._exp_title.setText("Ready to Focus")
            self._priority_tag.setText("General")
            self._target_label.setText("🎯 Any app")

        # Next task in queue
        if self._next_task:
            next_t = self._next_task.get("title", "")
            next_trunc = next_t if len(next_t) <= 12 else next_t[:10] + ".."
            self._next_task_label.setText(f"Next: {next_trunc}")
        else:
            self._next_task_label.setText("Queue: Clear 🎉" if not pending else "Next: None")

    def _on_mark_done_clicked(self) -> None:
        """
        Mark Done handler:
        - Completes current active/primed task in repository.
        - Automatically advances to the next pending task.
        - Emits task_completed signal to notify MainWindow & TasksPage.
        """
        target_id = self._active_task_id
        if target_id <= 0:
            pending = self._repo.get_smart_tasks(status="pending")
            if pending:
                target_id = pending[0]["id"]

        if target_id > 0:
            self._repo.update_smart_task_status(target_id, "completed")
            self.task_completed.emit(target_id)

            # Automatically promote next pending task
            remaining = self._repo.get_smart_tasks(status="pending")
            if remaining and self._fm.is_active:
                self._repo.update_smart_task_status(remaining[0]["id"], "in_progress")

            self.sync_active_task()
        else:
            # If no tasks at all, mark focus session complete
            if self._fm.is_active:
                self._fm.stop_focus()
            self.sync_active_task()

    def _on_skip_task_clicked(self) -> None:
        """Skip to the next pending task without completing the current one."""
        pending = self._repo.get_smart_tasks(status="pending")
        if self._active_task and self._active_task.get("status") == "in_progress":
            self._repo.update_smart_task_status(self._active_task["id"], "pending")
        if pending:
            self._repo.update_smart_task_status(pending[0]["id"], "in_progress")
        self.sync_active_task()

    def _on_plus5_clicked(self) -> None:
        if self._fm.is_active:
            self._fm._seconds_remaining += 300
            self._fm.tick.emit(self._fm._seconds_remaining)

    def _on_toggle_focus_clicked(self) -> None:
        if self._fm.is_active:
            self._fm.stop_focus()
        else:
            mins = 25
            if self._active_task:
                mins = self._active_task.get("estimated_minutes", 25)
            self._fm.start_focus(minutes=mins)

    # ── Theme & Styling ───────────────────────────────────────────────────────

    def _update_container_style(self) -> None:
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        radius = self.BORDER_RADIUS_EXP if self._is_expanded else self.BORDER_RADIUS_REST
        bg_col = "rgba(18, 19, 23, 0.95)" if is_dark else "rgba(245, 246, 249, 0.96)"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.10)"
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
                font-size: 11px;
                font-weight: 700;
                font-family: Consolas, monospace;
                color: {text_main};
            }}
            QLabel#compact_title {{
                font-size: 11px;
                font-weight: 600;
                color: {text_main};
            }}
            QLabel#compact_divider {{
                font-size: 12px;
                font-weight: 700;
                color: {text_sub};
            }}
            QLabel#exp_title {{
                font-size: 12px;
                font-weight: 700;
                color: {text_main};
            }}
            QLabel#priority_tag {{
                font-size: 9px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.08);
                color: {accent};
                text-transform: uppercase;
            }}
            QLabel#notch_target_label {{
                font-size: 10px;
                color: {text_sub};
                font-weight: 500;
            }}
            QLabel#notch_next_task {{
                font-size: 10px;
                color: {accent};
                font-weight: 600;
            }}
            QPushButton#notch_btn_done {{
                background-color: {accent};
                color: #FFFFFF;
                border: none;
                border-radius: 9px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 700;
            }}
            QPushButton#notch_btn_action {{
                background-color: {tm.color('surface_secondary')};
                color: {text_main};
                border: 1px solid {tm.color('border')};
                border-radius: 9px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton#notch_btn_action:hover, QPushButton#notch_btn_done:hover {{
                opacity: 0.88;
            }}
            QPushButton#notch_btn_close {{
                background: transparent;
                border: none;
                color: {text_sub};
                font-size: 11px;
                font-weight: 700;
                padding: 0 4px;
            }}
        """)

    def _apply_theme(self, is_dark: bool) -> None:
        self._update_container_style()
        self._flow_dot.setStyleSheet("color: #10B981;" if self._fm.is_active else "color: #8E8E93;")
