"""
wellbeing.py — Apple-Style Unified Focus Suite Page for Digital Wellbeing.

Provides:
- Apple macOS Sequoia / iOS HIG-styled page layout and header
- Live Focus vector status capsule indicator in the top right
- Responsive container hosting the immersive FocusTimerWidget
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tracker.sleepguard import SleepGuardController
from ui import design_system as ds
from ui.icons import get_pixmap
from ui.theme import ThemeManager
from ui.widgets.focus_timer import FocusTimerWidget


class HeaderStatusCapsule(QFrame):
    """Clean Apple-style status capsule with vector icon and status text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header_status_capsule")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 14, 5)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(14, 14)
        layout.addWidget(self.icon_lbl)

        self.text_lbl = QLabel("Focus Inactive")
        self.text_lbl.setObjectName("header_status_text")
        layout.addWidget(self.text_lbl)

    def set_active(self, is_active: bool, mode_name: str = "Focus"):
        tm = ThemeManager.instance()
        if is_active:
            self.icon_lbl.setPixmap(get_pixmap("sparkles", color="#30D158", size=13))
            self.text_lbl.setText(f"{mode_name.title()} Focus Active")
            self.setStyleSheet("""
                QFrame#header_status_capsule {
                    background: rgba(48, 209, 88, 0.14);
                    border: 1px solid rgba(48, 209, 88, 0.35);
                    border-radius: 12px;
                }
                QLabel#header_status_text {
                    font-size: 12px;
                    font-weight: 700;
                    color: #30D158;
                }
            """)
        else:
            self.icon_lbl.setPixmap(get_pixmap("focus", color=tm.color("text_sub"), size=13))
            self.text_lbl.setText("Focus Inactive")
            self.setStyleSheet(f"""
                QFrame#header_status_capsule {{
                    background: {tm.color('surface_secondary')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 12px;
                }}
                QLabel#header_status_text {{
                    font-size: 12px;
                    font-weight: 600;
                    color: {tm.color('text_sub')};
                }}
            """)


class WellbeingPage(QWidget):
    """Apple-style Focus Session & Distraction Shielding Page."""

    focus_completed = Signal()

    def __init__(self, sleepguard: Optional[SleepGuardController] = None, parent=None) -> None:
        super().__init__(parent)
        self._sleepguard = sleepguard
        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(36, 28, 36, 32)
        inner_layout.setSpacing(24)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        # Apple macOS / iOS Style Header
        header_row = QHBoxLayout()
        header_row.setSpacing(16)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("Focus")
        title.setObjectName("apple_page_title")

        subtitle = QLabel("Intentional distraction-free sessions engineered for deep concentration.")
        subtitle.setObjectName("apple_page_subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box, 1)

        # Right-aligned Live Status Capsule
        self._status_capsule = HeaderStatusCapsule()
        header_row.addWidget(self._status_capsule)

        inner_layout.addLayout(header_row)

        # Centered Container for Focus Cockpit
        center_box = QWidget()
        center_layout = QVBoxLayout(center_box)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_box.setMaximumWidth(1080)

        self._focus_timer = FocusTimerWidget()
        self._focus_timer.focus_completed.connect(self.focus_completed.emit)

        # Connect focus manager state change to update header status capsule
        from protection.focus_manager import FocusManager

        FocusManager.instance().focus_state_changed.connect(self._on_focus_state_changed)

        center_layout.addWidget(self._focus_timer)
        inner_layout.addWidget(center_box, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        inner_layout.addStretch()

    def _on_focus_state_changed(self, is_active: bool) -> None:
        from protection.focus_manager import FocusManager

        fm = FocusManager.instance()
        self._status_capsule.set_active(is_active, fm.current_mode)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QLabel#apple_page_title {{
                font-size: 28px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.6px;
                font-family: "Inter Display", "Inter", "Segoe UI", sans-serif;
            }}
            QLabel#apple_page_subtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
        """)
        from protection.focus_manager import FocusManager

        fm = FocusManager.instance()
        self._status_capsule.set_active(fm.is_active, fm.current_mode)
        self.on_data_changed()

    def on_data_changed(self) -> None:
        pass
