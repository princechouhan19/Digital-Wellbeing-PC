"""
circadian_section.py — SleepGuard page card for evening display warm-up.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTime, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)

from protection.circadian import CircadianController
from settings.manager import SettingsManager
from ui.theme import ThemeManager
from ui.widgets.fluent import ToggleSwitch


class CircadianSection(QFrame):
    """Evening colour-temperature schedule linked to the SleepGuard bedtime."""

    def __init__(self, controller: Optional[CircadianController] = None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("v2_card")
        self._sm = SettingsManager()
        self._controller = controller or CircadianController.instance()
        self._setup_ui()
        self._load_values()
        self._controller.state_changed.connect(self._on_state)
        try:
            self._controller.tick()
            self._on_state(self._controller.current_state().to_dict())
        except Exception:
            pass
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel("Circadian display warm-up")
        title.setObjectName("section_header")
        desc = QLabel(
            "Softly warms the display before bedtime using the SleepGuard schedule. "
            "Uses reversible gamma ramps — no registry or Night Light changes."
        )
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        text_col.addWidget(title)
        text_col.addWidget(desc)
        header.addLayout(text_col, 1)

        self._toggle = ToggleSwitch()
        self._toggle.toggled.connect(self._on_toggle)
        header.addWidget(self._toggle, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self._status = QLabel("Display warm-up is off")
        self._status.setObjectName("circadian_status")
        layout.addWidget(self._status)

        # Bedtime window
        bedtime_row = QHBoxLayout()
        bedtime_row.setSpacing(10)

        self._bedtime_start = QTimeEdit()
        self._bedtime_start.setDisplayFormat("HH:mm")
        self._bedtime_start.setFixedWidth(96)
        self._bedtime_start.timeChanged.connect(self._on_bedtime_changed)

        self._bedtime_end = QTimeEdit()
        self._bedtime_end.setDisplayFormat("HH:mm")
        self._bedtime_end.setFixedWidth(96)
        self._bedtime_end.timeChanged.connect(self._on_bedtime_changed)

        bedtime_row.addWidget(QLabel("Bedtime"))
        bedtime_row.addWidget(self._bedtime_start)
        bedtime_row.addWidget(QLabel("Wake"))
        bedtime_row.addWidget(self._bedtime_end)
        bedtime_row.addStretch()
        layout.addLayout(bedtime_row)

        # Lead time + target temperature
        tuning_row = QHBoxLayout()
        tuning_row.setSpacing(10)

        tuning_row.addWidget(QLabel("Start early"))
        self._lead_spin = QSpinBox()
        self._lead_spin.setRange(0, 360)
        self._lead_spin.setSingleStep(15)
        self._lead_spin.setSuffix(" min")
        self._lead_spin.setFixedWidth(104)
        self._lead_spin.valueChanged.connect(self._on_lead_changed)
        tuning_row.addWidget(self._lead_spin)

        tuning_row.addSpacing(12)
        tuning_row.addWidget(QLabel("Warmth"))
        self._kelvin_combo = QComboBox()
        for label, kelvin in (
            ("Subtle · 4500 K", 4500),
            ("Balanced · 3400 K", 3400),
            ("Warm · 2700 K", 2700),
            ("Candle · 2200 K", 2200),
        ):
            self._kelvin_combo.addItem(label, kelvin)
        self._kelvin_combo.setFixedWidth(170)
        self._kelvin_combo.currentIndexChanged.connect(self._on_kelvin_changed)
        tuning_row.addWidget(self._kelvin_combo)
        tuning_row.addStretch()
        layout.addLayout(tuning_row)

    # ── state ───────────────────────────────────────────────────────────────

    def _load_values(self) -> None:
        self._toggle.blockSignals(True)
        self._toggle.setChecked(self._sm.circadian_enabled)
        self._toggle.blockSignals(False)

        self._bedtime_start.blockSignals(True)
        self._bedtime_end.blockSignals(True)
        start = self._sm.bedtime_start.split(":")
        end = self._sm.bedtime_end.split(":")
        try:
            self._bedtime_start.setTime(QTime(int(start[0]), int(start[1])))
            self._bedtime_end.setTime(QTime(int(end[0]), int(end[1])))
        except Exception:
            self._bedtime_start.setTime(QTime(23, 0))
            self._bedtime_end.setTime(QTime(6, 0))
        self._bedtime_start.blockSignals(False)
        self._bedtime_end.blockSignals(False)

        self._lead_spin.blockSignals(True)
        self._lead_spin.setValue(self._sm.circadian_lead_minutes)
        self._lead_spin.blockSignals(False)

        idx = self._kelvin_combo.findData(self._sm.circadian_target_kelvin)
        if idx < 0:
            idx = 1
        self._kelvin_combo.blockSignals(True)
        self._kelvin_combo.setCurrentIndex(idx)
        self._kelvin_combo.blockSignals(False)

    def _on_toggle(self, enabled: bool) -> None:
        self._sm.circadian_enabled = enabled
        if enabled and not self._controller.is_running:
            self._controller.start()
        self._controller.tick()

    def _on_bedtime_changed(self) -> None:
        self._sm.bedtime_start = self._bedtime_start.time().toString("HH:mm")
        self._sm.bedtime_end = self._bedtime_end.time().toString("HH:mm")
        self._controller.tick()

    def _on_lead_changed(self, value: int) -> None:
        self._sm.circadian_lead_minutes = value
        self._controller.tick()

    def _on_kelvin_changed(self, index: int) -> None:
        kelvin = self._kelvin_combo.itemData(index)
        if kelvin:
            self._sm.circadian_target_kelvin = int(kelvin)
            self._controller.tick()

    def _on_state(self, state: dict) -> None:
        phase = state.get("phase", "off")
        kelvin = state.get("kelvin", 6500)
        minutes = int(state.get("minutes_to_bedtime", 0))
        if phase == "night":
            self._status.setText(f"● Night warmth active · {kelvin} K until wake")
        elif phase == "winding_down":
            self._status.setText(
                f"● Warming to {state.get('kelvin', 3400)} K · {minutes} min until bedtime"
            )
        elif phase == "off":
            self._status.setText("Display warm-up is off")
        else:
            if minutes:
                self._status.setText(f"○ Daylight · warm-up starts {minutes} min before bedtime")
            else:
                self._status.setText("○ Daylight · display at 6500 K")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#section_header {{ color: {tm.color('text_main')}; font-size: 11px; font-weight: 700; letter-spacing: 1.3px; }}
            QLabel#setting_desc {{ color: {tm.color('text_sub')}; font-size: 12px; }}
            QLabel#circadian_status {{ color: {tm.color('accent_tint_text')}; font-size: 12px; font-weight: 600; }}
            QSpinBox, QTimeEdit, QComboBox {{
                background: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                color: {tm.color('text_main')};
                padding: 5px 8px;
                font-size: 12px;
            }}
        """)
