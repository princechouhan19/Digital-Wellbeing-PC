"""
app_timer.py (UI page) — Unified Timer Dashboard for Digital Wellbeing.
Displays and manages daily active screen-time limits for both
Windows Applications and Websites.
Strictly independent from App Locker.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QMessageBox, QDialog, QProgressBar,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QIcon, QColor

from database.repository import Repository
from core.logger import logger
from ui.theme import ThemeManager
from ui.icons import get_icon
from utils.icon_provider import AppIconProvider


def _format_time_short(seconds: float) -> str:
    total_secs = int(max(0, seconds))
    h, r = divmod(total_secs, 3600)
    m, _ = divmod(r, 60)
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    elif m > 0:
        return f"{m}m"
    elif total_secs > 0:
        return f"{total_secs}s"
    else:
        return "0m"


_KNOWN_WEBSITES: dict[str, str] = {
    "youtube.com": "YouTube",
    "google.com": "Google",
    "github.com": "GitHub",
    "reddit.com": "Reddit",
    "twitter.com": "X (Twitter)",
    "x.com": "X (Twitter)",
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "netflix.com": "Netflix",
    "twitch.tv": "Twitch",
    "discord.com": "Discord",
    "amazon.com": "Amazon",
    "wikipedia.org": "Wikipedia",
    "linkedin.com": "LinkedIn",
    "stackoverflow.com": "Stack Overflow",
    "chatgpt.com": "ChatGPT",
    "openai.com": "OpenAI",
    "spotify.com": "Spotify",
    "tiktok.com": "TikTok",
    "pinterest.com": "Pinterest",
    "medium.com": "Medium",
    "notion.so": "Notion",
    "figma.com": "Figma",
    "slack.com": "Slack",
    "zoom.us": "Zoom",
}


def get_website_display_name(domain: str) -> str:
    """Returns friendly brand name for well-known domains or a clean capitalized title."""
    d = (domain or "").strip().lower()
    if d.startswith("www."):
        d = d[4:]
    if d in _KNOWN_WEBSITES:
        return _KNOWN_WEBSITES[d]
    parts = d.split(".")
    if len(parts) >= 2:
        return parts[0].replace("-", " ").title()
    return d.title()


class _ChoiceCard(QFrame):
    clicked = Signal()

    def __init__(self, icon_name: str, icon_color: str, title: str, description: str, action_text: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("choiceCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        self.ico = QLabel()
        self.ico.setFixedSize(28, 28)
        self.ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico.setPixmap(get_icon(icon_name, color=icon_color, size=24).pixmap(24, 24))
        layout.addWidget(self.ico)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("choiceCardTitle")
        lbl_desc = QLabel(description)
        lbl_desc.setObjectName("choiceCardDesc")
        lbl_desc.setWordWrap(True)
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_desc)
        layout.addLayout(text_layout, 1)

        if action_text:
            self.lbl_action = QLabel(action_text)
            self.lbl_action.setObjectName("choiceCardAction")
            layout.addWidget(self.lbl_action, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class AddTimerChoiceDialog(QDialog):
    """
    Sleek modal presenting the user with the choice to add an
    Application Timer or a Website Timer.
    """
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.choice: Optional[str] = None  # "app" or "website"
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("choiceContainer")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        # Header
        top_box = QVBoxLayout()
        top_box.setSpacing(4)
        title = QLabel("Add Timer")
        title.setObjectName("choiceTitle")
        sub = QLabel("Choose what you would like to set a daily time limit for.")
        sub.setObjectName("choiceSubtitle")
        top_box.addWidget(title)
        top_box.addWidget(sub)
        layout.addLayout(top_box)

        # Choice Cards
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(12)

        # Option 1: Application Timer
        self.card_app = _ChoiceCard(
            icon_name="clock",
            icon_color="#0A84FF",
            title="Application Timer",
            description="Limit active screen time for an installed or running desktop application.",
            action_text="Continue →",
            parent=container,
        )
        self.card_app.clicked.connect(lambda: self._select_choice("app"))
        cards_layout.addWidget(self.card_app)

        # Option 2: Website Timer (Restrained teal tone)
        self.card_web = _ChoiceCard(
            icon_name="globe",
            icon_color="#40C8E0",
            title="Website Timer",
            description="Limit active time spent on a specific website across all browsers.",
            action_text="Continue →",
            parent=container,
        )
        self.card_web.clicked.connect(lambda: self._select_choice("website"))
        cards_layout.addWidget(self.card_web)

        layout.addLayout(cards_layout)

        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("choiceCancelBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(container)
        self._apply_dialog_theme()

    def _select_choice(self, choice: str):
        self.choice = choice
        self.accept()

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg_col = "#1A1A1C" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        card_bg = "rgba(255, 255, 255, 0.03)" if is_dark else "#F5F5F7"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        card_hover = "rgba(255, 255, 255, 0.07)" if is_dark else "#F5F5F7"
        card_hover_border = "rgba(10, 132, 255, 0.45)"
        web_ico_col = "#63E6E2" if is_dark else "#30B0C7"
        app_ico_col = "#409CFF" if is_dark else "#0A84FF"
        action_col = "#409CFF" if is_dark else "#0A84FF"

        if hasattr(self, "card_app"):
            self.card_app.ico.setPixmap(get_icon("clock", color=app_ico_col, size=24).pixmap(24, 24))
        if hasattr(self, "card_web"):
            self.card_web.ico.setPixmap(get_icon("globe", color=web_ico_col, size=24).pixmap(24, 24))

        self.setStyleSheet(f"""
            QFrame#choiceContainer {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
            QLabel#choiceTitle {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#choiceSubtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QFrame#choiceCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
            QFrame#choiceCard:hover {{
                background-color: {card_hover};
                border: 1px solid {card_hover_border};
            }}
            QLabel#choiceCardTitle {{
                font-size: 15px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#choiceCardDesc {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QLabel#choiceCardAction {{
                font-size: 13px;
                font-weight: 700;
                color: {action_col};
                margin-left: 8px;
            }}
            QPushButton#choiceCancelBtn {{
                background-color: transparent;
                border: 1px solid {border_col};
                border-radius: 8px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 6px 18px;
            }}
            QPushButton#choiceCancelBtn:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {tm.color('text_main')};
            }}
        """)


def is_browser_app(process_name: str, display_name: str = "") -> bool:
    """Detect whether a selected application represents a recognized web browser."""
    from tracker.foreground import BROWSER_PROCESSES
    import re
    
    p = (process_name or "").strip().lower()
    p_exe = p if p.endswith(".exe") else f"{p}.exe"
    if p in BROWSER_PROCESSES or p_exe in BROWSER_PROCESSES:
        return True

    # Tokenized word matching to prevent substring collisions (e.g. 'tor' in 'calculator')
    words = set(re.findall(r"[a-z0-9]+", (display_name or "").lower()))
    words.update(re.findall(r"[a-z0-9]+", p.removesuffix(".exe")))
    
    for bp in BROWSER_PROCESSES:
        base = bp.removesuffix(".exe")
        if base in words or (base == "msedge" and "edge" in words):
            return True
    return False


class BrowserTimerChoiceDialog(QDialog):
    """
    Sleek modal presenting the user with the choice to limit the entire browser
    or specific websites inside the browser.
    """
    def __init__(self, parent=None, browser_name: str = "Browser", process_name: str = ""):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.browser_name = browser_name
        self.process_name = process_name
        self.choice: Optional[str] = None  # "entire" or "websites"
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        container = QFrame()
        container.setObjectName("choiceContainer")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(20)

        # Header
        top_box = QVBoxLayout()
        top_box.setSpacing(4)
        title = QLabel("What do you want to limit?")
        title.setObjectName("choiceTitle")
        b_name = self.browser_name or "this browser"
        sub = QLabel(f"Choose how you want to apply limits to {b_name}.")
        sub.setObjectName("choiceSubtitle")
        top_box.addWidget(title)
        top_box.addWidget(sub)
        layout.addLayout(top_box)

        # Choice Cards
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(12)

        # Option 1: Entire Browser
        self.card_entire = _ChoiceCard(
            icon_name="browser",
            icon_color="#0A84FF",
            title="Entire Browser",
            description=f"Limit total time spent using {b_name}.",
            action_text="Continue →",
            parent=container,
        )
        self.card_entire.clicked.connect(lambda: self._select_choice("entire"))
        cards_layout.addWidget(self.card_entire)

        # Option 2: Specific Websites (Restrained teal tone)
        self.card_websites = _ChoiceCard(
            icon_name="globe",
            icon_color="#40C8E0",
            title="Specific Websites",
            description=f"Limit individual websites inside {b_name}.",
            action_text="Continue →",
            parent=container,
        )
        self.card_websites.clicked.connect(lambda: self._select_choice("websites"))
        cards_layout.addWidget(self.card_websites)

        layout.addLayout(cards_layout)

        # Cancel button
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("choiceCancelBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedHeight(36)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(container)
        self._apply_dialog_theme()

    def _select_choice(self, choice: str):
        self.choice = choice
        self.accept()

    def _apply_dialog_theme(self):
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        bg_col = "#1A1A1C" if is_dark else "#FFFFFF"
        border_col = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"
        card_bg = "rgba(255, 255, 255, 0.03)" if is_dark else "#F5F5F7"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        card_hover = "rgba(255, 255, 255, 0.07)" if is_dark else "#F5F5F7"
        card_hover_border = "rgba(10, 132, 255, 0.45)"
        entire_ico_col = "#409CFF" if is_dark else "#0A84FF"
        web_ico_col = "#63E6E2" if is_dark else "#30B0C7"
        action_col = "#409CFF" if is_dark else "#0A84FF"

        if hasattr(self, "card_entire"):
            self.card_entire.ico.setPixmap(get_icon("browser", color=entire_ico_col, size=24).pixmap(24, 24))
        if hasattr(self, "card_websites"):
            self.card_websites.ico.setPixmap(get_icon("globe", color=web_ico_col, size=24).pixmap(24, 24))

        self.setStyleSheet(f"""
            QFrame#choiceContainer {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 16px;
            }}
            QLabel#choiceTitle {{
                font-size: 20px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QLabel#choiceSubtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QFrame#choiceCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
            QFrame#choiceCard:hover {{
                background-color: {card_hover};
                border: 1px solid {card_hover_border};
            }}
            QLabel#choiceCardTitle {{
                font-size: 15px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#choiceCardDesc {{
                font-size: 12px;
                color: {tm.color('text_sub')};
            }}
            QLabel#choiceCardAction {{
                font-size: 13px;
                font-weight: 700;
                color: {action_col};
                margin-left: 8px;
            }}
            QPushButton#choiceCancelBtn {{
                background-color: transparent;
                border: 1px solid {border_col};
                border-radius: 8px;
                color: {tm.color('text_sub')};
                font-size: 12px;
                font-weight: 600;
                padding: 6px 18px;
            }}
            QPushButton#choiceCancelBtn:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {tm.color('text_main')};
            }}
        """)


class _UnifiedTimerRow(QFrame):
    """
    Unified timer card row supporting both Application Timers and Website Timers.
    Displays name, subtle type badge, usage, limit, progress bar, status pill, and actions.
    """
    remove_requested = Signal(str, str, str)  # timer_type, identifier, display_name
    configure_requested = Signal(str, str)     # timer_type, identifier

    def __init__(
        self,
        timer_type: str,
        identifier: str,
        display_name: str,
        secondary_text: str,
        rule: dict,
        used_seconds: float = 0.0,
        parent=None,
    ):
        super().__init__(parent)
        self._timer_type = timer_type  # "app" or "website"
        self._identifier = identifier  # e.g. "discord.exe" or "youtube.com"
        self._display_name = display_name
        self._secondary_text = secondary_text
        self._rule = rule or {}
        self._used_s = used_seconds
        self.setObjectName("timer_app_card")
        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(lambda _: self._apply_card_theme())
        self._apply_card_theme()

    @property
    def timer_type(self) -> str:
        return self._timer_type

    @property
    def identifier(self) -> str:
        return self._identifier

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)

        # Left Icon
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(40, 40)
        self._icon_lbl.setObjectName("timer_row_icon")
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if self._timer_type == "app":
            icon_provider = AppIconProvider()
            icon = icon_provider.get_icon(self._identifier)
            if not icon.isNull():
                self._icon_lbl.setPixmap(icon.pixmap(QSize(38, 38)))
            else:
                self._icon_lbl.setPixmap(get_icon("clock", color="#0A84FF", size=24).pixmap(38, 38))
        else:
            # Website timer icon: Refined teal globe
            self._icon_lbl.setPixmap(get_icon("globe", color="#40C8E0", size=24).pixmap(38, 38))

        layout.addWidget(self._icon_lbl)

        # Center Info Column
        center_col = QVBoxLayout()
        center_col.setSpacing(5)

        # Top Header Row: Name + Type Badge + Domain/Exe + Status Pill
        top_h = QHBoxLayout()
        top_h.setSpacing(8)

        name_lbl = QLabel(self._display_name)
        name_lbl.setObjectName("timer_app_name")
        name_lbl.setMaximumWidth(260)
        name_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        tooltip_info = f"{self._display_name} ({self._secondary_text})" if self._secondary_text else self._display_name
        name_lbl.setToolTip(tooltip_info)
        top_h.addWidget(name_lbl)

        # Type Badge Pill (subtle pill)
        type_badge = QLabel("APPLICATION" if self._timer_type == "app" else "WEBSITE")
        type_badge.setObjectName("timer_type_app_badge" if self._timer_type == "app" else "timer_type_web_badge")
        top_h.addWidget(type_badge)

        # Optional secondary domain / exe caption if distinct
        if self._secondary_text and self._secondary_text.lower() != self._display_name.lower():
            sec_lbl = QLabel(self._secondary_text)
            sec_lbl.setObjectName("timer_domain_lbl")
            sec_lbl.setMaximumWidth(220)
            sec_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            top_h.addWidget(sec_lbl)

        top_h.addStretch()

        # Status & Remaining Pill
        limit_s = self._rule.get("limit_seconds", 3600)
        used_s = self._used_s
        is_unlimited = limit_s <= 0

        if is_unlimited:
            remaining_s = 0
            pct = 0
            self._rem_pill = QLabel("Unlimited")
            self._rem_pill.setObjectName("remaining_pill_unlimited")
        else:
            remaining_s = max(0, limit_s - used_s)
            pct = int(min(100, (used_s / max(limit_s, 1)) * 100))
            if remaining_s == 0 or pct >= 100:
                self._rem_pill = QLabel("Limit reached")
                self._rem_pill.setObjectName("remaining_pill_exceeded")
            elif pct >= 75:
                self._rem_pill = QLabel(f"{_format_time_short(remaining_s)} left")
                self._rem_pill.setObjectName("remaining_pill_warning")
            else:
                self._rem_pill = QLabel(f"{_format_time_short(remaining_s)} left")
                self._rem_pill.setObjectName("remaining_pill_ok")

        top_h.addWidget(self._rem_pill)
        center_col.addLayout(top_h)

        # Subtitle: Usage & Limit & Reset Schedule
        if is_unlimited:
            sub_text = f"{_format_time_short(used_s)} used  /  Unlimited limit  ·  Resets at midnight"
        else:
            sub_text = f"{_format_time_short(used_s)} used  /  {_format_time_short(limit_s)} limit  ·  Resets at midnight"

        sub_lbl = QLabel(sub_text)
        sub_lbl.setObjectName("timer_usage_sub")
        center_col.addWidget(sub_lbl)

        # Progress Bar Row
        bar_row = QHBoxLayout()
        bar_row.setSpacing(10)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setObjectName("timer_progress_bar")
        self._progress_bar.setValue(pct if not is_unlimited else 0)
        bar_row.addWidget(self._progress_bar, 1)

        pct_text = f"{pct}%" if not is_unlimited else "—"
        pct_lbl = QLabel(pct_text)
        pct_lbl.setObjectName("timer_pct_text")
        pct_lbl.setMinimumWidth(36)
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar_row.addWidget(pct_lbl)

        center_col.addLayout(bar_row)
        layout.addLayout(center_col, 1)

        # Action Buttons Column (fixed width container prevents viewport squeeze)
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        edit_btn = QPushButton("Edit")
        edit_btn.setObjectName("timer_edit_btn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedHeight(32)
        edit_btn.setFixedWidth(64)
        edit_btn.clicked.connect(lambda: self.configure_requested.emit(self._timer_type, self._identifier))
        action_layout.addWidget(edit_btn)

        remove_btn = QPushButton("Delete")
        remove_btn.setObjectName("timer_remove_btn")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setFixedHeight(32)
        remove_btn.setFixedWidth(72)
        remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self._timer_type, self._identifier, self._display_name)
        )
        action_layout.addWidget(remove_btn)

        action_widget.setFixedWidth(148)
        layout.addWidget(action_widget)

        self._lbl_name = name_lbl
        self._lbl_type_badge = type_badge
        self._lbl_domain = sec_lbl if (self._secondary_text and self._secondary_text.lower() != self._display_name.lower()) else name_lbl
        self._lbl_usage_text = sub_lbl
        self._lbl_remaining = self._rem_pill
        self._pct_lbl = pct_lbl
        self._edit_btn = edit_btn
        self._remove_btn = remove_btn

    @property
    def lbl_title(self) -> QLabel:
        return self._lbl_name

    def _apply_card_theme(self) -> None:
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        limit_s = self._rule.get("limit_seconds", 3600)
        is_unlimited = limit_s <= 0
        pct = int(min(100, (self._used_s / max(limit_s, 1)) * 100)) if not is_unlimited else 0

        if is_unlimited:
            chunk_color = tm.color("text_muted")
            pill_bg = "rgba(142, 142, 147, 0.14)"
            pill_border = "rgba(142, 142, 147, 0.28)"
            pill_text = "#A1A1A6" if is_dark else "#6E6E73"
        elif pct >= 100:
            chunk_color = "#FF453A"
            pill_bg = "rgba(255, 69, 58, 0.20)" if is_dark else "rgba(255, 69, 58, 0.12)"
            pill_border = "rgba(255, 69, 58, 0.38)" if is_dark else "rgba(255, 69, 58, 0.30)"
            pill_text = "#FF6B61" if is_dark else "#FF3B30"
        elif pct >= 75:
            chunk_color = "#FF9F0A"
            pill_bg = "rgba(255, 159, 10, 0.18)" if is_dark else "rgba(255, 159, 10, 0.12)"
            pill_border = "rgba(255, 159, 10, 0.38)" if is_dark else "rgba(255, 159, 10, 0.30)"
            pill_text = "#FFD60A" if is_dark else "#FF9500"
        else:
            chunk_color = "#0A84FF"
            pill_bg = "rgba(10, 132, 255, 0.16)" if is_dark else "rgba(10, 132, 255, 0.12)"
            pill_border = "rgba(10, 132, 255, 0.35)" if is_dark else "rgba(10, 132, 255, 0.30)"
            pill_text = "#409CFF" if is_dark else "#0A84FF"

        # Theme-tailored card surfaces & badges (Emerald for App, Teal for Website)
        if is_dark:
            card_bg = "rgba(42, 42, 46, 0.92)"
            card_hover = "rgba(28, 28, 30, 0.96)"
            border_col = "rgba(255, 255, 255, 0.08)"
            border_hover = "rgba(255, 255, 255, 0.18)"
            app_badge_text = "#409CFF"
            app_badge_bg = "rgba(10, 132, 255, 0.14)"
            app_badge_border = "rgba(10, 132, 255, 0.30)"
            web_badge_text = "#63E6E2"
            web_badge_bg = "rgba(100, 210, 255, 0.14)"
            web_badge_border = "rgba(100, 210, 255, 0.30)"
            edit_btn_bg = "rgba(255, 255, 255, 0.05)"
            edit_btn_border = "rgba(255, 255, 255, 0.10)"
            edit_btn_hover = "rgba(255, 255, 255, 0.12)"
            del_btn_color = "#FF6B61"
            del_btn_bg = "rgba(255, 69, 58, 0.12)"
            del_btn_border = "rgba(255, 69, 58, 0.30)"
            del_btn_hover = "rgba(255, 69, 58, 0.25)"
            globe_color = "#40C8E0"
        else:
            card_bg = "#FFFFFF"
            card_hover = "#F5F5F7"
            border_col = "rgba(0, 0, 0, 0.08)"
            border_hover = "rgba(0, 0, 0, 0.15)"
            app_badge_text = "#0A84FF"
            app_badge_bg = "rgba(10, 132, 255, 0.12)"
            app_badge_border = "rgba(10, 132, 255, 0.30)"
            web_badge_text = "#30B0C7"
            web_badge_bg = "rgba(48, 176, 199, 0.12)"
            web_badge_border = "rgba(48, 176, 199, 0.30)"
            edit_btn_bg = "#F5F5F7"
            edit_btn_border = "rgba(0, 0, 0, 0.08)"
            edit_btn_hover = "#E5E5EA"
            del_btn_color = "#FF3B30"
            del_btn_bg = "rgba(255, 69, 58, 0.10)"
            del_btn_border = "rgba(255, 69, 58, 0.24)"
            del_btn_hover = "rgba(255, 69, 58, 0.22)"
            globe_color = "#30B0C7"

        if self._timer_type == "website" and hasattr(self, "_icon_lbl"):
            self._icon_lbl.setPixmap(get_icon("globe", color=globe_color, size=24).pixmap(38, 38))

        self.setStyleSheet(f"""
            QFrame#timer_app_card {{
                background-color: {card_bg};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            QFrame#timer_app_card:hover {{
                background-color: {card_hover};
                border-color: {border_hover};
            }}
            QLabel#timer_app_name {{
                font-size: 15px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.2px;
            }}
            QLabel#timer_domain_lbl {{
                font-size: 12px;
                color: {tm.color('text_muted')};
                font-family: monospace;
            }}
            QLabel#timer_type_app_badge {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
                color: {app_badge_text};
                background: {app_badge_bg};
                border: 1px solid {app_badge_border};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QLabel#timer_type_web_badge {{
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
                color: {web_badge_text};
                background: {web_badge_bg};
                border: 1px solid {web_badge_border};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QLabel#timer_usage_sub {{
                font-size: 12px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QLabel#timer_pct_text {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                font-family: monospace;
            }}
            QLabel#remaining_pill_ok, QLabel#remaining_pill_warning, QLabel#remaining_pill_exceeded, QLabel#remaining_pill_unlimited {{
                font-size: 11px;
                font-weight: 700;
                color: {pill_text};
                background: {pill_bg};
                border: 1px solid {pill_border};
                border-radius: 10px;
                padding: 2px 8px;
            }}
            QProgressBar#timer_progress_bar {{
                background: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 3px;
            }}
            QProgressBar#timer_progress_bar::chunk {{
                background: {chunk_color};
                border-radius: 3px;
            }}
            QPushButton#timer_edit_btn {{
                background-color: {edit_btn_bg};
                border: 1px solid {edit_btn_border};
                border-radius: 8px;
                color: {tm.color('text_main')};
                font-size: 12px;
                font-weight: 600;
                padding: 4px 14px;
            }}
            QPushButton#timer_edit_btn:hover {{
                background-color: {edit_btn_hover};
            }}
            QPushButton#timer_remove_btn {{
                background-color: {del_btn_bg};
                border: 1px solid {del_btn_border};
                border-radius: 8px;
                color: {del_btn_color};
                font-size: 12px;
                font-weight: 600;
                padding: 4px 14px;
            }}
            QPushButton#timer_remove_btn:hover {{
                background-color: {del_btn_hover};
                color: #FFFFFF;
            }}
        """)


# Compatibility alias
_TimerAppRow = _UnifiedTimerRow


class AppTimerPage(QWidget):
    """
    Unified Timer Dashboard page supporting both Application Timers and Website Timers.
    Strictly independent from App Locker.
    """

    def __init__(self, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("app_timer_root")
        self._repo = Repository()
        
        self._pm = protection_manager
        if not self._pm:
            from protection.core import ProtectionManager
            self._pm = ProtectionManager(self._repo)

        self._filter_type: str = "all"  # "all", "apps", "websites"
        self._timer_rows: List[_UnifiedTimerRow] = []
        self._kpi_icons: List[tuple[QLabel, str]] = []

        self._setup_ui()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("app_timer_scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner.setObjectName("app_timer_inner")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(32, 28, 32, 28)
        self._inner_layout.setSpacing(24)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # Header Row: Title & Subtitle on Left, Add Timer on Right
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("App Timer")
        title.setObjectName("page_title")
        subtitle = QLabel("Set daily active time limits for applications and websites.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch()

        self._add_btn = QPushButton("+  Add Timer")
        self._add_btn.setObjectName("timer_primary_add_btn")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.setFixedHeight(40)
        self._add_btn.clicked.connect(self._on_add_timer)
        header_row.addWidget(self._add_btn)

        self._inner_layout.addLayout(header_row)

        # Summary Bar (Active Limits, Tracking Status)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(14)
        self._kpi_active_timers = self._create_kpi_card("ACTIVE TIMERS", "0 timers", "clock", summary_row)
        self._kpi_over_limit = self._create_kpi_card("LIMIT EXCEEDED", "0 timers", "shield", summary_row)
        self._kpi_resets = self._create_kpi_card("SCHEDULE", "Resets at Midnight", "hourglass", summary_row)
        self._inner_layout.addLayout(summary_row)

        # Section Header Row with Filter Pills
        section_row = QHBoxLayout()
        section_row.setSpacing(12)

        lbl_list = QLabel("CONFIGURED TIMERS")
        lbl_list.setObjectName("section_header")
        section_row.addWidget(lbl_list)
        section_row.addStretch()

        # Filter Pills: ALL | APPLICATIONS | WEBSITES
        self._filter_container = QWidget()
        filter_layout = QHBoxLayout(self._filter_container)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(6)

        self._btn_filter_all = QPushButton("ALL")
        self._btn_filter_apps = QPushButton("APPLICATIONS")
        self._btn_filter_web = QPushButton("WEBSITES")

        for btn, f_type in (
            (self._btn_filter_all, "all"),
            (self._btn_filter_apps, "apps"),
            (self._btn_filter_web, "websites")
        ):
            btn.setObjectName("timer_filter_pill")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.clicked.connect(lambda checked=False, ft=f_type: self._set_filter(ft))
            filter_layout.addWidget(btn)

        self._btn_filter_all.setChecked(True)
        section_row.addWidget(self._filter_container)
        self._inner_layout.addLayout(section_row)

        # Dynamic App & Website List Layout
        self._apps_layout = QVBoxLayout()
        self._apps_layout.setSpacing(12)
        self._inner_layout.addLayout(self._apps_layout)

        # Empty State Card
        self._empty_frame = QFrame()
        self._empty_frame.setObjectName("empty_state_frame")
        empty_layout = QVBoxLayout(self._empty_frame)
        empty_layout.setContentsMargins(32, 36, 32, 36)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._empty_icon = QLabel()
        self._empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self._empty_icon)

        empty_title = QLabel("No Timers Configured")
        empty_title.setObjectName("empty_title")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)

        empty_sub = QLabel("Set daily limits for applications and websites to stay intentional.")
        empty_sub.setObjectName("empty_sub")
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_sub)

        empty_add = QPushButton("Set First Timer")
        empty_add.setObjectName("timer_primary_add_btn")
        empty_add.setCursor(Qt.CursorShape.PointingHandCursor)
        empty_add.setFixedHeight(38)
        empty_add.clicked.connect(self._on_add_timer)
        empty_layout.addWidget(empty_add, 0, Qt.AlignmentFlag.AlignCenter)

        self._inner_layout.addWidget(self._empty_frame)
        self._inner_layout.addStretch()

        self._refresh_timers()

    def _create_kpi_card(self, title: str, default_val: str, icon_name: str, layout: QHBoxLayout) -> QLabel:
        tm = ThemeManager.instance()
        card = QFrame()
        card.setObjectName("v2_card")
        l = QVBoxLayout(card)
        l.setContentsMargins(18, 14, 18, 14)
        l.setSpacing(4)
        
        top_h = QHBoxLayout()
        top_h.setSpacing(8)
        lbl_title = QLabel(title)
        lbl_title.setObjectName("metric_hdr")
        top_h.addWidget(lbl_title)
        top_h.addStretch()
        
        ico = QLabel()
        ico.setPixmap(get_icon(icon_name, color=tm.color("text_muted"), size=14).pixmap(14, 14))
        top_h.addWidget(ico)
        l.addLayout(top_h)
        
        lbl_val = QLabel(default_val)
        lbl_val.setObjectName("metric_val_success")
        l.addWidget(lbl_val)
        
        self._kpi_icons.append((ico, icon_name))
        layout.addWidget(card, 1)
        return lbl_val

    def _set_filter(self, filter_type: str) -> None:
        self._filter_type = filter_type
        self._btn_filter_all.setChecked(filter_type == "all")
        self._btn_filter_apps.setChecked(filter_type == "apps")
        self._btn_filter_web.setChecked(filter_type == "websites")
        self._update_filter_visibility()

    def _update_filter_visibility(self) -> None:
        ft = self._filter_type
        for row in self._timer_rows:
            if ft == "all":
                row.setVisible(True)
            elif ft == "apps":
                row.setVisible(row.timer_type == "app")
            elif ft == "websites":
                row.setVisible(row.timer_type == "website")

    def _refresh_timers(self) -> None:
        """Rebuild both application and website timer rows from DB with live usage."""
        while self._apps_layout.count():
            item = self._apps_layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._timer_rows.clear()

        # 1. Fetch Application Timers
        limits_dict = self._pm.limits.get_all_limits() if self._pm else {}
        active_app_timers = {
            k: v for k, v in limits_dict.items()
            if v is not None and v.get("limit_seconds", 0) > 0
        }

        # 2. Fetch Website Timers
        web_limits_dict = self._pm.website_limits.get_all_limits() if (self._pm and hasattr(self._pm, "website_limits")) else {}
        active_web_timers = {
            k: v for k, v in web_limits_dict.items()
            if v is not None and v.get("limit_seconds", 0) > 0
        }

        total_active = len(active_app_timers) + len(active_web_timers)
        has_timers = total_active > 0

        self._empty_frame.setVisible(not has_timers)
        self._filter_container.setVisible(has_timers)

        self._kpi_active_timers.setText(f"{total_active} {'timer' if total_active == 1 else 'timers'}")

        over_limit_count = 0
        from tracker.categorizer import display_name as get_friendly_name

        # Build Application Timer Rows
        for proc, rule in active_app_timers.items():
            used_s = self._pm.timer.get_time(proc) if self._pm else 0.0
            limit_s = rule.get("limit_seconds", 3600)
            if limit_s > 0 and used_s >= limit_s:
                over_limit_count += 1

            disp_name = get_friendly_name(proc)
            if not disp_name or disp_name.lower() == proc.lower():
                try:
                    from utils.win_utils import clean_fallback_name
                    disp_name = clean_fallback_name(proc)
                except Exception:
                    disp_name = proc.replace(".exe", "").title()

            row = _UnifiedTimerRow(
                timer_type="app",
                identifier=proc,
                display_name=disp_name,
                secondary_text=proc,
                rule=rule,
                used_seconds=used_s,
                parent=self
            )
            row.remove_requested.connect(self._on_remove_item)
            row.configure_requested.connect(self._on_configure_item)
            self._timer_rows.append(row)
            self._apps_layout.addWidget(row)

        # Build Website Timer Rows
        for domain, rule in active_web_timers.items():
            used_s = self._pm.website_timer.get_time(domain) if (self._pm and hasattr(self._pm, "website_timer")) else 0.0
            limit_s = rule.get("limit_seconds", 3600)
            if limit_s > 0 and used_s >= limit_s:
                over_limit_count += 1

            disp_name = get_website_display_name(domain)

            row = _UnifiedTimerRow(
                timer_type="website",
                identifier=domain,
                display_name=disp_name,
                secondary_text=domain,
                rule=rule,
                used_seconds=used_s,
                parent=self
            )
            row.remove_requested.connect(self._on_remove_item)
            row.configure_requested.connect(self._on_configure_item)
            self._timer_rows.append(row)
            self._apps_layout.addWidget(row)

        self._kpi_over_limit.setText(f"{over_limit_count} {'timer' if over_limit_count == 1 else 'timers'}")
        self._update_filter_visibility()

    def _on_add_timer(self) -> None:
        """Presents choice modal between Application Timer and Website Timer."""
        choice_dialog = AddTimerChoiceDialog(self.window())
        if choice_dialog.exec() and choice_dialog.choice:
            if choice_dialog.choice == "app":
                self._on_add_app()
            elif choice_dialog.choice == "website":
                self._on_add_website()

    def _on_add_app(self) -> None:
        """Opens process picker and configures an Application Timer or browser flow."""
        from ui.widgets.process_picker import ProcessPickerDialog
        dialog = ProcessPickerDialog(self, mode="timer")
        if dialog.exec():
            proc = dialog.selected_process_name
            disp_name = dialog.selected_display_name or proc
            
            # If the selected application is a recognized browser, offer Entire Browser vs Specific Websites choice
            if is_browser_app(proc, disp_name):
                choice_dialog = BrowserTimerChoiceDialog(
                    self.window(),
                    browser_name=disp_name,
                    process_name=proc
                )
                if not choice_dialog.exec() or not choice_dialog.choice:
                    return  # Cancelled choice dialog, do not create any timer
                
                if choice_dialog.choice == "websites":
                    from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
                    cfg_dialog = WebsiteTimerConfigDialog(
                        self.window(),
                        browser_name=disp_name,
                        browser_process=proc
                    )
                    if cfg_dialog.exec():
                        domain, rule = cfg_dialog.get_data()
                        if domain and rule.get("limit_seconds", 0) > 0:
                            self._pm.website_limits.set_limit_rule(proc, domain, rule)
                            self._refresh_timers()
                    return

            # Non-browser application OR user chose "entire"
            default_rule = {
                "limit_seconds": 3600,
                "repeat_days": [0, 1, 2, 3, 4, 5, 6],
                "notifications": [15, 10, 5, 1],
                "on_expire": "lock"
            }
            from ui.widgets.app_timer_widgets import TimerConfigDialog
            cfg_dialog = TimerConfigDialog(self.window(), default_rule)
            if cfg_dialog.exec():
                rule = cfg_dialog.get_rule()
                self._pm.limits.set_limit_rule(proc, rule)
                self._refresh_timers()

    def _on_add_website(self) -> None:
        """Opens website config dialog and configures a Website Timer."""
        from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
        cfg_dialog = WebsiteTimerConfigDialog(self.window())
        if cfg_dialog.exec():
            domain, rule = cfg_dialog.get_data()
            if domain and rule.get("limit_seconds", 0) > 0:
                self._pm.website_limits.set_limit_rule("*", domain, rule)
                self._refresh_timers()

    def _on_configure_item(self, timer_type: str, identifier: str) -> None:
        """Opens edit dialog for the specified timer."""
        if timer_type == "app":
            current_rule = self._pm.limits.get_limit_rule(identifier)
            if not current_rule:
                return
            from ui.widgets.app_timer_widgets import TimerConfigDialog
            cfg_dialog = TimerConfigDialog(self.window(), current_rule)
            if cfg_dialog.exec():
                rule = cfg_dialog.get_rule()
                self._pm.limits.set_limit_rule(identifier, rule)
                self._refresh_timers()
        elif timer_type == "website":
            browser_proc = self._pm.website_limits.get_browser_for_domain(identifier) or "*"
            current_rule = self._pm.website_limits.get_limit_rule(browser_proc, identifier)
            if not current_rule:
                return
            from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
            cfg_dialog = WebsiteTimerConfigDialog(
                self.window(),
                domain=identifier,
                rule=current_rule,
                browser_process=browser_proc
            )
            if cfg_dialog.exec():
                _, rule = cfg_dialog.get_data()
                if rule.get("limit_seconds", 0) > 0:
                    self._pm.website_limits.set_limit_rule(browser_proc, identifier, rule)
                    self._refresh_timers()

    def _on_remove_item(self, timer_type: str, identifier: str, display_name: str) -> None:
        """Prompts confirmation and removes the specified timer."""
        mb = QMessageBox(self)
        mb.setWindowTitle("Remove Timer")
        entity_name = "website" if timer_type == "website" else "application"
        mb.setText(
            f"Remove daily timer for {display_name}?\n\nThis {entity_name} will no longer have time restrictions."
        )
        mb.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        mb.setDefaultButton(QMessageBox.StandardButton.No)
        if mb.exec() == QMessageBox.StandardButton.Yes:
            if timer_type == "app":
                self._pm.limits.set_limit_rule(identifier, None)
            else:
                browser_proc = self._pm.website_limits.get_browser_for_domain(identifier)
                self._pm.website_limits.remove_website_limit(identifier, browser_process=browser_proc)
            self._refresh_timers()

    def _apply_theme(self, is_dark: bool = True) -> None:
        tm = ThemeManager.instance()
        is_dark = is_dark if isinstance(is_dark, bool) else tm.is_dark
        icon_col = tm.color('text_muted')

        if hasattr(self, "_empty_icon"):
            self._empty_icon.setPixmap(get_icon("clock", color=icon_col, size=32).pixmap(32, 32))

        for ico_lbl, ico_name in getattr(self, "_kpi_icons", []):
            ico_lbl.setPixmap(get_icon(ico_name, color=icon_col, size=14).pixmap(14, 14))

        bg_color = tm.color('bg') if is_dark else "#F5F5F7"
        kpi_card_bg = "rgba(42, 42, 46, 0.92)" if is_dark else "#FFFFFF"
        kpi_card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        empty_bg = "rgba(42, 42, 46, 0.60)" if is_dark else "#FFFFFF"
        empty_border = "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(0, 0, 0, 0.12)"

        self.setStyleSheet(f"""
            QWidget#app_timer_root {{
                background-color: {bg_color};
            }}
            QScrollArea#app_timer_scroll {{
                background-color: transparent;
                border: none;
            }}
            QWidget#app_timer_inner {{
                background-color: transparent;
            }}
            QLabel#page_title {{
                font-size: 26px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.5px;
            }}
            QLabel#page_subtitle {{
                font-size: 13px;
                font-weight: 500;
                color: {tm.color('text_sub')};
            }}
            QFrame#v2_card {{
                background-color: {kpi_card_bg};
                border: 1px solid {kpi_card_border};
                border-radius: 12px;
            }}
            QLabel#section_header {{
                font-size: 11px;
                font-weight: 700;
                color: {tm.color('text_muted')};
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-top: 6px;
            }}
            QLabel#metric_hdr {{
                color: {tm.color('text_muted')};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                text-transform: uppercase;
            }}
            QLabel#metric_val_success {{
                font-size: 18px;
                font-weight: 700;
                color: {tm.color('text_main')};
                letter-spacing: -0.3px;
            }}
            QPushButton#timer_primary_add_btn {{
                background-color: {tm.color('accent')};
                color: #FFFFFF;
                border: 1px solid {tm.color('accent')};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 700;
                padding: 8px 18px;
            }}
            QPushButton#timer_primary_add_btn:hover {{
                background-color: {tm.color('accent_hover')};
            }}
            QPushButton#timer_filter_pill {{
                background-color: {tm.color('surface_secondary')};
                border: 1px solid {tm.color('border')};
                border-radius: 14px;
                color: {tm.color('text_sub')};
                font-size: 11px;
                font-weight: 700;
                padding: 4px 12px;
                letter-spacing: 0.5px;
            }}
            QPushButton#timer_filter_pill:checked {{
                background-color: {tm.color('accent')};
                border-color: {tm.color('accent')};
                color: #FFFFFF;
            }}
            QPushButton#timer_filter_pill:hover:!checked {{
                background-color: {tm.color('border')};
                color: {tm.color('text_main')};
            }}
            QFrame#empty_state_frame {{
                background-color: {empty_bg};
                border: 1px dashed {empty_border};
                border-radius: 14px;
            }}
            QLabel#empty_title {{
                font-size: 16px;
                font-weight: 700;
                color: {tm.color('text_main')};
            }}
            QLabel#empty_sub {{
                font-size: 13px;
                color: {tm.color('text_sub')};
            }}
        """)

    def on_data_changed(self) -> None:
        """Called by MainWindow refresh cycle."""
        self._refresh_timers()
