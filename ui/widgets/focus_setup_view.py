"""
focus_setup_view.py — Focus configuration surface (mode, duration, guardrails).

Extracted from FocusTimerWidget. The mixin operates on the host widget's state
and callbacks, so behavior and public attributes remain unchanged.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui import design_system as ds
from ui.icons import get_icon, get_pixmap
from ui.theme import ThemeManager
from ui.widgets.fluent import ToggleSwitch


class FocusSetupViewMixin:
    """Builds the inactive Focus setup cockpit on the host widget."""

    def _build_inactive_view(self) -> None:
        from ui.widgets.focus_timer import AppleFocusRing, FocusModeCard

        layout = QVBoxLayout(self._inactive_view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(ds.PAGE_SECTION_SPACING)

        # ── 1. Mode selection card ─────────────────────────────────────────
        mode_card = QFrame()
        mode_card.setObjectName("focus_section_card")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(*ds.CARD_MARGINS)
        mode_layout.setSpacing(12)

        mode_header = QHBoxLayout()
        mode_text = QVBoxLayout()
        mode_text.setSpacing(2)
        mode_eyebrow = QLabel("FOCUS MODE")
        mode_eyebrow.setObjectName("section_eyebrow")
        mode_sub = QLabel("Pick the shape of this session. The timer and guardrails adapt to it.")
        mode_sub.setObjectName("focus_section_sub")
        mode_text.addWidget(mode_eyebrow)
        mode_text.addWidget(mode_sub)
        mode_header.addLayout(mode_text, 1)
        mode_layout.addLayout(mode_header)

        modes_row = QHBoxLayout()
        modes_row.setSpacing(10)
        self._mode_cards: Dict[str, FocusModeCard] = {}
        for m_id in ("deep", "work", "study", "movie", "custom"):
            card = FocusModeCard(m_id)
            card.clicked.connect(self._set_mode)
            modes_row.addWidget(card, 1)
            self._mode_cards[m_id] = card
        mode_layout.addLayout(modes_row)
        layout.addWidget(mode_card)

        # ── 2. Session + guardrails row ────────────────────────────────────
        body_row = QHBoxLayout()
        body_row.setSpacing(ds.SPACING["lg"])

        # Left: timer / start
        session_card = QFrame()
        session_card.setObjectName("focus_section_card")
        session_card.setMinimumWidth(270)
        session_layout = QVBoxLayout(session_card)
        session_layout.setContentsMargins(*ds.CARD_MARGINS)
        session_layout.setSpacing(12)

        session_eyebrow = QLabel("SESSION")
        session_eyebrow.setObjectName("section_eyebrow")
        session_layout.addWidget(session_eyebrow)

        self._focus_ring = AppleFocusRing()
        session_layout.addWidget(self._focus_ring, 0, Qt.AlignmentFlag.AlignCenter)

        # Duration presets
        presets_frame = QFrame()
        presets_frame.setObjectName("segmented_capsule")
        p_layout = QHBoxLayout(presets_frame)
        p_layout.setContentsMargins(3, 3, 3, 3)
        p_layout.setSpacing(2)
        self._chips = []
        for minutes in (15, 25, 45, 60, 90):
            chip = QPushButton(f"{minutes}m")
            chip.setObjectName("preset_chip")
            chip.setCheckable(True)
            chip.setProperty("minutes", minutes)
            chip.setChecked(minutes == self._selected_minutes)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda checked, m=minutes: self.set_preset(m))
            p_layout.addWidget(chip)
            self._chips.append(chip)
        session_layout.addWidget(presets_frame)

        fine_row = QHBoxLayout()
        fine_row.setSpacing(8)
        self._step_minus_btn = QPushButton("−5m")
        self._step_minus_btn.setObjectName("stepper_btn")
        self._step_minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._step_minus_btn.clicked.connect(lambda: self._adjust_duration(-5))
        fine_row.addWidget(self._step_minus_btn)
        self._step_plus_btn = QPushButton("+5m")
        self._step_plus_btn.setObjectName("stepper_btn")
        self._step_plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._step_plus_btn.clicked.connect(lambda: self._adjust_duration(5))
        fine_row.addWidget(self._step_plus_btn)
        fine_row.addStretch()
        self._start_btn = QPushButton("Start Focus")
        self._start_btn.setObjectName("primary_start_btn")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.setMinimumHeight(42)
        self._start_btn.setIcon(get_icon("play", "#FFFFFF", 15))
        self._start_btn.clicked.connect(self._toggle_timer)
        fine_row.addWidget(self._start_btn, 1)
        session_layout.addLayout(fine_row)

        self._reset_btn = QPushButton("Reset to 25m")
        self._reset_btn.setObjectName("text_link_btn")
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.clicked.connect(self._stop_timer)
        session_layout.addWidget(self._reset_btn, 0, Qt.AlignmentFlag.AlignRight)
        body_row.addWidget(session_card, 5)

        # Right: tabbed guardrails
        guardrails_card = QFrame()
        guardrails_card.setObjectName("focus_section_card")
        guard_layout = QVBoxLayout(guardrails_card)
        guard_layout.setContentsMargins(*ds.CARD_MARGINS)
        guard_layout.setSpacing(10)

        guard_header = QHBoxLayout()
        guard_text = QVBoxLayout()
        guard_text.setSpacing(2)
        guard_eyebrow = QLabel("GUARDRAILS")
        guard_eyebrow.setObjectName("section_eyebrow")
        guard_sub = QLabel("What this session shields you from.")
        guard_sub.setObjectName("focus_section_sub")
        guard_text.addWidget(guard_eyebrow)
        guard_text.addWidget(guard_sub)
        guard_header.addLayout(guard_text, 1)
        guard_layout.addLayout(guard_header)

        tab_row = QHBoxLayout()
        tab_row.setSpacing(4)
        self._guardrail_tabs = []
        for index, label in enumerate(("Apps", "Websites", "URL rules")):
            tab = QPushButton(label)
            tab.setObjectName("guardrail_tab")
            tab.setCheckable(True)
            tab.setChecked(index == 0)
            tab.setCursor(Qt.CursorShape.PointingHandCursor)
            tab.clicked.connect(lambda checked, i=index: self._set_guardrail_tab(i))
            tab_row.addWidget(tab)
            self._guardrail_tabs.append(tab)
        tab_row.addStretch()
        guard_layout.addLayout(tab_row)

        self._guardrail_stack = QStackedWidget()
        # Apps page
        apps_page = QWidget()
        apps_layout = QVBoxLayout(apps_page)
        apps_layout.setContentsMargins(0, 2, 0, 0)
        apps_layout.setSpacing(8)
        apps_header = QHBoxLayout()
        self._list_hdr = QLabel("Permitted Applications")
        self._list_hdr.setObjectName("card_header_title")
        apps_header.addWidget(self._list_hdr)
        self._apps_count_badge = QLabel("0 apps")
        self._apps_count_badge.setObjectName("count_badge")
        apps_header.addWidget(self._apps_count_badge)
        apps_header.addStretch()
        self._add_app_btn = QPushButton("Add")
        self._add_app_btn.setObjectName("action_pill_btn")
        self._add_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_app_btn.setIcon(get_icon("plus", "#0A84FF", 12))
        self._add_app_btn.clicked.connect(self._open_app_picker)
        apps_header.addWidget(self._add_app_btn)
        apps_layout.addLayout(apps_header)
        self._list_sub = QLabel("Only these user applications can run during the session")
        self._list_sub.setObjectName("list_subtitle")
        self._list_sub.setWordWrap(True)
        apps_layout.addWidget(self._list_sub)
        self._blocklist_container = QWidget()
        self._blocklist_layout = QHBoxLayout(self._blocklist_container)
        self._blocklist_layout.setContentsMargins(0, 0, 0, 0)
        self._blocklist_layout.setSpacing(8)
        self._blocklist_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._blocklist_scroll = QScrollArea()
        self._blocklist_scroll.setWidgetResizable(True)
        self._blocklist_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._blocklist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._blocklist_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._blocklist_scroll.setFixedHeight(52)
        self._blocklist_scroll.setWidget(self._blocklist_container)
        apps_layout.addWidget(self._blocklist_scroll)
        apps_layout.addStretch()
        self._guardrail_stack.addWidget(apps_page)

        # Websites page
        web_page = QWidget()
        web_layout = QVBoxLayout(web_page)
        web_layout.setContentsMargins(0, 2, 0, 0)
        web_layout.setSpacing(8)
        web_header = QHBoxLayout()
        self._websites_hdr = QLabel("Blocked Websites")
        self._websites_hdr.setObjectName("card_header_title")
        web_header.addWidget(self._websites_hdr)
        self._websites_count_lbl = QLabel("0 sites")
        self._websites_count_lbl.setObjectName("count_badge")
        web_header.addWidget(self._websites_count_lbl)
        web_header.addStretch()
        self._site_search_input = QLineEdit()
        self._site_search_input.setObjectName("site_search_input")
        self._site_search_input.setPlaceholderText("Filter sites…")
        self._site_search_input.setFixedWidth(120)
        self._site_search_input.setClearButtonEnabled(True)
        self._site_search_input.textChanged.connect(self._on_search_websites)
        web_header.addWidget(self._site_search_input)
        self._add_website_btn = QPushButton("Add")
        self._add_website_btn.setObjectName("action_pill_btn")
        self._add_website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_website_btn.setIcon(get_icon("plus", "#0A84FF", 12))
        self._add_website_btn.clicked.connect(self._open_website_picker)
        web_header.addWidget(self._add_website_btn)
        web_layout.addLayout(web_header)
        self._websites_sub = QLabel("Blocked at DNS + hosts level across every browser")
        self._websites_sub.setObjectName("list_subtitle")
        self._websites_sub.setWordWrap(True)
        web_layout.addWidget(self._websites_sub)
        self._websites_container = QWidget()
        self._websites_layout = QHBoxLayout(self._websites_container)
        self._websites_layout.setContentsMargins(0, 0, 0, 0)
        self._websites_layout.setSpacing(8)
        self._websites_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._websites_scroll = QScrollArea()
        self._websites_scroll.setWidgetResizable(True)
        self._websites_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._websites_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._websites_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._websites_scroll.setFixedHeight(52)
        self._websites_scroll.setWidget(self._websites_container)
        web_layout.addWidget(self._websites_scroll)
        web_layout.addStretch()
        self._guardrail_stack.addWidget(web_page)

        # URL rules page
        rules_page = QWidget()
        rules_layout = QVBoxLayout(rules_page)
        rules_layout.setContentsMargins(0, 2, 0, 0)
        rules_layout.setSpacing(9)
        rules_title = QLabel("Granular sub-path rules")
        rules_title.setObjectName("card_header_title")
        rules_layout.addWidget(rules_title)
        rules_hint = QLabel(
            "Example: block youtube.com/shorts while keeping YouTube, or allow "
            "reddit.com/r/programming while blocking r/all. Enforced in the browser "
            "through the optional local bridge."
        )
        rules_hint.setObjectName("list_subtitle")
        rules_hint.setWordWrap(True)
        rules_layout.addWidget(rules_hint)
        self._rules_count_lbl = QLabel("No URL rules configured")
        self._rules_count_lbl.setObjectName("rules_count")
        rules_layout.addWidget(self._rules_count_lbl)
        rules_actions = QHBoxLayout()
        self._manage_rules_btn = QPushButton("Manage web rules")
        self._manage_rules_btn.setObjectName("secondary_pill_btn")
        self._manage_rules_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._manage_rules_btn.clicked.connect(self._open_url_rules)
        rules_actions.addWidget(self._manage_rules_btn)
        rules_actions.addStretch()
        rules_layout.addLayout(rules_actions)
        self._bridge_status_lbl = QLabel("")
        self._bridge_status_lbl.setObjectName("bridge_status_text")
        self._bridge_status_lbl.setWordWrap(True)
        rules_layout.addWidget(self._bridge_status_lbl)
        rules_layout.addStretch()
        self._guardrail_stack.addWidget(rules_page)

        guard_layout.addWidget(self._guardrail_stack, 1)

        guard_footer = QFrame()
        guard_footer.setObjectName("guardrail_footer")
        footer_layout = QVBoxLayout(guard_footer)
        footer_layout.setContentsMargins(12, 9, 12, 9)
        footer_layout.setSpacing(3)
        safe_apps = QLabel("●  Windows system processes and Digital Wellbeing stay protected")
        safe_apps.setObjectName("guardrail_footer_text")
        safe_web = QLabel("●  Domain blocks use an isolated hosts section; URL rules stay local")
        safe_web.setObjectName("guardrail_footer_text")
        footer_layout.addWidget(safe_apps)
        footer_layout.addWidget(safe_web)
        guard_layout.addWidget(guard_footer)

        body_row.addWidget(guardrails_card, 6)
        layout.addLayout(body_row)

        # ── 3. Session protection card ─────────────────────────────────────
        protection_card = QFrame()
        protection_card.setObjectName("focus_section_card")
        protect_layout = QVBoxLayout(protection_card)
        protect_layout.setContentsMargins(*ds.CARD_MARGINS)
        protect_layout.setSpacing(12)

        protect_header_row = QHBoxLayout()
        protect_header = QLabel("SESSION PROTECTION")
        protect_header.setObjectName("section_eyebrow")
        protect_header_row.addWidget(protect_header)
        protect_header_row.addStretch()
        self._schedules_btn = QPushButton("Schedules")
        self._schedules_btn.setObjectName("action_pill_btn")
        self._schedules_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._schedules_btn.setIcon(get_icon("clock", "#0A84FF", 12))
        self._schedules_btn.clicked.connect(self._open_focus_schedules)
        protect_header_row.addWidget(self._schedules_btn)
        protect_layout.addLayout(protect_header_row)

        strict_row = QHBoxLayout()
        strict_text = QVBoxLayout()
        strict_text.setSpacing(2)
        strict_lbl = QLabel("Strict enforcement")
        strict_lbl.setObjectName("protection_title")
        strict_desc = QLabel("Ending early requires your security PIN.")
        strict_desc.setObjectName("list_subtitle")
        strict_text.addWidget(strict_lbl)
        strict_text.addWidget(strict_desc)
        strict_row.addLayout(strict_text, 1)
        self._strict_switch = ToggleSwitch()
        self._strict_switch.toggled.connect(self._on_strict_toggled)
        strict_row.addWidget(self._strict_switch)
        protect_layout.addLayout(strict_row)

        lockout_row = QHBoxLayout()
        lockout_text = QVBoxLayout()
        lockout_text.setSpacing(2)
        lockout_lbl = QLabel("Lockout (hardcore)")
        lockout_lbl.setObjectName("protection_title")
        lockout_desc = QLabel(
            "No early exit at all: the window cannot be closed or minimized, and a "
            "watchdog relaunches the app if its process is killed. Best-effort, not "
            "a kernel-level or Safe Mode defense."
        )
        lockout_desc.setObjectName("list_subtitle")
        lockout_desc.setWordWrap(True)
        lockout_text.addWidget(lockout_lbl)
        lockout_text.addWidget(lockout_desc)
        lockout_row.addLayout(lockout_text, 1)
        self._lockout_switch = ToggleSwitch()
        self._lockout_switch.setToolTip("Cannot be canceled until the countdown completes.")
        lockout_row.addWidget(self._lockout_switch, 0, Qt.AlignmentFlag.AlignTop)
        protect_layout.addLayout(lockout_row)

        layout.addWidget(protection_card)

        self._site_search_query = ""
        self._quick_preset_btns = {}

    def _set_guardrail_tab(self, index: int) -> None:
        for i, tab in enumerate(getattr(self, "_guardrail_tabs", [])):
            tab.setChecked(i == index)
        if hasattr(self, "_guardrail_stack"):
            self._guardrail_stack.setCurrentIndex(index)
        if index == 2:
            self._refresh_rules_ui()

    def _refresh_rules_ui(self) -> None:
        rules = self._fm.url_rules()
        if rules:
            blocks = sum(1 for r in rules if r.action == "block" and r.enabled)
            allows = sum(1 for r in rules if r.action == "allow" and r.enabled)
            self._rules_count_lbl.setText(
                f"{len(rules)} rule{'s' if len(rules) != 1 else ''} · {blocks} block · {allows} allow"
            )
        else:
            self._rules_count_lbl.setText("No URL rules configured")

        info = self._fm.extension_bridge_info()
        if info.get("running"):
            self._bridge_status_lbl.setText(
                f"● Browser bridge listening on 127.0.0.1:{info.get('port', 0)} · "
                "install the bundled extension to enforce sub-paths."
            )
            self._bridge_status_lbl.setProperty("state", "on")
        else:
            self._bridge_status_lbl.setText(
                "○ Browser bridge offline. Domain blocks still work through hosts; "
                "install the extension for sub-path rules."
            )
            self._bridge_status_lbl.setProperty("state", "off")
        self._bridge_status_lbl.style().unpolish(self._bridge_status_lbl)
        self._bridge_status_lbl.style().polish(self._bridge_status_lbl)

    def _open_url_rules(self) -> None:
        from ui.widgets.url_rules_dialog import UrlRulesDialog

        dialog = UrlRulesDialog(focus_manager=self._fm, parent=self.window())
        dialog.exec()
        self._refresh_rules_ui()
        self._refresh_websites_ui()

    def _open_focus_schedules(self) -> None:
        from protection.focus_schedule import FocusScheduleEngine
        from ui.widgets.focus_schedule_dialog import FocusScheduleDialog

        dialog = FocusScheduleDialog(FocusScheduleEngine(), parent=self.window())
        dialog.exec()


