"""
focus_timer.py — Apple-Style Immersive Focus Suite for Digital Wellbeing.

Designed according to macOS Sequoia / iOS Human Interface Guidelines:
- Apple Focus Mode Selector Cards with semantic accent colors and vector SVG icons
- Circular Countdown Timer Dial (Apple Watch / Stopwatch inspired) with smooth radial arc
- Apple Segmented Duration Control and fine-tuning minute steppers
- Inset Grouped Restriction Cards for Permitted/Blocked Apps and Blocked Websites
- Vector-iconized quick distraction toggles (YouTube, Reddit, Instagram, X/Twitter, TikTok)
- Apple iOS ToggleSwitch for Strict Mode PIN Enforcement
- Serene Apple Zen Active Focus cockpit with vector status pills and live countdown
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import design_system as ds
from ui.icons import get_icon, get_pixmap
from ui.styles.focus import build_focus_stylesheet
from ui.theme import ThemeManager
from ui.widgets.focus_active_view import FocusActiveViewMixin
from ui.widgets.focus_setup_view import FocusSetupViewMixin


# ─────────────────────────────────────────────────────────────────────────────
# Mode Visual Configurations (Apple HIG Semantic Palettes)
# ─────────────────────────────────────────────────────────────────────────────

MODE_CONFIG = {
    "deep": {
        "title": "Deep Focus",
        "subtitle": "Strict allowlist",
        "icon": "sparkles",
        "light_color": "#AF52DE",  # Apple Purple
        "dark_color": "#BF5AF2",
    },
    "work": {
        "title": "Work",
        "subtitle": "Workflow & tools",
        "icon": "briefcase",
        "light_color": "#007AFF",  # Apple Blue
        "dark_color": "#0A84FF",
    },
    "study": {
        "title": "Study",
        "subtitle": "Research & notes",
        "icon": "book",
        "light_color": "#FF9500",  # Apple Orange
        "dark_color": "#FF9F0A",
    },
    "movie": {
        "title": "Media",
        "subtitle": "Video & entertainment",
        "icon": "film",
        "light_color": "#30B0C7",  # Apple Teal
        "dark_color": "#64D2FF",
    },
    "custom": {
        "title": "Custom",
        "subtitle": "Personal blocklist",
        "icon": "sliders",
        "light_color": "#FF2D55",  # Apple Pink
        "dark_color": "#FF375F",
    },
}


def _get_mode_color(mode: str, is_dark: bool) -> str:
    cfg = MODE_CONFIG.get(mode, MODE_CONFIG["deep"])
    return cfg["dark_color"] if is_dark else cfg["light_color"]


# ─────────────────────────────────────────────────────────────────────────────
# Apple Circular Countdown Dial
# ─────────────────────────────────────────────────────────────────────────────

class AppleFocusRing(QWidget):
    """
    Apple Watch / macOS Stopwatch inspired circular countdown dial.
    Renders an antialiased circular track with a sweeping progress arc,
    central typographic time readout, vector indicator dot, and status subtext.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self._progress = 0.0          # 0.0 to 1.0
        self._time_text = "25:00"
        self._tag_text = "DEEP FOCUS"
        self._status_text = "Ready to focus"
        self._mode_color = "#BF5AF2"
        self._is_active = False

    def update_state(
        self,
        time_text: str,
        progress: float,
        tag_text: str,
        status_text: str,
        mode_color: str,
        is_active: bool = False,
    ) -> None:
        self._time_text = time_text
        self._progress = max(0.0, min(1.0, progress))
        self._tag_text = tag_text.upper()
        self._status_text = status_text
        self._mode_color = mode_color
        self._is_active = is_active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        tm = ThemeManager.instance()
        is_dark = tm.is_dark

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        # Ring geometry
        pen_width = 8.5
        diameter = min(w, h) - pen_width - 18.0
        r = diameter / 2.0
        rect = QRectF(cx - r, cy - r, diameter, diameter)

        # 1. Background Track
        track_color = QColor(255, 255, 255, 20) if is_dark else QColor(0, 0, 0, 16)
        track_pen = QPen(track_color, pen_width)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        # 2. Progress Arc
        if self._progress > 0.0:
            arc_color = QColor(self._mode_color)
            arc_pen = QPen(arc_color, pen_width)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)

            start_angle = 90 * 16  # 12 o'clock
            span_angle = -int(self._progress * 360 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 3. Mode Tag (Top) with Antialiased Vector Indicator Dot
        tag_color = QColor(self._mode_color)
        painter.setPen(tag_color)
        painter.setBrush(tag_color)

        tag_font = QFont("Inter", 10, QFont.Weight.Bold)
        tag_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(tag_font)

        fm_tag = painter.fontMetrics()
        text_w = float(fm_tag.horizontalAdvance(self._tag_text))
        dot_dia = 6.0
        total_w = text_w + dot_dia + 6.0
        start_x = cx - (total_w / 2.0)

        painter.drawEllipse(QRectF(start_x, cy - 40.0, dot_dia, dot_dia))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawText(
            QRectF(start_x + dot_dia + 6.0, cy - 48.0, text_w + 10.0, 22.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._tag_text,
        )

        # 4. Large Typographic Countdown (Center)
        time_color = QColor(tm.color("text_main"))
        painter.setPen(time_color)
        time_font = QFont("Inter Display", 40, QFont.Weight.Bold)
        time_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1.5)
        painter.setFont(time_font)
        painter.drawText(
            QRectF(cx - r, cy - 24.0, diameter, 52.0),
            Qt.AlignmentFlag.AlignCenter,
            self._time_text,
        )

        # 5. Status Subtext (Bottom)
        sub_color = QColor(tm.color("text_sub"))
        painter.setPen(sub_color)
        sub_font = QFont("Inter", 11, QFont.Weight.Medium)
        painter.setFont(sub_font)
        painter.drawText(
            QRectF(cx - r, cy + 30.0, diameter, 22.0),
            Qt.AlignmentFlag.AlignCenter,
            self._status_text,
        )

        painter.end()


# ─────────────────────────────────────────────────────────────────────────────
# Apple Focus Mode Selection Card
# ─────────────────────────────────────────────────────────────────────────────

class FocusModeCard(QFrame):
    """
    Apple macOS / iOS style Focus Mode pill card with colored squircle vector icon,
    title, subtitle, and dynamic accent highlight on selection.
    """

    clicked = Signal(str)

    def __init__(self, mode_id: str, parent=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._is_selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("focus_mode_card")

        cfg = MODE_CONFIG.get(mode_id, MODE_CONFIG["deep"])
        self.title_str = cfg["title"]
        self.sub_str = cfg["subtitle"]
        self.icon_name = cfg["icon"]

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Squircle Icon Container
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(30, 30)
        self.icon_frame.setObjectName("mode_icon_frame")
        icon_layout = QVBoxLayout(self.icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(16, 16)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_lbl)
        layout.addWidget(self.icon_frame)

        # Text Details
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_lbl = QLabel(self.title_str)
        self.title_lbl.setObjectName("mode_title")

        self.sub_lbl = QLabel(self.sub_str)
        self.sub_lbl.setObjectName("mode_sub")

        text_col.addWidget(self.title_lbl)
        text_col.addWidget(self.sub_lbl)
        layout.addLayout(text_col, 1)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.mode_id)

    def set_selected(self, selected: bool):
        if self._is_selected != selected:
            self._is_selected = selected
            self._apply_style()

    def _apply_style(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        accent_color = _get_mode_color(self.mode_id, is_dark)
        q_acc = QColor(accent_color)
        r, g, b = q_acc.red(), q_acc.green(), q_acc.blue()

        icon_color = accent_color if self._is_selected else tm.color("text_sub")
        self.icon_lbl.setPixmap(get_pixmap(self.icon_name, color=icon_color, size=16))

        if self._is_selected:
            bg = f"rgba({r}, {g}, {b}, 0.14)" if is_dark else f"rgba({r}, {g}, {b}, 0.12)"
            border = f"1.5px solid {accent_color}"
            icon_bg = f"rgba({r}, {g}, {b}, 0.25)" if is_dark else f"rgba({r}, {g}, {b}, 0.20)"
            title_color = tm.color("text_main")
        else:
            bg = tm.color("surface_secondary")
            border = f"1px solid {tm.color('border')}"
            icon_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.04)"
            title_color = tm.color("text_main")

        self.setStyleSheet(f"""
            QFrame#focus_mode_card {{
                background-color: {bg};
                border: {border};
                border-radius: {ds.CARD_RADIUS}px;
            }}
            QFrame#focus_mode_card:hover {{
                background-color: {f'rgba({r}, {g}, {b}, 0.18)' if self._is_selected else tm.color('card_hover')};
                border-color: {accent_color if self._is_selected else tm.color('border_hover')};
            }}
            QFrame#mode_icon_frame {{
                background-color: {icon_bg};
                border-radius: 10px;
                border: none;
            }}
            QLabel#mode_title {{
                font-size: 13px;
                font-weight: 700;
                color: {title_color};
                letter-spacing: -0.2px;
            }}
            QLabel#mode_sub {{
                font-size: 11px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Apple Style Rounded Chip Tag (with vector close icon)
# ─────────────────────────────────────────────────────────────────────────────

class ChipWidget(QFrame):
    """Clean Apple-style capsule chip for configured apps and blocked websites."""

    removed = Signal(str)

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text_val = text
        self.setObjectName("apple_chip")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)

        self.lbl = QLabel(text)
        self.lbl.setObjectName("chip_text")

        self.btn = QPushButton()
        self.btn.setObjectName("chip_close")
        self.btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn.setFixedSize(18, 18)
        self.btn.setIcon(get_icon("close", color="#8E8E93", size=10))
        self.btn.clicked.connect(lambda: self.removed.emit(self.text_val))

        layout.addWidget(self.lbl)
        layout.addWidget(self.btn)

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self, *args):
        try:
            tm = ThemeManager.instance()
            self.btn.setIcon(get_icon("close", color=tm.color("text_sub"), size=10))
            self.setStyleSheet(f"""
                QFrame#apple_chip {{
                    background-color: {tm.color('surface_secondary')};
                    border: 1px solid {tm.color('border')};
                    border-radius: 9px;
                }}
                QLabel#chip_text {{
                    color: {tm.color('text_main')};
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton#chip_close {{
                    background: transparent;
                    border: none;
                    border-radius: 9px;
                    padding: 0px;
                }}
                QPushButton#chip_close:hover {{
                    background: rgba(255, 69, 58, 0.16);
                }}
            """)
        except RuntimeError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Vector Statistic Pill
# ─────────────────────────────────────────────────────────────────────────────

class StatPill(QFrame):
    """Clean capsule pill with a vector SVG icon and high-contrast text."""

    def __init__(self, icon_name: str, icon_color: str, initial_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName("stat_pill")
        self._icon_name = icon_name
        self._icon_color = icon_color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 14, 6)
        layout.setSpacing(7)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(14, 14)
        self.icon_lbl.setPixmap(get_pixmap(icon_name, color=icon_color, size=14))
        layout.addWidget(self.icon_lbl)

        self.text_lbl = QLabel(initial_text)
        self.text_lbl.setObjectName("stat_pill_text")
        layout.addWidget(self.text_lbl)

        self._apply_style()

    def set_value(self, text: str):
        self.text_lbl.setText(text)

    def set_icon_color(self, color: str):
        self._icon_color = color
        self.icon_lbl.setPixmap(get_pixmap(self._icon_name, color=color, size=14))

    def _apply_style(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QFrame#stat_pill {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
            }}
            QLabel#stat_pill_text {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('text_sub')};
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Apple Modal Dialogs (Add Website & Preflight)
# ─────────────────────────────────────────────────────────────────────────────

class AddWebsiteDialog(QDialog):
    """Apple macOS sheet modal for adding a blocked website to Focus Mode."""

    def __init__(self, mode: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add Blocked Website — {mode.title()}")
        self.setFixedSize(500, 390)
        self.setObjectName("add_website_dialog")
        self._chosen_domain: Optional[str] = None
        self._setup_ui(mode)
        self._apply_dialog_theme()

    def _setup_ui(self, mode: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Header Badge & Icon
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(8)

        badge_icon = QLabel()
        badge_icon.setPixmap(get_pixmap("globe", color="#0A84FF", size=14))
        hdr_row.addWidget(badge_icon)

        badge = QLabel("WEBSITE RESTRICTION")
        badge.setObjectName("badge_label")
        hdr_row.addWidget(badge)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        title = QLabel("Add Blocked Website")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel(
            f"Enter a website domain to restrict during {mode.title()} Focus sessions across all browsers. "
            "Traffic to this domain will be blocked at the system level."
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Popular Presets
        sugg_lbl = QLabel("POPULAR PRESETS:")
        sugg_lbl.setObjectName("field_heading")
        layout.addWidget(sugg_lbl)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        quick_presets = [
            ("YouTube", "youtube.com"),
            ("Instagram", "instagram.com"),
            ("Reddit", "reddit.com"),
            ("X / Twitter", "x.com"),
            ("TikTok", "tiktok.com"),
        ]
        for label, domain in quick_presets:
            p_btn = QPushButton(label)
            p_btn.setObjectName("preset_pill_btn")
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.setIcon(get_icon("plus", color="#8E8E93", size=11))
            p_btn.clicked.connect(lambda _, d=domain: self._set_input(d))
            preset_row.addWidget(p_btn)
        preset_row.addStretch()
        layout.addLayout(preset_row)

        # Domain Input Field
        input_lbl = QLabel("DOMAIN / WEBSITE:")
        input_lbl.setObjectName("field_heading")
        layout.addWidget(input_lbl)

        self._domain_input = QLineEdit()
        self._domain_input.setObjectName("domain_input")
        self._domain_input.setPlaceholderText("e.g. reddit.com or youtube.com")
        self._domain_input.textChanged.connect(self._validate_input)
        layout.addWidget(self._domain_input)

        # Validation Feedback
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setObjectName("feedback_lbl")
        layout.addWidget(self._feedback_lbl)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        self._add_btn = QPushButton("Add Block")
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setIcon(get_icon("plus", "#FFFFFF", 13))
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self._add_btn)
        layout.addLayout(btn_layout)

    def _set_input(self, domain: str):
        self._domain_input.setText(domain)
        self._domain_input.setFocus()

    def _validate_input(self, text: str):
        from protection.website_blocker import WebsiteBlocker

        clean = WebsiteBlocker.clean_domain(text)
        if not text.strip():
            self._feedback_lbl.setText("")
            self._add_btn.setEnabled(False)
        elif not clean:
            self._feedback_lbl.setText("Please enter a valid domain (e.g. example.com)")
            self._feedback_lbl.setStyleSheet("color: #FF453A; font-size: 11px; font-weight: 500;")
            self._add_btn.setEnabled(False)
        else:
            self._feedback_lbl.setText(f"Will block {clean} (and www.{clean})")
            self._feedback_lbl.setStyleSheet("color: #0A84FF; font-size: 11px; font-weight: 500;")
            self._add_btn.setEnabled(True)

    def _on_add(self):
        from protection.website_blocker import WebsiteBlocker

        clean = WebsiteBlocker.clean_domain(self._domain_input.text())
        if clean:
            self._chosen_domain = clean
            self.accept()

    @property
    def domain(self) -> Optional[str]:
        return self._chosen_domain

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog#add_website_dialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 18px;
            }}
            QLabel#badge_label {{
                color: #0A84FF;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.4px;
                background: rgba(10, 132, 255, 0.14);
                border: 1px solid rgba(10, 132, 255, 0.32);
                border-radius: 9px;
                padding: 3px 10px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.4px;
            }}
            QLabel#dialog_desc {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QLabel#field_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            QPushButton#preset_pill_btn {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 600;
                padding: 6px 12px;
            }}
            QPushButton#preset_pill_btn:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
                border-color: {tm.color('accent')};
            }}
            QLineEdit#domain_input {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_main')};
                font-size: 13px;
                padding: 10px 14px;
            }}
            QLineEdit#domain_input:focus {{
                border: 1.5px solid {tm.color('accent')};
            }}
            QPushButton#btn_cancel {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
            }}
            QPushButton#btn_cancel:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_primary {{
                background: {tm.color('accent')};
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 24px;
            }}
            QPushButton#btn_primary:hover {{
                background: {tm.color('accent_hover')};
            }}
            QPushButton#btn_primary:disabled {{
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.30);
            }}
        """)


