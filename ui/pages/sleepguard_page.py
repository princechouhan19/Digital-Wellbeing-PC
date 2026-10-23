"""
sleepguard_page.py — Premium SleepGuard Power & Inactivity Management UI.
Redesigned with calm obsidian aesthetic, clear arming banner, media awareness indicators,
and precise inactivity configuration.
"""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)
from tracker.sleepguard import SleepGuardController
from ui.widgets.fluent import ToggleSwitch


class SleepGuardPage(QWidget):
    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None):
        super().__init__(parent)
        self._sleepguard = sleepguard
        self._setup_ui()

        from ui.theme import ThemeManager
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 28, 36, 28)
        main_layout.setSpacing(20)

        # Header Title
        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        pill_row = QHBoxLayout()
        pill = QLabel("● SYSTEM SLEEPGUARD")
        pill.setObjectName("section_pill")
        pill.setStyleSheet("""
            color: #38BDF8;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.2px;
            background: rgba(100, 210, 255, 0.12);
            border: 1px solid rgba(100, 210, 255, 0.30);
            border-radius: 12px;
            padding: 3px 10px;
        """)
        pill_row.addWidget(pill)
        pill_row.addStretch()
        title_box.addLayout(pill_row)

        title = QLabel("SleepGuard Protection")
        title.setObjectName("page_title")
        subtitle = QLabel("Monitors system inactivity to safely transition power state during bedtime and protect sleep habits.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        main_layout.addLayout(title_box)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 4, 0, 20)
        inner_layout.setSpacing(20)
        scroll.setWidget(inner)
        main_layout.addWidget(scroll, 1)

        # 1. Hero Status Card
        self._status_card = QFrame()
        self._status_card.setObjectName("status_card")
        status_l = QHBoxLayout(self._status_card)
        status_l.setContentsMargins(24, 20, 24, 20)
        status_l.setSpacing(20)

        status_text_col = QVBoxLayout()
        status_text_col.setSpacing(4)

        self._status_heading = QLabel("SleepGuard armed")
        self._status_heading.setObjectName("status_heading")
        
        self._status_desc = QLabel("Automatic power transitions on extended inactivity are armed.")
        self._status_desc.setObjectName("status_desc")
        self._status_desc.setWordWrap(True)

        status_text_col.addWidget(self._status_heading)
        status_text_col.addWidget(self._status_desc)
        status_l.addLayout(status_text_col, 1)

        self._sg_check = ToggleSwitch()
        if self._sleepguard:
            self._sg_check.setChecked(self._sleepguard.is_enabled)
        self._sg_check.toggled.connect(self._on_sg_toggle)
        status_l.addWidget(self._sg_check, 0, Qt.AlignmentFlag.AlignVCenter)

        inner_layout.addWidget(self._status_card)

        # 2. Main Content Grid (Two columns)
        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        # Left Column: Configuration Card
        config_card = QFrame()
        config_card.setObjectName("v2_card")
        config_l = QVBoxLayout(config_card)
        config_l.setContentsMargins(24, 22, 24, 22)
        config_l.setSpacing(18)

        cfg_hdr = QLabel("Power & timeout configuration")
        cfg_hdr.setObjectName("section_header")
        config_l.addWidget(cfg_hdr)

        # Action Dropdown Row
        act_row = QHBoxLayout()
        act_col = QVBoxLayout()
        act_col.setSpacing(2)
        act_lbl = QLabel("Inactivity Power Action")
        act_lbl.setObjectName("setting_label")
        act_desc = QLabel("Action executed when idle timer countdown completes")
        act_desc.setObjectName("setting_desc")
        act_col.addWidget(act_lbl)
        act_col.addWidget(act_desc)
        act_row.addLayout(act_col, 1)

        self._action_combo = QComboBox()
        self._action_combo.addItem("Lock Computer", "lock")
        self._action_combo.addItem("Sleep", "sleep")
        self._action_combo.addItem("Hibernate", "hibernate")
        self._action_combo.addItem("Shut Down", "shutdown")
        self._action_combo.addItem("Cancel Action", "cancel")
        self._action_combo.setFixedWidth(160)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        act_row.addWidget(self._action_combo)
        config_l.addLayout(act_row)

        line1 = QFrame()
        line1.setObjectName("card_divider")
        line1.setFixedHeight(1)
        config_l.addWidget(line1)

        # Timeout Row
        out_row = QHBoxLayout()
        out_col = QVBoxLayout()
        out_col.setSpacing(2)
        out_lbl = QLabel("Inactivity Threshold")
        out_lbl.setObjectName("setting_label")
        out_desc = QLabel("Consecutive minutes of zero input before countdown")
        out_desc.setObjectName("setting_desc")
        out_col.addWidget(out_lbl)
        out_col.addWidget(out_desc)
        out_row.addLayout(out_col, 1)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 120)
        self._timeout_spin.setSuffix(" min")
        self._timeout_spin.setFixedWidth(110)
        self._timeout_spin.setValue(30)
        self._timeout_spin.valueChanged.connect(self._on_timeout_changed)
        out_row.addWidget(self._timeout_spin)
        config_l.addLayout(out_row)

        line2 = QFrame()
        line2.setObjectName("card_divider")
        line2.setFixedHeight(1)
        config_l.addWidget(line2)

        # Media Grace Period Row
        grace_row = QHBoxLayout()
        grace_col = QVBoxLayout()
        grace_col.setSpacing(2)
        grace_lbl = QLabel("Media Grace Period")
        grace_lbl.setObjectName("setting_label")
        grace_desc = QLabel("Additional time before warning when audio/video is detected")
        grace_desc.setObjectName("setting_desc")
        grace_col.addWidget(grace_lbl)
        grace_col.addWidget(grace_desc)
        grace_row.addLayout(grace_col, 1)

        self._grace_spin = QSpinBox()
        self._grace_spin.setRange(1, 30)
        self._grace_spin.setSuffix(" min")
        self._grace_spin.setFixedWidth(110)
        self._grace_spin.setValue(5)
        self._grace_spin.valueChanged.connect(self._on_grace_changed)
        grace_row.addWidget(self._grace_spin)
        config_l.addLayout(grace_row)

        # Grace Quick Presets
        grace_preset_row = QHBoxLayout()
        grace_preset_row.setSpacing(8)
        grace_preset_lbl = QLabel("Quick Presets:")
        grace_preset_lbl.setObjectName("setting_desc")
        grace_preset_row.addWidget(grace_preset_lbl)
        for minutes in [2, 5, 10]:
            btn = QPushButton(f"{minutes}m")
            btn.setObjectName("preset_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=minutes: self._grace_spin.setValue(m))
            grace_preset_row.addWidget(btn)
        grace_preset_row.addStretch()
        config_l.addLayout(grace_preset_row)

        line2b = QFrame()
        line2b.setObjectName("card_divider")
        line2b.setFixedHeight(1)
        config_l.addWidget(line2b)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_lbl = QLabel("Quick Presets:")
        preset_lbl.setObjectName("setting_desc")
        preset_row.addWidget(preset_lbl)

        for minutes in [15, 30, 45, 60]:
            btn = QPushButton(f"{minutes}m")
            btn.setObjectName("preset_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, m=minutes: self._timeout_spin.setValue(m))
            preset_row.addWidget(btn)
        preset_row.addStretch()
        config_l.addLayout(preset_row)

        line2 = QFrame()
        line2.setObjectName("card_divider")
        line2.setFixedHeight(1)
        config_l.addWidget(line2)

        # Test Action Row
        test_row = QHBoxLayout()
        test_col = QVBoxLayout()
        test_col.setSpacing(2)
        test_lbl = QLabel("Test Countdown Warning")
        test_lbl.setObjectName("setting_label")
        test_desc = QLabel("Displays the 60-second cancelable dialog to preview the experience")
        test_desc.setObjectName("setting_desc")
        test_col.addWidget(test_lbl)
        test_col.addWidget(test_desc)
        test_row.addLayout(test_col, 1)

        self._test_btn = QPushButton("Test Warning")
        self._test_btn.setObjectName("test_action_btn")
        self._test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._test_btn.clicked.connect(self._on_test_warning)
        test_row.addWidget(self._test_btn)
        config_l.addLayout(test_row)

        config_l.addStretch()
        content_row.addWidget(config_card, 3)

        # Right Column: Safety & Awareness Card
        safety_card = QFrame()
        safety_card.setObjectName("v2_card")
        safety_l = QVBoxLayout(safety_card)
        safety_l.setContentsMargins(24, 22, 24, 22)
        safety_l.setSpacing(16)

        safe_hdr = QLabel("SAFETY & AWARENESS CHECKS")
        safe_hdr.setObjectName("section_header")
        safety_l.addWidget(safe_hdr)

        # Media status banner
        self._media_lbl = QLabel("Media Playback Detection: Idle / Not playing")
        self._media_lbl.setObjectName("media_lbl")
        self._media_lbl.setWordWrap(True)
        safety_l.addWidget(self._media_lbl)

        # Safety Rules explanation
        from ui.icons import get_pixmap
        checks = [
            ("video", "Media Grace Period", "When inactivity is detected while audio or video plays, SleepGuard grants one additional grace period before warning. Media never disables SleepGuard permanently."),
            ("monitor", "Fullscreen Awareness", "Prevents unwanted power interruptions during presentations or gaming sessions."),
            ("power", "Cancellation Grace", "Any mouse movement or keypress during the 60-second warning countdown immediately aborts the power action."),
            ("moon", "Startup Grace Period", "SleepGuard remains dormant for the first 30 seconds after the application starts.")
        ]

        for icon_name, check_title, check_body in checks:
            item_row = QHBoxLayout()
            item_row.setSpacing(12)
            item_row.setAlignment(Qt.AlignmentFlag.AlignTop)

            ico_lbl = QLabel()
            ico_lbl.setPixmap(get_pixmap(icon_name, "#0A84FF", 16))
            ico_lbl.setFixedSize(20, 20)
            ico_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item_row.addWidget(ico_lbl)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            h = QLabel(check_title)
            h.setObjectName("safety_item_title")
            b = QLabel(check_body)
            b.setObjectName("safety_item_body")
            b.setWordWrap(True)
            text_col.addWidget(h)
            text_col.addWidget(b)
            item_row.addLayout(text_col, 1)

            safety_l.addLayout(item_row)

        safety_l.addStretch()
        content_row.addWidget(safety_card, 2)

        inner_layout.addLayout(content_row)

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        tm = ThemeManager.instance()
        title_col = tm.color("text_main")
        sub_col = tm.color("text_sub")
        card_bg = tm.color("surface_elevated") if not is_dark else "#1E1E20"
        border_col = tm.color("border")
        divider_col = "rgba(0, 0, 0, 0.06)" if not is_dark else "rgba(255, 255, 255, 0.06)"
        media_bg = "rgba(0, 0, 0, 0.03)" if not is_dark else "rgba(255, 255, 255, 0.03)"
        preset_bg = "rgba(0, 0, 0, 0.04)" if not is_dark else "rgba(255, 255, 255, 0.04)"
        input_bg = tm.color("input_bg")
        input_border = tm.color("input_border")
        accent = tm.color("accent")

        self.setStyleSheet(f"""
            QLabel#page_title {{ font-size: 26px; font-weight: 700; color: {title_col}; letter-spacing: -0.5px; }}
            QLabel#page_subtitle {{ font-size: 14px; font-weight: 500; color: {sub_col}; }}
            QLabel#section_header {{ font-size: 11px; font-weight: 700; color: {accent}; letter-spacing: 1.5px; text-transform: uppercase; }}
            QLabel#setting_label {{ font-weight: 700; color: {title_col}; font-size: 14px; }}
            QLabel#setting_desc {{ color: {sub_col}; font-size: 12px; }}
            QLabel#media_lbl {{
                background: {media_bg};
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 10px 14px;
                color: {sub_col};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#safety_item_title {{
                color: {title_col};
                font-size: 13px;
                font-weight: 700;
            }}
            QLabel#safety_item_body {{
                color: {sub_col};
                font-size: 12px;
                line-height: 1.4;
            }}
            QFrame#v2_card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 14px;
            }}
            QFrame#card_divider {{
                background: {divider_col};
            }}
            QPushButton#preset_btn {{
                background: {preset_bg};
                color: {sub_col};
                border: 1px solid {border_col};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#preset_btn:hover {{
                background: rgba(10, 132, 255, 0.14);
                color: {accent};
                border-color: rgba(10, 132, 255, 0.35);
            }}
            QPushButton#test_action_btn {{
                background: rgba(255, 159, 10, 0.10);
                color: #FF9F0A;
                border: 1px solid rgba(255, 159, 10, 0.30);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton#test_action_btn:hover {{
                background: rgba(255, 159, 10, 0.18);
                border-color: rgba(255, 159, 10, 0.45);
            }}
            QComboBox, QSpinBox {{
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 6px 10px;
                color: {title_col};
                font-size: 13px;
                font-weight: 600;
            }}
            QComboBox:hover, QSpinBox:hover {{
                border: 1px solid {accent};
            }}
            QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                border: none;
                background: transparent;
            }}
        """)
        self.on_data_changed()

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

        # Determine configured action
        action = "lock"
        if hasattr(self, "_action_combo") and self._action_combo.currentData():
            action = self._action_combo.currentData()
        elif self._sleepguard and hasattr(self._sleepguard, "_settings"):
            action = getattr(self._sleepguard._settings, "sleepguard_action", "lock")

        logger.info("[SLEEPGUARD_PAGE] Opening Test Warning preview dialog (action='%s')", action)

        # Close existing test dialog if one is already active
        if getattr(self, "_test_dialog", None) is not None:
            try:
                self._test_dialog.close()
            except Exception:
                pass
            self._test_dialog = None

        # Instantiate dedicated test preview dialog with full 60-second countdown
        parent_window = self.window() if (self.window() and self.window() is not self) else None
        dialog = ShutdownCountdownDialog(
            countdown_seconds=60,
            action=action,
            parent=parent_window,
            is_test=True,
        )
        self._test_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, "_test_dialog", None))

        # Start countdown immediately and show non-blocking on the Qt event loop
        dialog.start_countdown()
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        logger.info("[SLEEPGUARD_PAGE] Test Warning dialog shown immediately (is_test=True, countdown=60s).")

    def on_data_changed(self) -> None:
        enabled = self._sleepguard.is_enabled if self._sleepguard else False
        act = self._sleepguard._settings.sleepguard_action if self._sleepguard else "lock"
        timeout_m = self._sleepguard._settings.idle_timeout_minutes if self._sleepguard else 30

        act_title = act.title()

        if enabled:
            self._status_card.setStyleSheet("""
                QFrame#status_card {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #061A14, stop:0.5 #0B221A, stop:1 #0A1B16);
                    border: 1px solid rgba(10, 132, 255, 0.35);
                    border-radius: 14px;
                }
                QLabel#status_heading {
                    color: #0A84FF;
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 0.8px;
                }
                QLabel#status_desc {
                    color: #A1A1A6;
                    font-size: 13px;
                }
            """)
            self._status_heading.setText("● SLEEPGUARD ARMED & MONITORING")
            self._status_desc.setText(
                f"Your PC will automatically execute '{act_title}' after {timeout_m} minutes of uninterrupted inactivity."
            )
        else:
            self._status_card.setStyleSheet("""
                QFrame#status_card {
                    background: #1E1E20;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 14px;
                }
                QLabel#status_heading {
                    color: #6E6E73;
                    font-size: 16px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }
                QLabel#status_desc {
                    color: #6E6E73;
                    font-size: 13px;
                }
            """)
            self._status_heading.setText("○ SLEEPGUARD STANDBY / DISABLED")
            self._status_desc.setText(
                "Automatic power transitions on extended inactivity are currently disabled. Toggle to arm."
            )

        if self._sleepguard:
            self._sg_check.blockSignals(True)
            self._sg_check.setChecked(self._sleepguard.is_enabled)
            self._sg_check.blockSignals(False)

            idx = self._action_combo.findData(act)
            if idx >= 0:
                self._action_combo.blockSignals(True)
                self._action_combo.setCurrentIndex(idx)
                self._action_combo.blockSignals(False)

            self._timeout_spin.blockSignals(True)
            self._timeout_spin.setValue(timeout_m)
            self._timeout_spin.blockSignals(False)

            grace_m = getattr(self._sleepguard._settings, "media_grace_minutes", 5) if (self._sleepguard and hasattr(self._sleepguard, "_settings")) else 5
            self._grace_spin.blockSignals(True)
            self._grace_spin.setValue(grace_m)
            self._grace_spin.blockSignals(False)

            media = self._sleepguard.current_media
            if media and media.is_playing:
                self._media_lbl.setText(
                    f"\u25cf Media Playback Active: {media.display_name}\n"
                    "SleepGuard continues monitoring inactivity while media plays "
                    "and allows one short grace period before warning."
                )
                self._media_lbl.setStyleSheet("""
                    background-color: rgba(10, 132, 255, 0.12);
                    color: #0A84FF;
                    border: 1px solid rgba(10, 132, 255, 0.32);
                    border-radius: 10px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 12px 16px;
                """)
            else:
                self._media_lbl.setText("○ Media Playback Detection: Idle / Not playing")
                self._media_lbl.setStyleSheet("""
                    background-color: rgba(255, 255, 255, 0.03);
                    color: #A1A1A6;
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    border-radius: 10px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 12px 16px;
                """)
