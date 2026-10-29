"""
sleepguard_page.py — Media-aware SleepGuard control surface.

The page separates three concerns:
1. current protection and activity state;
2. what happens when the user is away;
3. what happens while media, lectures, or notes are open.

Playback never permanently disables SleepGuard: it holds power actions while
active, then applies a short post-media grace before the warning.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tracker.idle import get_idle_seconds
from tracker.sleepguard import SleepGuardController
from ui import design_system as ds
from ui.icons import get_pixmap
from ui.theme import ThemeManager
from ui.widgets.fluent import ToggleSwitch


class SleepGuardPage(QWidget):
    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None):
        super().__init__(parent)
        self._sleepguard = sleepguard
        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)
        self.on_data_changed()

        if self._sleepguard:
            self._sleepguard.media_state_changed.connect(lambda _info: self.on_data_changed())
            self._sleepguard.sleepguard_status_changed.connect(lambda _enabled: self.on_data_changed())

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(2000)
        self._refresh_timer.timeout.connect(self.on_data_changed)
        self._refresh_timer.start()

    # ── UI construction ───────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(*ds.PAGE_MARGINS)
        root.setSpacing(ds.PAGE_SECTION_SPACING)

        # ── Page header ───────────────────────────────────────────────────
        header = QHBoxLayout()
        text = QVBoxLayout()
        text.setSpacing(3)
        eyebrow = QLabel("MEDIA-AWARE PROTECTION")
        eyebrow.setObjectName("sg_eyebrow")
        title = QLabel("SleepGuard")
        title.setObjectName("page_title")
        subtitle = QLabel(
            "Power protection that distinguishes real inactivity from watching, "
            "lectures, and late-night reading."
        )
        subtitle.setObjectName("page_subtitle")
        subtitle.setWordWrap(True)
        text.addWidget(eyebrow)
        text.addWidget(title)
        text.addWidget(subtitle)
        header.addLayout(text, 1)

        # Status pill badges
        self._action_chip = QLabel("Lock")
        self._action_chip.setObjectName("sg_chip")
        self._threshold_chip = QLabel("30 min idle")
        self._threshold_chip.setObjectName("sg_chip")
        header.addWidget(self._action_chip, 0, Qt.AlignmentFlag.AlignTop)
        header.addWidget(self._threshold_chip, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 16)
        self._inner_layout.setSpacing(ds.PAGE_SECTION_SPACING)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._build_hero()
        self._build_activity_row()
        self._build_config_row()
        self._build_safety_card()

        from ui.widgets.circadian_section import CircadianSection

        self._circadian_section = CircadianSection()
        self._inner_layout.addWidget(self._circadian_section)
        self._inner_layout.addStretch()

    def _card(self, title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("sg_card")
        body = QVBoxLayout(card)
        body.setContentsMargins(*ds.CARD_MARGINS)
        body.setSpacing(12)
        heading = QLabel(title)
        heading.setObjectName("sg_card_title")
        body.addWidget(heading)
        if subtitle:
            desc = QLabel(subtitle)
            desc.setObjectName("sg_card_desc")
            desc.setWordWrap(True)
            body.addWidget(desc)
        return card, body

    def _build_hero(self) -> None:
        # Section eyebrow above the hero card
        section_eyebrow = QLabel("SLEEP PROTECTION")
        section_eyebrow.setObjectName("sg_section_eyebrow")
        self._inner_layout.addWidget(section_eyebrow)

        self._hero = QFrame()
        self._hero.setObjectName("sg_hero")
        self._hero.setProperty("state", "on")
        layout = QHBoxLayout(self._hero)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(24)

        # ── Left: status text block ───────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(6)

        self._status_kicker = QLabel("PROTECTION ACTIVE")
        self._status_kicker.setObjectName("sg_kicker")

        self._status_heading = QLabel("SleepGuard is watching for real inactivity")
        self._status_heading.setObjectName("sg_hero_title")
        self._status_heading.setWordWrap(True)

        self._status_desc = QLabel(
            "Intelligent power protection with real-time media awareness"
        )
        self._status_desc.setObjectName("sg_hero_subtitle")
        self._status_desc.setWordWrap(True)

        self._status_detail = QLabel(
            "Playback, lectures, and notes hold power actions. "
            "A short grace period runs after they end before any warning."
        )
        self._status_detail.setObjectName("sg_hero_desc")
        self._status_detail.setWordWrap(True)

        left.addWidget(self._status_kicker)
        left.addWidget(self._status_heading)
        left.addWidget(self._status_desc)
        left.addSpacing(4)
        left.addWidget(self._status_detail)

        # Status chips row
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self._state_chip = QLabel("Monitoring")
        self._state_chip.setObjectName("sg_state_chip")
        self._guard_chip = QLabel("Media guard ready")
        self._guard_chip.setObjectName("sg_state_chip")
        status_row.addWidget(self._state_chip)
        status_row.addWidget(self._guard_chip)
        status_row.addStretch()
        left.addSpacing(6)
        left.addLayout(status_row)

        layout.addLayout(left, 1)

        # ── Right: toggle ─────────────────────────────────────────────────
        toggle_col = QVBoxLayout()
        toggle_col.setSpacing(0)
        toggle_col.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(10)
        toggle_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        toggle_label = QLabel("Protection")
        toggle_label.setObjectName("sg_toggle_label")
        toggle_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._sg_check = ToggleSwitch()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
        self._sg_check.toggled.connect(self._on_sg_toggle)

        toggle_row.addWidget(toggle_label)
        toggle_row.addWidget(self._sg_check)
        toggle_col.addLayout(toggle_row)

        layout.addLayout(toggle_col, 0)
        self._inner_layout.addWidget(self._hero)

    def _build_activity_row(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)

        # ── Current activity card ─────────────────────────────────────────
        activity_card, activity_body = self._card("Current activity")
        activity_body.addSpacing(2)

        # Status indicator row with dot
        indicator_row = QHBoxLayout()
        indicator_row.setSpacing(10)
        indicator_row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._media_dot = QLabel()
        self._media_dot.setObjectName("sg_media_dot")
        self._media_dot.setFixedSize(10, 10)
        self._media_label = QLabel("No active media or lecture sessions")
        self._media_label.setObjectName("sg_media_value")
        self._media_label.setWordWrap(True)
        indicator_row.addWidget(self._media_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        indicator_row.addWidget(self._media_label, 1)
        activity_body.addLayout(indicator_row)

        self._media_detail = QLabel("Power actions are permitted after the idle threshold.")
        self._media_detail.setObjectName("sg_media_detail")
        self._media_detail.setWordWrap(True)
        activity_body.addWidget(self._media_detail)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(18)
        self._idle_value = QLabel("Idle 0m")
        self._idle_value.setObjectName("sg_meta_value")
        self._state_value = QLabel("Monitoring")
        self._state_value.setObjectName("sg_meta_value")
        meta_row.addWidget(self._idle_value)
        meta_row.addWidget(self._state_value)
        meta_row.addStretch()
        activity_body.addLayout(meta_row)
        activity_body.addStretch()
        row.addWidget(activity_card, 1)

        # ── Media guard explainer card ────────────────────────────────────
        guard_card, guard_body = self._card(
            "How the media guard works",
            "Holds are re-evaluated every second — not a permanent override.",
        )
        checks = [
            (
                "video",
                "Playback holds power actions",
                "YouTube, Netflix, VLC, and browser media keep SleepGuard in a hold state.",
            ),
            (
                "book",
                "Lectures and notes count",
                "OneNote, PDF readers, slide decks, course pages, and study notes pause the idle timer.",
            ),
            (
                "clock",
                "Grace period after media ends",
                "Once playback stops, a configurable grace period runs before the cancelable warning.",
            ),
        ]
        for icon_name, heading, body_text in checks:
            item = QHBoxLayout()
            item.setSpacing(12)
            item.setAlignment(Qt.AlignmentFlag.AlignTop)
            icon = QLabel()
            icon.setPixmap(get_pixmap(icon_name, ThemeManager.instance().color("accent"), 15))
            icon.setFixedSize(18, 18)
            item.addWidget(icon)
            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            h = QLabel(heading)
            h.setObjectName("sg_check_title")
            b = QLabel(body_text)
            b.setObjectName("sg_check_body")
            b.setWordWrap(True)
            text_col.addWidget(h)
            text_col.addWidget(b)
            item.addLayout(text_col, 1)
            guard_body.addLayout(item)
        guard_body.addStretch()
        row.addWidget(guard_card, 1)
        self._inner_layout.addLayout(row)

    def _build_config_row(self) -> None:
        row = QHBoxLayout()
        row.setSpacing(16)

        # ── Away config card ──────────────────────────────────────────────
        away_card, away_body = self._card(
            "When you are away",
            "Base inactivity threshold and the power action to execute.",
        )
        action_row = QHBoxLayout()
        action_text = QVBoxLayout()
        action_text.setSpacing(2)
        action_label = QLabel("Power action")
        action_label.setObjectName("sg_field_label")
        action_desc = QLabel("Runs only after the cancelable warning.")
        action_desc.setObjectName("sg_field_desc")
        action_text.addWidget(action_label)
        action_text.addWidget(action_desc)
        action_row.addLayout(action_text, 1)
        self._action_combo = QComboBox()
        self._action_combo.addItem("Lock computer", "lock")
        self._action_combo.addItem("Sleep", "sleep")
        self._action_combo.addItem("Hibernate", "hibernate")
        self._action_combo.addItem("Shut down", "shutdown")
        self._action_combo.addItem("Cancel action", "cancel")
        self._action_combo.setFixedWidth(150)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        action_row.addWidget(self._action_combo)
        away_body.addLayout(action_row)

        away_body.addWidget(self._divider())
        timeout_row = QHBoxLayout()
        timeout_text = QVBoxLayout()
        timeout_text.setSpacing(2)
        timeout_label = QLabel("Idle threshold")
        timeout_label.setObjectName("sg_field_label")
        timeout_desc = QLabel("Consecutive minutes without keyboard or mouse input.")
        timeout_desc.setObjectName("sg_field_desc")
        timeout_text.addWidget(timeout_label)
        timeout_text.addWidget(timeout_desc)
        timeout_row.addLayout(timeout_text, 1)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120)
        self._timeout_spin.setSuffix(" min")
        self._timeout_spin.setFixedWidth(110)
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        timeout_row.addWidget(self._timeout_spin)
        away_body.addLayout(timeout_row)
        away_body.addLayout(self._presets([15, 30, 45, 60], self._timeout_spin))
        away_body.addStretch()
        row.addWidget(away_card, 1)

        # ── Media config card ─────────────────────────────────────────────
        media_card, media_body = self._card(
            "When media is playing",
            "A hold keeps the PC awake while media, lectures, or notes are active.",
        )
        grace_row = QHBoxLayout()
        grace_text = QVBoxLayout()
        grace_text.setSpacing(2)
        grace_label = QLabel("Post-media grace")
        grace_label.setObjectName("sg_field_label")
        grace_desc = QLabel("Extra time after playback stops before the warning appears.")
        grace_desc.setObjectName("sg_field_desc")
        grace_text.addWidget(grace_label)
        grace_text.addWidget(grace_desc)
        grace_row.addLayout(grace_text, 1)
        self._grace_spin = QSpinBox()
        self._grace_spin.setRange(1, 30)
        self._grace_spin.setSuffix(" min")
        self._grace_spin.setFixedWidth(110)
        self._grace_spin.valueChanged.connect(self._on_grace_changed)
        grace_row.addWidget(self._grace_spin)
        media_body.addLayout(grace_row)
        media_body.addLayout(self._presets([2, 5, 10], self._grace_spin))

        media_body.addWidget(self._divider())
        self._media_policy = QLabel(
            "While media is active, no power action is executed — even after the idle "
            "threshold. Monitoring resumes automatically when the media session ends."
        )
        self._media_policy.setObjectName("sg_policy")
        self._media_policy.setWordWrap(True)
        media_body.addWidget(self._media_policy)
        media_body.addStretch()
        row.addWidget(media_card, 1)
        self._inner_layout.addLayout(row)

    def _build_safety_card(self) -> None:
        card, body = self._card("Warning and safety")

        desc = self._label(
            "Any mouse movement or keypress during the 60-second warning cancels the action. "
            "SleepGuard also holds off for the first 30 seconds after launch to avoid "
            "triggering on startup.",
            "sg_card_desc",
        )
        body.addWidget(desc)

        body.addWidget(self._divider())

        test_row = QHBoxLayout()
        test_text = QVBoxLayout()
        test_text.setSpacing(2)
        test_text.addWidget(self._label("Preview the warning", "sg_field_label"))
        test_text.addWidget(
            self._label(
                "Open the cancelable 60-second dialog without affecting the idle timer.",
                "sg_field_desc",
            )
        )
        test_row.addLayout(test_text, 1)
        self._test_btn = QPushButton("Test warning")
        self._test_btn.setObjectName("sg_test_btn")
        self._test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test_warning)
        test_row.addWidget(self._test_btn)
        body.addLayout(test_row)
        self._inner_layout.addWidget(card)

    def _label(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setObjectName("sg_divider")
        line.setFixedHeight(1)
        return line

    def _presets(self, minutes: list[int], target: QSpinBox) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self._label("Presets", "sg_field_desc"))
        for value in minutes:
            btn = QPushButton(f"{value}m")
            btn.setObjectName("sg_preset_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, m=value: target.setValue(m))
            row.addWidget(btn)
        row.addStretch()
        return row

    # ── state / settings ──────────────────────────────────────────────────

    def _on_sg_toggle(self, checked: bool) -> None:
        if self._sleepguard:
            self._sleepguard.set_enabled(checked)
        self.on_data_changed()

    def _on_action_changed(self) -> None:
        act = self._action_combo.currentData()
        if act and self._sleepguard:
            self._sleepguard._settings.sleepguard_action = act
            self.on_data_changed()

    def _on_timeout_changed(self, val: int) -> None:
        if self._sleepguard:
            self._sleepguard._settings.idle_timeout_minutes = val
            self.on_data_changed()

    def _on_grace_changed(self, val: int) -> None:
        if self._sleepguard:
            self._sleepguard._settings.media_grace_minutes = val
            self.on_data_changed()

    def _on_test_warning(self) -> None:
        from core.logger import logger
        from ui.widgets.countdown_dialog import ShutdownCountdownDialog

        action = "lock"
        if self._action_combo.currentData():
            action = self._action_combo.currentData()
        elif self._sleepguard:
            action = getattr(self._sleepguard._settings, "sleepguard_action", "lock")

        if getattr(self, "_test_dialog", None) is not None:
            try:
                self._test_dialog.close()
            except Exception:
                pass
            self._test_dialog = None

        parent_window = self.window() if (self.window() and self.window() is not self) else None
        dialog = ShutdownCountdownDialog(
            countdown_seconds=60,
            action=action,
            parent=parent_window,
            is_test=True,
        )
        self._test_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, "_test_dialog", None))
        dialog.start_countdown()
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        logger.info("[SLEEPGUARD_PAGE] Test warning preview opened.")

    def on_data_changed(self) -> None:
        sg = self._sleepguard
        enabled = sg.is_enabled if sg else False
        action = getattr(getattr(sg, "_settings", None), "sleepguard_action", "lock") if sg else "lock"
        timeout_m = getattr(getattr(sg, "_settings", None), "idle_timeout_minutes", 30) if sg else 30
        grace_m = getattr(getattr(sg, "_settings", None), "media_grace_minutes", 5) if sg else 5

        self._hero.setProperty("state", "on" if enabled else "off")
        self._hero.style().unpolish(self._hero)
        self._hero.style().polish(self._hero)

        if enabled:
            self._status_kicker.setText("PROTECTION ACTIVE")
            self._status_heading.setText("SleepGuard is watching for real inactivity")
            self._status_detail.setText(
                f"After {timeout_m} minutes without input, SleepGuard warns before "
                f"'{action.title()}'. Playback, lectures, and notes hold the timer."
            )
            self._state_chip.setText("Monitoring")
            self._state_chip.setProperty("state", "active")
        else:
            self._status_kicker.setText("PROTECTION PAUSED")
            self._status_heading.setText("SleepGuard is not enforcing power actions")
            self._status_detail.setText(
                "Protection is paused. Enable it to resume media-aware inactivity handling."
            )
            self._state_chip.setText("Paused")
            self._state_chip.setProperty("state", "paused")

        self._state_chip.style().unpolish(self._state_chip)
        self._state_chip.style().polish(self._state_chip)

        if sg:
            self._sg_check.blockSignals(True)
            self._sg_check.setChecked(enabled)
            self._sg_check.blockSignals(False)
            idx = self._action_combo.findData(action)
            if idx >= 0:
                self._action_combo.blockSignals(True)
                self._action_combo.setCurrentIndex(idx)
                self._action_combo.blockSignals(False)
            self._timeout_spin.blockSignals(True)
            self._timeout_spin.setValue(timeout_m)
            self._timeout_spin.blockSignals(False)
            self._grace_spin.blockSignals(True)
            self._grace_spin.setValue(grace_m)
            self._grace_spin.blockSignals(False)

        guard_active = bool(sg and sg.media_guard_active)
        self._guard_chip.setText("Holding power action" if guard_active else "Media guard ready")
        self._guard_chip.setProperty("state", "hold" if guard_active else "ready")
        self._guard_chip.style().unpolish(self._guard_chip)
        self._guard_chip.style().polish(self._guard_chip)

        # Media dot indicator
        self._media_dot.setProperty("active", "true" if guard_active else "false")
        self._media_dot.style().unpolish(self._media_dot)
        self._media_dot.style().polish(self._media_dot)

        if sg:
            label = sg.media_guard_label
            self._media_label.setText(label)
            if guard_active:
                self._media_detail.setText(
                    "Power actions are suppressed while this session is active."
                )
            else:
                self._media_detail.setText(
                    f"No active hold. After {grace_m} min of post-media grace, the warning may appear."
                )
            state = sg.current_state.value.replace("_", " ").title()
            self._state_value.setText(state)
            idle_s = get_idle_seconds()
            if idle_s < 5:
                self._idle_value.setText("Active now")
            else:
                self._idle_value.setText(f"Idle {int(idle_s // 60)}m {int(idle_s % 60):02d}s")
        else:
            self._media_label.setText("SleepGuard controller not connected")
            self._media_detail.setText("Open Settings to configure protection.")
            self._state_value.setText("Unavailable")
            self._idle_value.setText("—")

        self._action_chip.setText(action.title())
        self._threshold_chip.setText(f"{timeout_m} min idle")

    # ── theme ─────────────────────────────────────────────────────────────

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        text = tm.color("text_main")
        sub = tm.color("text_sub")
        muted = tm.color("text_muted")
        border = tm.color("border")
        accent = tm.color("accent")

        # Semantic chip colours
        green_bg   = "rgba(52,199,89,0.14)"   if is_dark else "rgba(52,199,89,0.10)"
        green_fg   = "#34C759"                 if is_dark else "#1E8742"
        green_bd   = "rgba(52,199,89,0.35)"   if is_dark else "rgba(52,199,89,0.30)"
        amber_bg   = "rgba(255,159,10,0.14)"  if is_dark else "rgba(255,149,0,0.10)"
        amber_fg   = "#FF9F0A"                 if is_dark else "#B85E00"
        amber_bd   = "rgba(255,159,10,0.35)"  if is_dark else "rgba(255,149,0,0.30)"

        self.setStyleSheet(f"""
            /* ── Page header ─────────────────────────────────────────────── */
            QLabel#page_title      {{ font-size: 26px; font-weight: 700; color: {text}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle   {{ font-size: 13px; color: {sub}; }}
            QLabel#sg_eyebrow      {{ color: {tm.color('accent_tint_text')}; font-size: 9px; font-weight: 700; letter-spacing: 1.5px; }}

            /* Pill badges in header */
            QLabel#sg_chip {{
                background: {tm.color('surface')};
                border: 1px solid {border};
                border-radius: 999px;
                color: {sub};
                padding: 5px 13px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}

            /* ── Section eyebrow ─────────────────────────────────────────── */
            QLabel#sg_section_eyebrow {{
                color: {muted};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.8px;
                margin-bottom: 2px;
            }}

            /* ── Hero card ───────────────────────────────────────────────── */
            QFrame#sg_hero {{
                background: {tm.color('surface_elevated')};
                border: 1px solid {border};
                border-radius: 18px;
            }}
            QFrame#sg_hero[state="on"]  {{ border-color: {tm.color('accent_tint_border')}; }}
            QFrame#sg_hero[state="off"] {{ border-color: {border}; }}

            QLabel#sg_kicker {{
                color: {accent};
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1.6px;
            }}
            QLabel#sg_hero_title {{
                color: {text};
                font-size: 22px;
                font-weight: 700;
                letter-spacing: -0.3px;
            }}
            QLabel#sg_hero_subtitle {{
                color: {sub};
                font-size: 12px;
                font-weight: 500;
            }}
            QLabel#sg_hero_desc  {{ color: {muted}; font-size: 11px; }}
            QLabel#sg_toggle_label {{
                color: {sub};
                font-size: 11px;
                font-weight: 600;
            }}

            /* Status chips inside hero */
            QLabel#sg_state_chip {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 999px;
                color: {muted};
                padding: 4px 12px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.2px;
            }}
            QLabel#sg_state_chip[state="active"] {{
                color: {green_fg};
                border-color: {green_bd};
                background: {green_bg};
            }}
            QLabel#sg_state_chip[state="hold"] {{
                color: {amber_fg};
                border-color: {amber_bd};
                background: {amber_bg};
            }}
            QLabel#sg_state_chip[state="paused"] {{
                color: {muted};
                border-color: {border};
                background: {tm.color('surface_secondary')};
            }}

            /* ── Content cards ───────────────────────────────────────────── */
            QFrame#sg_card {{
                background: {tm.color('surface')};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QLabel#sg_card_title {{ color: {text}; font-size: 14px; font-weight: 700; }}
            QLabel#sg_card_desc  {{ color: {sub}; font-size: 11px; }}

            /* ── Activity card ───────────────────────────────────────────── */
            QLabel#sg_media_dot {{
                border-radius: 5px;
                background: {muted};
            }}
            QLabel#sg_media_dot[active="true"] {{
                background: {green_fg};
            }}
            QLabel#sg_media_value  {{ color: {text}; font-size: 15px; font-weight: 700; }}
            QLabel#sg_media_detail {{ color: {sub}; font-size: 11px; }}
            QLabel#sg_meta_value   {{ color: {muted}; font-size: 10px; font-weight: 600; }}

            /* ── Media guard explainer ───────────────────────────────────── */
            QLabel#sg_check_title {{ color: {text}; font-size: 12px; font-weight: 700; }}
            QLabel#sg_check_body  {{ color: {sub}; font-size: 11px; }}

            /* ── Config fields ───────────────────────────────────────────── */
            QLabel#sg_field_label {{ color: {text}; font-size: 12px; font-weight: 700; }}
            QLabel#sg_field_desc  {{ color: {muted}; font-size: 10px; }}
            QLabel#sg_policy {{
                color: {sub};
                background: {tm.color('surface_secondary')};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 10px 14px;
                font-size: 11px;
            }}
            QFrame#sg_divider {{ background: {border}; }}

            QPushButton#sg_preset_btn {{
                background: transparent;
                border: 1px solid {border};
                border-radius: 999px;
                color: {sub};
                padding: 4px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton#sg_preset_btn:hover {{ color: {text}; border-color: {accent}; }}

            QPushButton#sg_test_btn {{
                background: {tm.color('accent_tint_bg')};
                border: 1px solid {tm.color('accent_tint_border')};
                border-radius: 10px;
                color: {tm.color('accent_tint_text')};
                padding: 8px 18px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton#sg_test_btn:hover {{ background: {tm.color('accent_tint_border')}; }}

            QComboBox, QSpinBox {{
                background: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 9px;
                padding: 6px 9px;
                color: {text};
                font-size: 11px;
                font-weight: 600;
            }}
            QComboBox:hover, QSpinBox:hover {{ border-color: {accent}; }}
        """)