class DeepFocusPreflightDialog(QDialog):
    """Apple macOS verification sheet confirming restrictions before starting Focus."""

    def __init__(self, mode: str, allowed_apps: List[str], blocked_websites: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Focus Preflight Review — {mode.title()}")
        self.setFixedSize(580, 480)
        self.setObjectName("preflight_dialog")
        self._mode = mode
        self._allowed_apps = allowed_apps or []
        self._blocked_websites = blocked_websites or []

        self._setup_ui(mode)
        self._apply_dialog_theme()

    def _setup_ui(self, mode: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(14)

        # Header Badge
        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(8)

        badge_icon = QLabel()
        badge_icon.setPixmap(get_pixmap("shield", color="#AF52DE", size=14))
        hdr_row.addWidget(badge_icon)

        badge = QLabel("FOCUS PREFLIGHT REVIEW")
        badge.setObjectName("badge_label")
        hdr_row.addWidget(badge)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        title = QLabel(f"Start {mode.title()} Focus?")
        title.setObjectName("dialog_title")
        layout.addWidget(title)

        desc = QLabel(
            "Review the distraction shielding rules that will take effect immediately upon starting. "
            "System infrastructure and essential tools remain protected."
        )
        desc.setObjectName("dialog_desc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Split Inset Grid: Applications & Websites
        content_grid = QHBoxLayout()
        content_grid.setSpacing(16)

        # Left Column: Apps
        apps_col = QVBoxLayout()
        apps_col.setSpacing(8)
        is_custom = (mode == "custom")
        apps_lbl = QLabel("BLOCKED APPLICATIONS:" if is_custom else "PERMITTED APPLICATIONS:")
        apps_lbl.setObjectName("apps_heading")
        apps_col.addWidget(apps_lbl)

        apps_scroll = QScrollArea()
        apps_scroll.setWidgetResizable(True)
        apps_scroll.setFrameShape(QFrame.Shape.NoFrame)
        apps_scroll.setObjectName("preflight_scroll")

        apps_container = QWidget()
        apps_list_layout = QVBoxLayout(apps_container)
        apps_list_layout.setContentsMargins(8, 8, 8, 8)
        apps_list_layout.setSpacing(6)

        if not self._allowed_apps:
            none_msg = "No applications configured." if is_custom else "All standard user apps will be restricted."
            none_lbl = QLabel(none_msg)
            none_lbl.setObjectName("none_lbl")
            none_lbl.setWordWrap(True)
            apps_list_layout.addWidget(none_lbl)
        else:
            for a in self._allowed_apps:
                row = QHBoxLayout()
                row.setSpacing(8)
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(14, 14)
                if is_custom:
                    icon_lbl.setPixmap(get_pixmap("close", color="#FF453A", size=12))
                else:
                    icon_lbl.setPixmap(get_pixmap("check", color="#30D158", size=12))
                txt = QLabel(a)
                txt.setStyleSheet("color: #F5F5F7; font-weight: 600; font-size: 12px;")
                row.addWidget(icon_lbl)
                row.addWidget(txt)
                row.addStretch()
                apps_list_layout.addLayout(row)

        apps_list_layout.addStretch()
        apps_scroll.setWidget(apps_container)
        apps_col.addWidget(apps_scroll, 1)
        content_grid.addLayout(apps_col, 1)

        # Right Column: Websites
        sites_col = QVBoxLayout()
        sites_col.setSpacing(8)
        sites_lbl = QLabel("BLOCKED WEBSITES:")
        sites_lbl.setObjectName("apps_heading")
        sites_col.addWidget(sites_lbl)

        sites_scroll = QScrollArea()
        sites_scroll.setWidgetResizable(True)
        sites_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sites_scroll.setObjectName("preflight_scroll")

        sites_container = QWidget()
        sites_list_layout = QVBoxLayout(sites_container)
        sites_list_layout.setContentsMargins(8, 8, 8, 8)
        sites_list_layout.setSpacing(6)

        if not self._blocked_websites:
            none_sites = QLabel("No websites blocked for this mode.")
            none_sites.setObjectName("none_lbl")
            none_sites.setWordWrap(True)
            sites_list_layout.addWidget(none_sites)
        else:
            for site in self._blocked_websites:
                row = QHBoxLayout()
                row.setSpacing(8)
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(14, 14)
                icon_lbl.setPixmap(get_pixmap("close", color="#FF453A", size=12))
                txt = QLabel(site)
                txt.setStyleSheet("color: #F5F5F7; font-weight: 600; font-size: 12px;")
                row.addWidget(icon_lbl)
                row.addWidget(txt)
                row.addStretch()
                sites_list_layout.addLayout(row)

        sites_list_layout.addStretch()
        sites_scroll.setWidget(sites_container)
        sites_col.addWidget(sites_scroll, 1)
        content_grid.addLayout(sites_col, 1)

        layout.addLayout(content_grid, 1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_cancel")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        start_btn = QPushButton("Start Focus Session")
        start_btn.setObjectName("btn_primary")
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setIcon(get_icon("play", "#FFFFFF", 13))
        start_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(start_btn)
        layout.addLayout(btn_layout)

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        self.setStyleSheet(f"""
            QDialog#preflight_dialog {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                border-radius: 18px;
            }}
            QLabel#badge_label {{
                color: #AF52DE;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1.4px;
                background: rgba(175, 82, 222, 0.14);
                border: 1px solid rgba(175, 82, 222, 0.32);
                border-radius: 9px;
                padding: 3px 10px;
            }}
            QLabel#dialog_title {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.4px;
            }}
            QLabel#dialog_desc {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
                line-height: 1.4;
            }}
            QLabel#apps_heading {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.2px;
            }}
            QLabel#none_lbl {{
                color: #FF9F0A;
                font-size: 12px;
                font-style: italic;
            }}
            QScrollArea#preflight_scroll {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 12px;
                padding: 4px;
            }}
            QPushButton#btn_cancel {{
                background: {tm.color('surface')};
                border: 1px solid {tm.color('border')};
                border-radius: 10px;
                color: {tm.color('text_sub')};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
            }}
            QPushButton#btn_cancel:hover {{
                background: {tm.color('card_hover')};
                color: {tm.color('text_main')};
            }}
            QPushButton#btn_primary {{
                background: {tm.color('accent')};
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 9px 22px;
            }}
            QPushButton#btn_primary:hover {{
                background: {tm.color('accent_hover')};
            }}
        """)


# ─────────────────────────────────────────────────────────────────────────────
# Apple Focus Timer Suite (Main Cockpit Widget)
# ─────────────────────────────────────────────────────────────────────────────

class FocusTimerWidget(FocusSetupViewMixin, FocusActiveViewMixin, QFrame):
    """
    Apple macOS / iOS style Focus Suite Cockpit Widget.
    Manages mode configuration, circular countdown dial, distraction lists,
    and the active focus session state with vector icons.
    """

    card_clicked = Signal()
    focus_completed = Signal()
    DEFAULT_FOCUS_M = 25

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("focus_suite_root")

        from protection.focus_manager import FocusManager

        self._fm = FocusManager.instance()
        self._fm.tick.connect(self._on_tick)
        self._fm.focus_state_changed.connect(self._on_state_changed)
        self._fm.focus_completed.connect(self.focus_completed.emit)

        self._selected_minutes = self.DEFAULT_FOCUS_M
        self._session_total_seconds = self.DEFAULT_FOCUS_M * 60
        self._site_search_query = ""

        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.card_clicked.emit()

    def resizeEvent(self, event) -> None:
        # Five mode cards fit side-by-side on wide layouts; on narrower
        # windows the subtitles are hidden so the cards never force horizontal
        # overflow in the page's scroll area.
        compact = event.size().width() < 880
        for card in getattr(self, "_mode_cards", {}).values():
            card.sub_lbl.setVisible(not compact)
        super().resizeEvent(event)

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._stack = QStackedWidget(self)
        main_layout.addWidget(self._stack)

        # 0: INACTIVE CONFIGURATION COCKPIT
        self._inactive_view = QWidget()
        self._build_inactive_view()
        self._stack.addWidget(self._inactive_view)

        # 1: ACTIVE FOCUS COCKPIT
        self._active_view = QWidget()
        self._build_active_view()
        self._stack.addWidget(self._active_view)

        # Sync Initial State
        self._sync_mode_cards()
        self._refresh_blocklist_ui()
        self._refresh_websites_ui()
        self._refresh_rules_ui()
        self._sync_ui_state()

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        mode = self._fm.current_mode
        mode_color = _get_mode_color(mode, is_dark)

        # Update mode cards
        for card in self._mode_cards.values():
            card._apply_style()

        # Update timer dial
        self._focus_ring.update_state(
            time_text=self._format_time(self._selected_minutes * 60),
            progress=0.0,
            tag_text=MODE_CONFIG.get(mode, MODE_CONFIG["deep"])["title"],
            status_text="Ready to focus",
            mode_color=mode_color,
            is_active=False,
        )

        self.setStyleSheet(build_focus_stylesheet(tm, mode_color, is_dark))

    def set_preset(self, minutes: int) -> None:
        if self._fm.is_active:
            return
        self._selected_minutes = minutes
        self._session_total_seconds = minutes * 60
        mode = self._fm.current_mode
        mode_color = _get_mode_color(mode, ThemeManager.instance().is_dark)

        self._focus_ring.update_state(
            time_text=self._format_time(minutes * 60),
            progress=0.0,
            tag_text=MODE_CONFIG.get(mode, MODE_CONFIG["deep"])["title"],
            status_text=f"Session set to {minutes}m",
            mode_color=mode_color,
            is_active=False,
        )
        for chip in getattr(self, "_chips", []):
            chip.setChecked(chip.property("minutes") == minutes)

    def _adjust_duration(self, delta_m: int) -> None:
        if self._fm.is_active:
            return
        new_dur = max(5, min(180, self._selected_minutes + delta_m))
        self.set_preset(new_dur)

    def _on_strict_toggled(self, checked: bool) -> None:
        if checked and not self._fm._pin_manager.is_enabled():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "PIN Required",
                "You must configure a PIN in Settings before enabling Strict Mode.",
            )
            self._strict_switch.setChecked(False)

    def _set_mode(self, mode: str) -> None:
        if self._fm.is_active:
            return
        self._fm.set_mode(mode)
        self._sync_mode_cards()
        self._handle_dynamic_suggestions(mode)
        self._refresh_blocklist_ui()
        self._refresh_websites_ui()
        self._apply_theme(ThemeManager.instance().is_dark)

    def _sync_mode_cards(self) -> None:
        current = self._fm.current_mode
        for m_id, card in self._mode_cards.items():
            card.set_selected(m_id == current)

    def _handle_dynamic_suggestions(self, mode: str) -> None:
        apps = self._fm.current_mode_apps
        if apps:
            return

        if mode in ("study", "work", "movie"):
            suggested = self._get_suggestions(mode)
            if suggested:
                self._fm.save_mode_apps(mode, suggested)

    def _get_suggestions(self, mode: str) -> List[str]:
        if mode not in ("study", "work", "movie"):
            return []
        from utils.win_utils import get_all_discoverable_applications

        suggested = []
        kws = (
            ["code", "word", "excel", "onenote", "edge", "chrome", "brave", "firefox", "notion", "slack", "teams", "zoom"]
            if mode in ("study", "work")
            else ["vlc", "player", "spotify", "netflix", "chrome", "edge", "brave", "firefox"]
        )
        try:
            apps = get_all_discoverable_applications()
            seen = set()
            for name, display, _ in apps:
                n_lower = name.lower()
                d_lower = display.lower()
                if n_lower in seen:
                    continue
                if any(k in n_lower for k in kws) or any(k in d_lower for k in kws):
                    seen.add(n_lower)
                    suggested.append(n_lower)
        except Exception:
            pass
        return suggested

    def _refresh_blocklist_ui(self) -> None:
        while self._blocklist_layout.count():
            item = self._blocklist_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()

        items = self._fm.current_mode_apps
        mode = self._fm.current_mode

        is_custom = (mode == "custom")
        self._list_hdr.setText("Blocked apps" if is_custom else "Permitted apps")
        self._list_sub.setText("These applications will be closed & blocked" if is_custom else "Only these user applications can run during session")
        self._apps_count_badge.setText(f"{len(items)} app{'s' if len(items) != 1 else ''}")

        if not items:
            placeholder = QLabel("No applications configured.")
            placeholder.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-style: italic; font-size: 12px;")
            self._blocklist_layout.addWidget(placeholder)
        else:
            for text in items:
                chip = ChipWidget(text)
                chip.removed.connect(self._remove_app_item)
                self._blocklist_layout.addWidget(chip)

    def _refresh_websites_ui(self) -> None:
        while self._websites_layout.count():
            item = self._websites_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()

        mode = self._fm.current_mode
        sites = self._fm.get_mode_websites(mode)
        search_q = getattr(self, "_site_search_query", "").strip().lower()

        if search_q:
            filtered_sites = [s for s in sites if search_q in s.lower()]
        else:
            filtered_sites = sites

        self._websites_count_lbl.setText(f"{len(sites)} site{'s' if len(sites) != 1 else ''}")

        # Update quick preset buttons with vector SVG icons
        tm = ThemeManager.instance()
        for p_dom, btn in getattr(self, "_quick_preset_btns", {}).items():
            if p_dom in sites:
                btn.setIcon(get_icon("check", color="#30D158", size=12))
                btn.setStyleSheet("color: #30D158; border-color: rgba(48, 209, 88, 0.4);")
            else:
                btn.setIcon(get_icon("plus", color=tm.color("text_sub"), size=11))
                btn.setStyleSheet("")

        if not filtered_sites:
            if search_q:
                placeholder = QLabel(f"No sites matching '{search_q}'")
            else:
                placeholder = QLabel("No websites blocked for this mode.")
            placeholder.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-style: italic; font-size: 12px;")
            self._websites_layout.addWidget(placeholder)
        else:
            for site in filtered_sites:
                chip = ChipWidget(site)
                chip.removed.connect(self._remove_website_item)
                self._websites_layout.addWidget(chip)

    def _quick_toggle_site(self, domain: str) -> None:
        mode = self._fm.current_mode
        sites = self._fm.get_mode_websites(mode)
        if domain in sites:
            self._fm.remove_mode_website(mode, domain)
        else:
            self._fm.add_mode_website(mode, domain)
        self._refresh_websites_ui()

    def _on_search_websites(self, query: str) -> None:
        self._site_search_query = query
        self._refresh_websites_ui()

    def _open_website_picker(self) -> None:
        mode = self._fm.current_mode
        dlg = AddWebsiteDialog(mode, self.window())
        if dlg.exec():
            domain = dlg.domain
            if domain:
                self._fm.add_mode_website(mode, domain)
                self._refresh_websites_ui()

    def _remove_website_item(self, site: str) -> None:
        self._fm.remove_mode_website(self._fm.current_mode, site)
        self._refresh_websites_ui()

    def _open_app_picker(self) -> None:
        mode = self._fm.current_mode
        action = "Block Application" if mode == "custom" else "Allow Application"
        title = "Add to Blocklist" if mode == "custom" else "Add to Allowlist"

        from ui.widgets.process_picker import ProcessPickerDialog

        dlg = ProcessPickerDialog(self.window(), mode="focus", action_text=action, title_text=title)
        if dlg.exec():
            app = dlg.selected_process_name
            if app:
                items = self._fm.current_mode_apps
                if app not in items:
                    items.append(app)
                    self._fm.save_mode_apps(mode, items)
                    self._refresh_blocklist_ui()

    def _remove_app_item(self, text: str) -> None:
        items = self._fm.current_mode_apps
        if text in items:
            items.remove(text)
            self._fm.save_mode_apps(self._fm.current_mode, items)
            self._refresh_blocklist_ui()

    def _on_tick(self, seconds: int) -> None:
        time_str = self._format_time(seconds)
        mode = self._fm.current_mode
        mode_color = _get_mode_color(mode, ThemeManager.instance().is_dark)

        if self._fm.is_lockout:
            host = self.window()
            if host is not None and (host.isMinimized() or not host.isVisible()):
                host.showNormal()
                host.raise_()
                host.activateWindow()
            if hasattr(self, "_emergency_btn") and self._emergency_btn.isVisible():
                if self._fm.is_emergency_pending:
                    remaining = self._fm.emergency_unlock_remaining
                    self._emergency_btn.setText(
                        f"Emergency unlock in {remaining // 60}:{remaining % 60:02d}"
                    )
                    self._emergency_btn.setEnabled(False)
                else:
                    self._emergency_btn.setEnabled(True)

        total = self._fm.session_total_seconds or self._session_total_seconds or (self._selected_minutes * 60)
        elapsed = max(0, total - seconds)
        pct = (elapsed / max(total, 1))

        # Update active ring dial
        status_text = "Lockout in progress · cannot be ended" if self._fm.is_lockout else "Deep focus in progress"
        self._active_focus_ring.update_state(
            time_text=time_str,
            progress=pct,
            tag_text=MODE_CONFIG.get(mode, MODE_CONFIG["deep"])["title"],
            status_text=status_text,
            mode_color=mode_color,
            is_active=True,
        )

        self._active_elapsed_pill.set_value(f"{elapsed // 60}m elapsed")
        self._active_remaining_pill.set_value(f"{seconds // 60}m remaining")

    def _on_state_changed(self, is_active: bool) -> None:
        self._sync_ui_state()

    def _sync_ui_state(self) -> None:
        mode = self._fm.current_mode
        is_dark = ThemeManager.instance().is_dark
        mode_color = _get_mode_color(mode, is_dark)

        if self._fm.is_active:
            self._session_total_seconds = self._fm.session_total_seconds or (self._selected_minutes * 60)
            self._active_mode_lbl.setText(f"{mode.upper()} FOCUS MODE")

            apps = self._fm.current_mode_apps
            websites = self._fm.current_mode_websites
            if mode == "custom":
                self._active_apps_summary.setText(f"{len(apps)} applications blocked from running")
            else:
                self._active_apps_summary.setText(f"{len(apps)} user applications permitted · Windows safe")

            self._active_websites_summary.setText(
                f"{len(websites)} distracting websites blocked across all browsers" if websites else "No website blocks active"
            )

            # Update active status pill with vector icon and color
            self._active_pill_icon.setPixmap(get_pixmap("sparkles", color=mode_color, size=14))
            if self._fm.is_lockout:
                self._active_pill_text.setText(f"LOCKOUT ACTIVE — {mode.upper()}")
                self._active_stop_btn.setVisible(False)
                self._active_mode_lbl.setText(f"{mode.upper()} LOCKOUT · CANNOT END EARLY")
                self._emergency_btn.setVisible(True)
                if self._fm.is_emergency_pending:
                    remaining = self._fm.emergency_unlock_remaining
                    self._emergency_btn.setText(
                        f"Emergency unlock in {remaining // 60}:{remaining % 60:02d}"
                    )
                    self._emergency_btn.setEnabled(False)
                else:
                    self._emergency_btn.setText("Need to exit? Emergency unlock")
                    self._emergency_btn.setEnabled(True)
            else:
                self._active_pill_text.setText(f"FOCUS ACTIVE — {mode.upper()}")
                self._active_stop_btn.setVisible(True)
                self._emergency_btn.setVisible(False)
            q_acc = QColor(mode_color)
            r, g, b = q_acc.red(), q_acc.green(), q_acc.blue()
            self._active_status_pill.setStyleSheet(f"""
                QFrame#active_focus_pill {{
                    background: rgba({r}, {g}, {b}, 0.14);
                    border: 1.5px solid rgba({r}, {g}, {b}, 0.38);
                    border-radius: 12px;
                }}
                QLabel#active_pill_text {{
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 1.5px;
                    color: {mode_color};
                }}
            """)

            self._stack.setCurrentIndex(1)
        else:
            self._stack.setCurrentIndex(0)
            time_str = self._format_time(self._selected_minutes * 60)
            status = "Session complete! Great work." if time_str == "00:00" else "Ready to focus"

            self._focus_ring.update_state(
                time_text=time_str,
                progress=0.0,
                tag_text=MODE_CONFIG.get(mode, MODE_CONFIG["deep"])["title"],
                status_text=status,
                mode_color=mode_color,
                is_active=False,
            )

    def _toggle_timer(self) -> None:
        if not self._fm.is_active:
            lockout = bool(getattr(self, "_lockout_switch", None) and self._lockout_switch.isChecked())
            strict = bool(self._strict_switch.isChecked())
            if strict and not lockout and not self._fm._pin_manager.is_enabled():
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "PIN Required", "You must configure a PIN in Settings before using Strict Mode.")
                self._strict_switch.setChecked(False)
                return
            if lockout and not self._fm._pin_manager.is_enabled():
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "PIN Required",
                    "Lockout needs a PIN so the safe emergency exit can verify you. "
                    "Configure one in Settings first.",
                )
                self._lockout_switch.setChecked(False)
                return

            if lockout:
                from PySide6.QtWidgets import QMessageBox

                confirm = QMessageBox.warning(
                    self,
                    "Start Lockout Session?",
                    "Lockout cannot be ended from inside the app until the countdown completes.\n\n"
                    "The app will relaunch if its process is closed, and the remaining session "
                    "will resume. This is best-effort: it cannot defeat an administrator, "
                    "Safe Mode, or a full system shutdown.\n\n"
                    "Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

            mode = self._fm.current_mode
            # Preflight review showing BOTH applications and websites for all modes
            dlg = DeepFocusPreflightDialog(
                mode=mode,
                allowed_apps=self._fm.current_mode_apps,
                blocked_websites=self._fm.get_mode_websites(mode),
                parent=self.window(),
            )
            if not dlg.exec():
                return

            self._session_total_seconds = self._selected_minutes * 60
            started = self._fm.start_focus(
                self._selected_minutes,
                strict_mode=strict,
                lockout=lockout,
            )
            if started and lockout:
                # A lockout must be visible: bring the host window forward.
                host = self.window()
                if host is not None:
                    host.showNormal()
                    host.raise_()
                    host.activateWindow()

    def _stop_timer(self) -> None:
        if not self._fm.is_active:
            self._selected_minutes = self.DEFAULT_FOCUS_M
            self._session_total_seconds = self.DEFAULT_FOCUS_M * 60
            self.set_preset(self.DEFAULT_FOCUS_M)
            return

        if self._fm.is_lockout:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.information(
                self,
                "Lockout active",
                "This session is locked until the countdown completes. "
                "You chose Lockout to make ending it harder — take a breath and keep going.",
            )
            return

        if self._fm.is_strict:
            from ui.widgets.pin_dialog import PinDialog

            dialog = PinDialog(self._fm._pin_manager, self.window())
            if dialog.exec():
                self._fm.stop_focus_after_pin_dialog()
        else:
            self._fm.stop_focus()

    @staticmethod
    def _format_time(seconds: int) -> str:
        m, s = divmod(seconds, 60)
        return f"{m:02d}:{s:02d}"
