"""
onboarding.py — First-run welcome flow for Digital Wellbeing.

A five-step, Apple-style setup experience:
    1. Welcome + optional name
    2. Appearance (live theme preview)
    3. What matters to you (goal cards that tune sensible defaults)
    4. SafeBrowse (open-source adult content filter)
    5. You're all set

Design rules:
  - Every choice is skippable; nothing is forced.
  - Only local settings are written; the content filter applies its hosts
    block in a background thread and may surface a single UAC prompt.
  - The dialog is application-modal, frameless, and animates between steps
    with the same rise+fade used by page navigation.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame,
    QGraphicsOpacityEffect, QSizePolicy,
)

from settings.manager import SettingsManager
from ui.theme import ThemeManager
from ui import feedback
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
from ui.widgets.fluent import FluentButton, SegmentedControl, ToggleSwitch


class _GoalCard(QFrame):
    """Selectable card used for the 'What matters to you' step."""

    toggled = Signal(bool)

    def __init__(self, title: str, subtitle: str, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("goal_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = bool(checked)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(2)
        self._title = QLabel(title)
        self._title.setObjectName("goal_title")
        self._subtitle = QLabel(subtitle)
        self._subtitle.setObjectName("goal_subtitle")
        self._subtitle.setWordWrap(True)
        lay.addWidget(self._title)
        lay.addWidget(self._subtitle)

        self._apply_theme(ThemeManager.instance().is_dark)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if checked != self._checked:
            self._checked = bool(checked)
            self._refresh_check_style()
            self.toggled.emit(self._checked)

    def mouseReleaseEvent(self, event):
        self.setChecked(not self._checked)
        feedback.tap()
        super().mouseReleaseEvent(event)

    def _refresh_check_style(self) -> None:
        tm = ThemeManager.instance()
        accent = tm.color("accent")
        if self._checked:
            self.setStyleSheet(f"""
                QFrame#goal_card {{
                    background-color: {accent}22;
                    border: 1.5px solid {accent};
                    border-radius: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#goal_card {{
                    background-color: {tm.color('surface_secondary')};
                    border: 1.5px solid {tm.color('border')};
                    border-radius: 14px;
                }}
            """)

    def _apply_theme(self, is_dark: bool) -> None:
        self._refresh_check_style()


class OnboardingFlow(QDialog):
    """First-run onboarding wizard. Emits flow_finished() when completed."""

    flow_finished = Signal()
    _filter_result = Signal(bool, str)

    STEPS = ("welcome", "appearance", "goals", "safebrowse", "done")

    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint,
        )
        self._sm = SettingsManager()
        self._step = 0
        self._applying_filter = False

        self.setFixedSize(560, 600)
        self.setWindowTitle("Welcome to Digital Wellbeing")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Fade-in
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity")
        self._fade.setDuration(240)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui()
        self._filter_result.connect(self._on_filter_result)
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("onboarding_card")
        card_l = QVBoxLayout(self._card)
        card_l.setContentsMargins(40, 32, 40, 28)
        card_l.setSpacing(16)

        # Progress dots
        dots_row = QHBoxLayout()
        dots_row.addStretch()
        self._dots = []
        for _ in self.STEPS:
            d = QLabel()
            d.setFixedSize(7, 7)
            d.setObjectName("onb_dot")
            dots_row.addWidget(d)
        dots_row.addStretch()
        card_l.addLayout(dots_row)

        # Steps
        self._stack = AnimatedStackedWidget()
        self._stack.addWidget(self._build_welcome_step())      # 0
        self._stack.addWidget(self._build_appearance_step())   # 1
        self._stack.addWidget(self._build_goals_step())        # 2
        self._stack.addWidget(self._build_safebrowse_step())   # 3
        self._stack.addWidget(self._build_done_step())         # 4
        card_l.addWidget(self._stack, 1)

        # Footer buttons
        footer = QHBoxLayout()
        footer.setSpacing(12)
        self._back_btn = FluentButton("Back")
        self._back_btn.clicked.connect(self._go_back)
        footer.addWidget(self._back_btn)
        footer.addStretch()
        self._continue_btn = FluentButton("Continue", primary=True)
        self._continue_btn.setFixedWidth(140)
        self._continue_btn.clicked.connect(self._go_next)
        footer.addWidget(self._continue_btn)
        card_l.addLayout(footer)

        outer.addWidget(self._card)
        self._update_chrome()

    def _step_header(self, title: str, subtitle: str) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(6)
        t = QLabel(title)
        t.setObjectName("onb_title")
        t.setWordWrap(True)
        s = QLabel(subtitle)
        s.setObjectName("onb_subtitle")
        s.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(s)
        return col

    def _build_welcome_step(self) -> QFrame:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(16)

        # App icon
        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(
                72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(icon_lbl)

        head = self._step_header(
            "Welcome to Digital Wellbeing",
            "A calmer relationship with your PC — built on understanding your time, "
            "not policing it. Everything stays on this device.",
        )
        lay.addLayout(head)

        name_lbl = QLabel("What should we call you?")
        name_lbl.setObjectName("onb_field_label")
        lay.addWidget(name_lbl)

        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Optional — your name stays private")
        self._name_input.setMaxLength(50)
        self._name_input.returnPressed.connect(self._go_next)
        lay.addWidget(self._name_input)
        lay.addStretch()
        return page

    def _build_appearance_step(self) -> QFrame:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(16)

        head = self._step_header(
            "Pick your look",
            "You can change this anytime in Settings. The preview applies instantly.",
        )
        lay.addLayout(head)

        current = self._sm.theme
        idx = {"dark": 0, "light": 1, "system": 2}.get(current, 0)
        self._theme_seg = SegmentedControl(["Dark", "Light", "System"])
        self._theme_seg.set_current(idx)
        self._theme_seg.selection_changed.connect(self._on_theme_selected)
        lay.addWidget(self._theme_seg)

        # Preview panel
        self._preview = QFrame()
        self._preview.setObjectName("onb_preview")
        self._preview.setMinimumHeight(180)
        pv_l = QVBoxLayout(self._preview)
        pv_l.setContentsMargins(20, 16, 20, 16)
        pv_l.setSpacing(8)
        pv_title = QLabel("Dashboard preview")
        pv_title.setObjectName("onb_preview_title")
        pv_line = QLabel("Screen time today · 4h 32m")
        pv_line.setObjectName("onb_preview_line")
        pv_bar = QFrame()
        pv_bar.setObjectName("onb_preview_bar")
        pv_bar.setFixedHeight(10)
        pv_bar.setMaximumWidth(220)
        pv_bar.setStyleSheet(f"border-radius: 5px;")
        pv_l.addWidget(pv_title)
        pv_l.addWidget(pv_line)
        pv_l.addSpacing(6)
        pv_l.addWidget(pv_bar)
        pv_l.addStretch()
        lay.addWidget(self._preview)
        lay.addStretch()
        return page

    def _build_goals_step(self) -> QFrame:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(12)

        head = self._step_header(
            "What matters to you?",
            "Choose what to start with. You can fine-tune everything later in Settings.",
        )
        lay.addLayout(head)

        self._goal_insights = _GoalCard(
            "Understand my screen time",
            "Daily summaries and weekly trends, right on your dashboard.",
            checked=True,
        )
        self._goal_limits = _GoalCard(
            "Limit distracting apps",
            "Gentle daily limits with a friendly heads-up before they run out.",
            checked=False,
        )
        self._goal_winddown = _GoalCard(
            "Wind down at night",
            "SleepGuard notices when you doze off and safely locks the PC.",
            checked=False,
        )
        lay.addWidget(self._goal_insights)
        lay.addWidget(self._goal_limits)
        lay.addWidget(self._goal_winddown)
        lay.addStretch()
        return page

    def _build_safebrowse_step(self) -> QFrame:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(16)

        head = self._step_header(
            "Browse with confidence",
            "SafeBrowse filters adult websites system-wide using open-source, "
            "community-maintained blocklists — in every browser, fully offline "
            "after setup.",
        )
        lay.addLayout(head)

        from PySide6.QtWidgets import QFrame as _QF
        card = _QF()
        card.setObjectName("goal_card")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 14, 16, 14)
        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Block adult content")
        t.setObjectName("goal_title")
        s = QLabel("Windows will ask for administrator approval once — that's what "
                   "keeps the filter honest.")
        s.setObjectName("goal_subtitle")
        s.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(s)
        row.addLayout(col, 1)

        self._safebrowse_toggle = ToggleSwitch()
        self._safebrowse_toggle.setChecked(False)
        self._safebrowse_toggle.toggled.connect(lambda _: feedback.tap())
        row.addWidget(self._safebrowse_toggle)
        lay.addWidget(card)

        self._filter_status = QLabel("")
        self._filter_status.setObjectName("onb_status")
        self._filter_status.setWordWrap(True)
        lay.addWidget(self._filter_status)
        lay.addStretch()
        return page

    def _build_done_step(self) -> QFrame:
        page = QFrame()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).parent.parent / "assets" / "icons" / "app_logo.png"
        pix = QPixmap(str(logo_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(icon_lbl)

        self._done_title = QLabel("You're all set")
        self._done_title.setObjectName("onb_title")
        self._done_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._done_title)

        self._summary = QLabel("")
        self._summary.setObjectName("onb_subtitle")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setWordWrap(True)
        lay.addWidget(self._summary)
        return page

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _go_next(self) -> None:
        if self._step == 0 and not self._name_input.hasFocus():
            # allow Return key convenience
            pass
        if self._step >= len(self.STEPS) - 1:
            self._finish()
            return
        if self._step == 3 and self._safebrowse_toggle.isChecked() and not self._applying_filter:
            # Apply the filter while the user reads the final step
            self._apply_safebrowse()
        self._step += 1
        self._stack.setCurrentIndexAnimated(self._step)
        self._update_chrome()
        feedback.play(feedback.Sound.TAP)

    def _go_back(self) -> None:
        if self._step <= 0:
            return
        self._step -= 1
        self._stack.setCurrentIndexAnimated(self._step)
        self._update_chrome()
        feedback.play(feedback.Sound.TAP)

    def _update_chrome(self) -> None:
        # Dots
        for i, d in enumerate(self._dots):
            d.setProperty("active", i == self._step)
            d.setStyleSheet(
                f"background-color: {self._dot_color(i == self._step)}; border-radius: 3px;")
        # Buttons
        self._back_btn.setVisible(self._step > 0 and self._step < len(self.STEPS) - 1)
        self._continue_btn.setText("Get Started" if self._step == len(self.STEPS) - 1 else "Continue")
        if self._step == 0:
            self._name_input.setFocus()

    def _dot_color(self, active: bool) -> str:
        tm = ThemeManager.instance()
        return tm.color("accent") if active else tm.color("border")

    # ------------------------------------------------------------------
    # Choices
    # ------------------------------------------------------------------

    def _on_theme_selected(self, idx: int) -> None:
        theme = ("dark", "light", "system")[idx]
        self._sm.theme = theme
        ThemeManager.instance().set_theme(theme)
        feedback.tap()

    def _apply_safebrowse(self) -> None:
        self._applying_filter = True
        self._filter_status.setText("Setting up SafeBrowse…")

        from protection.content_blocker import ContentBlocker
        cb = ContentBlocker.instance()

        def worker():
            try:
                if self._safebrowse_toggle.isChecked():
                    ok, msg = cb.enable()
                else:
                    ok, msg = True, ""
            except Exception as exc:
                ok, msg = False, f"SafeBrowse couldn't finish setup: {exc}"
            # Queued connection: safe to emit from a worker thread
            self._filter_result.emit(ok, msg)

        import threading
        threading.Thread(target=worker, daemon=True, name="DW-Onboarding-SafeBrowse").start()

    def _on_filter_result(self, ok: bool, msg: str) -> None:
        self._applying_filter = False
        self._filter_status.setText(("\u2713  " if ok else "\u2014  ") + msg)

    # ------------------------------------------------------------------
    # Finish
    # ------------------------------------------------------------------

    def _finish(self) -> None:
        name = self._name_input.text().strip()
        if name:
            self._sm.display_name = name

        goals = []
        if self._goal_insights.isChecked():
            self._sm.set_bool("notifications_enabled", True)
            goals.append("insights")
        if self._goal_limits.isChecked():
            if self._sm.get_int("daily_limit_minutes", 0) <= 0:
                self._sm.set_int("daily_limit_minutes", 120)
            goals.append("limits")
        if self._goal_winddown.isChecked():
            self._sm.set_bool("sleepguard_enabled", True)
            goals.append("winddown")
        self._sm.set("onboarding_goals", ",".join(goals))

        if self._safebrowse_toggle.isChecked() and not self._applying_filter:
            # User reached the end before the apply completed — persist intent.
            self._sm.set_bool("content_filter_enabled", True)

        self._summary.setText(self._build_summary())
        self._sm.onboarding_completed = True
        feedback.success()
        self.flow_finished.emit()
        self.accept()

    def _build_summary(self) -> str:
        parts = []
        name = self._name_input.text().strip()
        if name:
            parts.append(f"Welcome, {name}.")
        theme = self._sm.theme
        parts.append({"dark": "Dark appearance", "light": "Light appearance",
                      "system": "Follows your system theme"}[theme])
        if self._goal_insights.isChecked():
            parts.append("daily insights on")
        if self._goal_limits.isChecked():
            parts.append("app limits on")
        if self._goal_winddown.isChecked():
            parts.append("nightly wind-down on")
        if self._safebrowse_toggle.isChecked():
            parts.append("SafeBrowse on")
        return " · ".join(parts)

    # ------------------------------------------------------------------
    # Chrome / theme
    # ------------------------------------------------------------------

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self._card.setStyleSheet(f"""
            QFrame#onboarding_card {{
                background-color: {tm.color('card_solid')};
                border: 1px solid {tm.color('border')};
                border-radius: 20px;
            }}
            QLabel#onb_title {{
                color: {tm.color('text_main')};
                font-size: 24px;
                font-weight: 700;
                letter-spacing: -0.4px;
            }}
            QLabel#onb_subtitle {{
                color: {tm.color('text_sub')};
                font-size: 13px;
                line-height: 1.45;
            }}
            QLabel#onb_field_label {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#onb_status {{
                color: {tm.color('text_muted')};
                font-size: 12px;
            }}
            QLabel#onb_preview {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#onb_preview_title {{
                color: {tm.color('text_main')};
                font-size: 15px;
                font-weight: 700;
            }}
            QLabel#onb_preview_line {{
                color: {tm.color('text_sub')};
                font-size: 12px;
            }}
            QFrame#onb_preview_bar {{
                background-color: {tm.color('accent')};
            }}
            QFrame#goal_card {{
                background-color: {tm.color('surface_secondary')};
                border: 1.5px solid {tm.color('border')};
                border-radius: 14px;
            }}
            QLabel#goal_title {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 600;
            }}
            QLabel#goal_subtitle {{
                color: {tm.color('text_sub')};
                font-size: 12px;
            }}
            QLineEdit {{
                background-color: {tm.color('input_bg')};
                color: {tm.color('text_main')};
                border: 1.5px solid {tm.color('input_border')};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 14px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border-color: {tm.color('accent')};
            }}
        """)
        self._update_chrome()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fade.start()
        self._name_input.setFocus()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            # Escape completes onboarding with defaults rather than abandoning it
            self._finish()
        else:
            super().keyPressEvent(event)
