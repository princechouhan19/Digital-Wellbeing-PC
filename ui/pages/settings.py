"""
settings.py — Settings Page for Digital Wellbeing.
Redesigned with clean category navigation, responsive density,
polished 3-option Appearance Segmented Selector, dynamic theme contrast,
and the SafeBrowse content filter.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QStackedWidget, QSizePolicy, QLineEdit,
    QProgressBar
)

from core.logger import logger
from ui.widgets.fluent import FluentButton
from database.repository import Repository
from settings.manager import SettingsManager
from utils.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from utils.csv_exporter import CSVExporter
from ui.theme import ThemeManager


class SettingsPage(QWidget):
    settings_changed = Signal()
    theme_changed_req = Signal(str)
    manual_update_requested = Signal()
    update_now_requested = Signal()
    update_later_requested = Signal()

    def __init__(self, tracker=None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._sm = SettingsManager()
        self._tracker = tracker
        self._protection_manager = protection_manager
        
        self._pending_changes = False
        self._theme_btns: dict[str, QPushButton] = {}
        self._selected_theme = self._sm.theme
        
        self._setup_ui()
        self._load_values()
        
        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(18)

        # Header Title (Clean, no permanent status banners or watermarks)
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("Settings")
        title.setObjectName("page_title")
        subtitle = QLabel("Make Digital Wellbeing yours — appearance, tracking, protections, and your data.")
        subtitle.setObjectName("page_subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        # Split layout for Sidebar + Stack
        split_layout = QHBoxLayout()
        split_layout.setSpacing(24)
        
        # Left Sidebar (QListWidget)
        self._sidebar = QListWidget()
        self._sidebar.setObjectName("settings_sidebar")
        self._sidebar.setFixedWidth(200)
        self._sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        split_layout.addWidget(self._sidebar)

        # Right Stacked Widget
        self._stack = QStackedWidget()
        split_layout.addWidget(self._stack, 1)
        
        layout.addLayout(split_layout, 1)
        
        # Build Pages
        self._build_pages()
        
        # Bottom Save button row (Clean, no watermark)
        save_row = QHBoxLayout()
        save_row.addStretch()
        
        self._save_btn = QPushButton("Save Preferences")
        self._save_btn.setObjectName("save_btn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        save_row.addWidget(self._save_btn)
        
        layout.addLayout(save_row)

    def _build_pages(self):
        categories = []

        # 1. General (System & Startup)
        gen_page = QWidget()
        gen_layout = QVBoxLayout(gen_page)
        gen_layout.setContentsMargins(0, 0, 0, 0)
        gen_layout.setSpacing(14)
        
        gen_layout.addWidget(self._create_section_title("System & startup"))
        
        self._autostart_check, row1 = self._create_toggle_row(
            "Launch on Windows Login",
            "Automatically start tracking when Windows boots up"
        )
        gen_layout.addWidget(row1)
        
        self._minimize_tray_check, row2 = self._create_toggle_row(
            "Minimize to System Tray",
            "Keep background tracking active in notification area when closed"
        )
        gen_layout.addWidget(row2)

        # Personalization
        gen_layout.addSpacing(6)
        gen_layout.addWidget(self._create_section_title("Personalization"))
        self._display_name_edit, row_name = self._create_text_input_row(
            "Display Name",
            "Your preferred name for personalized greetings on the Home screen (stored locally only)",
            placeholder="Enter your name"
        )
        gen_layout.addWidget(row_name)

        gen_layout.addStretch()
        categories.append(("General", "Startup and window behavior"))
        self._stack.addWidget(self._wrap_scroll(gen_page))

        # 2. Appearance & Theme (Dedicated prominent section)
        app_page = QWidget()
        app_layout = QVBoxLayout(app_page)
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(14)
        
        app_layout.addWidget(self._create_section_title("Appearance"))
        
        theme_card = QFrame()
        theme_card.setObjectName("settings_card")
        tc_layout = QVBoxLayout(theme_card)
        tc_layout.setContentsMargins(20, 18, 20, 18)
        tc_layout.setSpacing(12)
        
        tc_header = QVBoxLayout()
        tc_header.setSpacing(3)
        lbl_t_title = QLabel("Choose Visual Mode")
        lbl_t_title.setObjectName("setting_label")
        lbl_t_desc = QLabel("Choose how Digital Wellbeing looks across every page, dialog, and control.")
        lbl_t_desc.setObjectName("setting_desc")
        lbl_t_desc.setWordWrap(True)
        tc_header.addWidget(lbl_t_title)
        tc_header.addWidget(lbl_t_desc)
        tc_layout.addLayout(tc_header)
        
        # Segmented Theme Buttons
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(10)
        
        options = [
            ("System", "system", "Follow Windows theme"),
            ("Dark", "dark", "Aurora dark mode"),
            ("Light", "light", "Aurora light mode"),
        ]
        
        for text, val, sub in options:
            btn = QPushButton(text)
            btn.setObjectName("theme_choice_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _, v=val: self._on_theme_selected(v))
            self._theme_btns[val] = btn
            theme_btn_layout.addWidget(btn)
            
        tc_layout.addLayout(theme_btn_layout)
        app_layout.addWidget(theme_card)

        # Sound Feedback (haptics-lite)
        self._sound_check, sound_row = self._create_toggle_row(
            "Interaction Sounds",
            "Play subtle system sounds on toggles, alerts, and completed sessions (haptic-style feedback)"
        )
        self._sound_check.setChecked(self._sm.get_bool("sound_feedback", True))
        self._sound_check.toggled.connect(self._on_sound_feedback_changed)
        app_layout.addWidget(sound_row)

        app_layout.addStretch()
        categories.append(("Appearance", "Theme and visual mode"))
        self._stack.addWidget(self._wrap_scroll(app_page))

        # 3. Tracking & Limits
        track_page = QWidget()
        track_layout = QVBoxLayout(track_page)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.setSpacing(14)
        
        track_layout.addWidget(self._create_section_title("Tracking"))
        
        idle_row, self._idle_spin = self._create_spin_row(
            "Inactivity Idle Threshold",
            "Minutes of zero input before marking computer status as idle",
            1, 60, " min"
        )
        track_layout.addWidget(idle_row)
        
        self._debug_tracking_check, row3 = self._create_toggle_row(
            "Debug Tracking Log",
            "Log structured process transitions to disk for diagnostics"
        )
        track_layout.addWidget(row3)
        
        track_layout.addSpacing(6)
        track_layout.addWidget(self._create_section_title("Notifications & limits"))
        
        self._notif_check, row4 = self._create_toggle_row(
            "System Notifications",
            "Deliver Windows toast notifications for focus & limit milestones"
        )
        track_layout.addWidget(row4)
        
        limit_row, self._limit_spin = self._create_spin_row(
            "Daily Screen Time Alert",
            "Notify when total daily active screen time crosses this limit",
            30, 1440, " min", step=30
        )
        track_layout.addWidget(limit_row)
        
        track_layout.addStretch()
        categories.append(("Tracking", "Idle detection and daily limits"))
        self._stack.addWidget(self._wrap_scroll(track_page))

        # 4. SleepGuard
        sg_page = QWidget()
        sg_layout = QVBoxLayout(sg_page)
        sg_layout.setContentsMargins(0, 0, 0, 0)
        sg_layout.setSpacing(14)
        
        sg_layout.addWidget(self._create_section_title("SleepGuard"))
        
        self._sg_enable_check, r1 = self._create_toggle_row(
            "Enable SleepGuard",
            "Monitor extended inactivity and safely trigger bedtime power actions"
        )
        sg_layout.addWidget(r1)
        
        sg_a_row, self._sg_action_combo = self._create_combo_row(
            "Inactivity Action",
            "Power action to execute when timeout is reached",
            [("Lock Computer", "lock"), ("Sleep", "sleep"), ("Hibernate", "hibernate"), ("Shut Down", "shutdown")]
        )
        sg_layout.addWidget(sg_a_row)
        
        sg_t_row, self._sg_timeout_spin = self._create_spin_row(
            "Idle Timeout",
            "Minutes of continuous inactivity required",
            5, 120, " min", step=5
        )
        sg_layout.addWidget(sg_t_row)
        
        sg_c_row, self._sg_countdown_spin = self._create_spin_row(
            "Warning Countdown Duration",
            "Grace seconds to display the cancelable warning dialog",
            10, 300, " sec", step=10
        )
        sg_layout.addWidget(sg_c_row)
        
        sg_layout.addSpacing(6)
        sg_layout.addWidget(self._create_section_title("Media awareness"))
        
        sg_m_row, self._sg_mode_combo = self._create_combo_row(
            "Media Playback Rule",
            "Inactivity handling while watching video or audio",
            [
                ("Smart - Trigger after extended media threshold", "smart"),
                ("Always Allow - Never trigger during media playback", "media"),
                ("Strict - Ignore media playback", "strict")
            ]
        )
        self._sg_mode_combo.currentIndexChanged.connect(self._on_sg_mode_changed)
        sg_layout.addWidget(sg_m_row)
        
        sg_mt_row, self._sg_media_timeout_combo = self._create_combo_row(
            "Extended Media Idle Timeout",
            "Threshold when media playback is detected",
            [("Never", -1), ("5 min", 5), ("10 min", 10), ("15 min", 15), ("30 min", 30), ("60 min", 60)]
        )
        sg_layout.addWidget(sg_mt_row)
        
        sg_layout.addSpacing(6)
        sg_layout.addWidget(self._create_section_title("Developer"))
        sg_test_row, self._sg_test_timeout_combo = self._create_combo_row(
            "Rapid Test Mode",
            "Override timeout for testing countdown",
            [("Off (Production Standard)", 0), ("10 seconds", 10), ("20 seconds", 20), ("30 seconds", 30), ("1 minute", 60)]
        )
        sg_layout.addWidget(sg_test_row)
        
        sg_layout.addStretch()
        categories.append(("SleepGuard", "Bedtime inactivity rules"))
        self._stack.addWidget(self._wrap_scroll(sg_page))

        # 5. Security & Protection
        prot_page = QWidget()
        prot_layout = QVBoxLayout(prot_page)
        prot_layout.setContentsMargins(0, 0, 0, 0)
        prot_layout.setSpacing(14)

        if self._protection_manager:
            from ui.widgets.protection_section import ProtectionSection
            prot_card = QFrame()
            prot_card.setObjectName("settings_card")
            card_l = QVBoxLayout(prot_card)
            card_l.setContentsMargins(20, 20, 20, 20)
            card_l.addWidget(ProtectionSection(self._protection_manager))
            prot_layout.addWidget(prot_card)

        try:
            from ui.widgets.safebrowse_section import SafeBrowseSection
            prot_layout.addWidget(SafeBrowseSection())
        except Exception as exc:
            logger.warning(f"SafeBrowse section unavailable: {exc}")

        prot_layout.addStretch()
        categories.append(("Security", "App Locker, SafeBrowse, Windows Hello"))
        self._stack.addWidget(self._wrap_scroll(prot_page))
        
        # 6. Data Management
        data_page = QWidget()
        data_layout = QVBoxLayout(data_page)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(14)
        
        data_layout.addWidget(self._create_section_title("Storage & retention"))
        
        ret_row, self._retention_combo = self._create_combo_row(
            "History Retention",
            "Automatically prune older raw activity sessions",
            [("30 Days", 30), ("90 Days", 90), ("1 Year", 365), ("Unlimited (Keep Forever)", -1)]
        )
        data_layout.addWidget(ret_row)
        
        data_layout.addSpacing(6)
        data_layout.addWidget(self._create_section_title("Export & backup"))
        
        export_row, self._export_range_combo = self._create_combo_row(
            "Export Sessions (CSV)",
            "Generate offline CSV report",
            [("Today", 0), ("Past 7 Days", 7), ("Past 30 Days", 30), ("This Month", 99)]
        )
        btn_exp = QPushButton("Export CSV")
        btn_exp.setObjectName("secondary_action_btn")
        btn_exp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exp.clicked.connect(self._on_export_csv)
        export_row.layout().addWidget(btn_exp)
        data_layout.addWidget(export_row)
        
        db_row = QFrame()
        db_row.setObjectName("settings_card")
        db_l = QHBoxLayout(db_row)
        db_c = QVBoxLayout()
        db_lbl = QLabel("Backup & Restore Database")
        db_lbl.setObjectName("setting_label")
        db_desc = QLabel("Save an exact snapshot of your SQLite tracking database or restore an existing backup.")
        db_desc.setObjectName("setting_desc")
        db_desc.setWordWrap(True)
        db_c.addWidget(db_lbl)
        db_c.addWidget(db_desc)
        db_l.addLayout(db_c, 1)

        btn_bak = QPushButton("Backup DB")
        btn_bak.setObjectName("secondary_action_btn")
        btn_bak.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bak.clicked.connect(self._on_backup_db)
        
        btn_res = QPushButton("Restore DB")
        btn_res.setObjectName("secondary_action_btn")
        btn_res.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_res.clicked.connect(self._on_restore_db)
        
        db_l.addWidget(btn_bak)
        db_l.addWidget(btn_res)
        data_layout.addWidget(db_row)
        
        clr_row = QFrame()
        clr_row.setObjectName("settings_card")
        clr_l = QHBoxLayout(clr_row)
        clr_c = QVBoxLayout()
        clr_lbl = QLabel("Clear Tracking History")
        clr_lbl.setObjectName("setting_label")
        clr_desc = QLabel("Permanently purge all recorded sessions from your local database. Cannot be undone.")
        clr_desc.setObjectName("setting_desc")
        clr_desc.setWordWrap(True)
        clr_c.addWidget(clr_lbl)
        clr_c.addWidget(clr_desc)
        clr_l.addLayout(clr_c, 1)

        self._clear_btn = QPushButton("Clear History")
        self._clear_btn.setObjectName("danger_btn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_history)
        clr_l.addWidget(self._clear_btn)
        data_layout.addWidget(clr_row)
        
        self._data_status_lbl = QLabel("")
        self._data_status_lbl.setObjectName("data_status")
        data_layout.addWidget(self._data_status_lbl)
        
        data_layout.addStretch()
        categories.append(("Data & Storage", "Export, backup, and local storage limits"))
        self._stack.addWidget(self._wrap_scroll(data_page))
        
        # 7. About & Privacy (Dedicated Section for Local-First & Zero Telemetry)
        upd_page = QWidget()
        upd_layout = QVBoxLayout(upd_page)
        upd_layout.setContentsMargins(0, 0, 0, 0)
        upd_layout.setSpacing(14)
        
        upd_layout.addWidget(self._create_section_title("About & updates"))
        
        from core.constants import APP_VERSION, APP_NAME
        upd_card = QFrame()
        upd_card.setObjectName("settings_card")
        upd_card_l = QVBoxLayout(upd_card)
        upd_card_l.setContentsMargins(20, 18, 20, 18)
        upd_card_l.setSpacing(14)

        # Version & Status Row
        ver_status_layout = QHBoxLayout()
        ver_status_layout.setSpacing(24)

        # Current Version Column
        cur_ver_col = QVBoxLayout()
        cur_ver_col.setSpacing(3)
        cur_ver_title = QLabel("Current Version")
        cur_ver_title.setObjectName("setting_desc")
        self._upd_current_version_lbl = QLabel(APP_VERSION)
        self._upd_current_version_lbl.setObjectName("setting_label")
        self._upd_current_version_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        cur_ver_col.addWidget(cur_ver_title)
        cur_ver_col.addWidget(self._upd_current_version_lbl)
        ver_status_layout.addLayout(cur_ver_col)

        ver_status_layout.addSpacing(16)

        # Update Status Column
        status_col = QVBoxLayout()
        status_col.setSpacing(3)
        status_title = QLabel("Update Status")
        status_title.setObjectName("setting_desc")
        self._upd_status_lbl = QLabel("You're up to date")
        self._upd_status_lbl.setObjectName("update_status_label")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #0A84FF;")
        status_col.addWidget(status_title)
        status_col.addWidget(self._upd_status_lbl)
        ver_status_layout.addLayout(status_col, 1)

        upd_card_l.addLayout(ver_status_layout)

        # Progress / Installing state row (shown during download / install)
        self._upd_progress_col = QVBoxLayout()
        self._upd_progress_col.setSpacing(6)
        self._upd_progress_lbl = QLabel("")
        self._upd_progress_lbl.setObjectName("setting_desc")
        self._upd_progress_lbl.setVisible(False)
        self._upd_progress_bar = QProgressBar()
        self._upd_progress_bar.setRange(0, 100)
        self._upd_progress_bar.setValue(0)
        self._upd_progress_bar.setFixedHeight(8)
        self._upd_progress_bar.setTextVisible(False)
        self._upd_progress_bar.setVisible(False)
        self._upd_progress_col.addWidget(self._upd_progress_lbl)
        self._upd_progress_col.addWidget(self._upd_progress_bar)
        upd_card_l.addLayout(self._upd_progress_col)

        # Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._check_updates_btn = QPushButton("Check for Updates")
        self._check_updates_btn.setObjectName("secondary_action_btn")
        self._check_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_updates_btn.clicked.connect(self._on_check_updates_clicked)
        btn_row.addWidget(self._check_updates_btn)

        self._update_now_btn = QPushButton("Update Now")
        self._update_now_btn.setObjectName("save_btn")
        self._update_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_now_btn.setVisible(False)
        self._update_now_btn.clicked.connect(self._on_update_now_clicked)
        btn_row.addWidget(self._update_now_btn)

        self._update_later_btn = QPushButton("Later")
        self._update_later_btn.setObjectName("secondary_action_btn")
        self._update_later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_later_btn.setVisible(False)
        self._update_later_btn.clicked.connect(self._on_update_later_clicked)
        btn_row.addWidget(self._update_later_btn)

        btn_row.addStretch()
        upd_card_l.addLayout(btn_row)

        upd_layout.addWidget(upd_card)

        upd_layout.addSpacing(6)
        upd_layout.addWidget(self._create_section_title("Privacy"))
        
        privacy_card = QFrame()
        privacy_card.setObjectName("settings_card")
        priv_l = QVBoxLayout(privacy_card)
        priv_l.setContentsMargins(20, 18, 20, 18)
        priv_l.setSpacing(10)
        
        priv_title = QLabel("Local-first storage, zero telemetry")
        priv_title.setObjectName("privacy_guarantee_title")
        priv_desc = QLabel(
            "Your data never leaves this PC.\n\n"
            "Every session, metric, and focus record lives in a local SQLite database on your device. "
            "There is no account, no cloud sync, no behavioral profiling, and no third-party SDKs.\n\n"
            "The only outbound requests Digital Wellbeing can ever make are ones you control: "
            "checking for updates, and — only if you explicitly turn it on in Settings — an anonymous "
            "usage ping with no personal data. SafeBrowse blocklists are downloaded from public "
            "open-source lists and carry no information about you."
        )
        priv_desc.setWordWrap(True)
        priv_desc.setObjectName("setting_desc")
        priv_l.addWidget(priv_title)
        priv_l.addWidget(priv_desc)
        upd_layout.addWidget(privacy_card)

        # Opt-in anonymous stats (off by default; honors the privacy promise)
        self._share_stats_check, r_stats = self._create_toggle_row(
            "Share Anonymous Usage Statistics",
            "If you turn this on, Digital Wellbeing sends a single anonymous ping (a random id and the app version) once per launch. It is never used for profiling and stays off unless you opt in."
        )
        self._share_stats_check.setChecked(self._sm.get_bool("share_anonymous_stats", False))
        self._share_stats_check.toggled.connect(
            lambda v: self._sm.set_bool("share_anonymous_stats", v))
        upd_layout.addWidget(r_stats)

        upd_layout.addSpacing(6)
        upd_layout.addWidget(self._create_section_title("Update checks"))
        
        self._auto_update_check, r_upd1 = self._create_toggle_row("Automatic Update Checks", "Check for new versions once per day")
        upd_layout.addWidget(r_upd1)
        
        self._notify_update_check, r_upd2 = self._create_toggle_row("Update Notifications", "Display notification when a new version is available")
        upd_layout.addWidget(r_upd2)
        
        upd_layout.addStretch()
        categories.append(("About / Updates", "Version info, updates, and privacy architecture"))
        self._stack.addWidget(self._wrap_scroll(upd_page))

        # Populate sidebar
        for title, desc in categories:
            item = QListWidgetItem(title)
            item.setToolTip(desc)
            self._sidebar.addItem(item)
            
        self._sidebar.setCurrentRow(0)

    def _wrap_scroll(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(widget)
        scroll.setStyleSheet("QScrollArea { background: transparent; } QWidget { background: transparent; }")
        return scroll

    def _create_section_title(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setObjectName("section_header")
        return lbl

    def _create_toggle_row(self, title: str, description: str):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 14, 18, 14)
        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        from ui.widgets.fluent import ToggleSwitch
        check = ToggleSwitch()
        layout.addWidget(check)
        return check, row

    def _create_combo_row(self, title: str, description: str, items: list):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 14, 18, 14)
        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        combo = QComboBox()
        for text, data in items:
            combo.addItem(text, data)
        combo.setMinimumWidth(180)
        combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(combo)
        return row, combo

    def _create_spin_row(self, title: str, description: str, min_val: int, max_val: int, suffix: str, step: int = 1):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 14, 18, 14)
        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(120)
        spin.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(spin)
        return row, spin

    def _create_text_input_row(self, title: str, description: str, placeholder: str = ""):
        row = QFrame()
        row.setObjectName("settings_card")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 14, 18, 14)
        col = QVBoxLayout()
        col.setSpacing(3)
        lbl = QLabel(title)
        lbl.setObjectName("setting_label")
        desc = QLabel(description)
        desc.setObjectName("setting_desc")
        desc.setWordWrap(True)
        col.addWidget(lbl)
        col.addWidget(desc)
        layout.addLayout(col, 1)
        edit = QLineEdit()
        edit.setObjectName("settings_line_edit")
        edit.setPlaceholderText(placeholder)
        edit.setMinimumWidth(200)
        edit.setMaxLength(50)
        edit.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addWidget(edit)
        return edit, row

    def _on_sidebar_changed(self, index: int):
        self._stack.setCurrentIndex(index)

    def _on_theme_selected(self, theme_val: str) -> None:
        self._selected_theme = theme_val
        self._update_theme_btn_styles()
        self._sm.theme = theme_val
        self.theme_changed_req.emit(theme_val)

    def _on_sound_feedback_changed(self, checked: bool) -> None:
        self._sm.set("sound_feedback", "true" if checked else "false")
        if checked:
            try:
                from ui import feedback
                feedback.play(feedback.Sound.SUCCESS)
            except Exception:
                pass
        self.settings_changed.emit()

    def _update_theme_btn_styles(self) -> None:
        tm = ThemeManager.instance()
        is_dark = tm.is_dark
        active_theme = self._selected_theme or self._sm.theme
        
        for val, btn in self._theme_btns.items():
            if val == active_theme:
                btn.setStyleSheet(f"""
                    QPushButton#theme_choice_btn {{
                        background: {tm.color('accent_emerald_bg')};
                        border: 2px solid {tm.color('accent')};
                        border-radius: 10px;
                        color: {tm.color('accent')};
                        font-size: 13px;
                        font-weight: 700;
                        padding: 10px 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton#theme_choice_btn {{
                        background: {tm.color('surface_secondary')};
                        border: 1px solid {tm.color('border')};
                        border-radius: 10px;
                        color: {tm.color('text_sub')};
                        font-size: 13px;
                        font-weight: 600;
                        padding: 10px 14px;
                    }}
                    QPushButton#theme_choice_btn:hover {{
                        background: {tm.color('surface_hover')};
                        border-color: {tm.color('border_hover')};
                        color: {tm.color('text_main')};
                    }}
                """)

    def _apply_theme(self, is_dark: bool) -> None:
        tm = ThemeManager.instance()
        
        self.setStyleSheet(f"""
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
                line-height: 1.4;
            }}
            QLabel#section_header {{
                font-size: 12px;
                font-weight: 600;
                color: {tm.color('text_muted')};
                letter-spacing: -0.1px;
                margin-top: 6px;
                margin-bottom: 2px;
            }}
            QLabel#setting_label {{
                color: {tm.color('text_main')};
                font-size: 14px;
                font-weight: 700;
            }}
            QLabel#setting_desc {{
                color: {tm.color('text_sub')};
                font-size: 12px;
                line-height: 1.4;
            }}
            QLabel#privacy_guarantee_title {{
                color: {tm.color('accent')};
                font-size: 14px;
                font-weight: 700;
            }}
            
            QFrame#settings_card {{ 
                background-color: {tm.color('card_bg')}; 
                border-radius: 12px; 
                border: 1px solid {tm.color('border')}; 
            }}
            
            QListWidget#settings_sidebar {{
                background: transparent;
                border: none;
                padding: 0px;
                outline: none;
            }}
            QListWidget#settings_sidebar::item {{
                background: transparent;
                color: {tm.color('text_sub')};
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 4px;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid transparent;
            }}
            QListWidget#settings_sidebar::item:hover {{
                background: {tm.color('surface_hover')};
                color: {tm.color('text_main')};
            }}
            QListWidget#settings_sidebar::item:selected {{
                background: {tm.color('accent_emerald_bg')};
                color: {tm.color('accent')};
                font-weight: 700;
                border: 1px solid {tm.color('accent_emerald_bg')};
            }}
            
            QComboBox, QSpinBox, QLineEdit#settings_line_edit {{
                background-color: {tm.color('input_bg')};
                border: 1px solid {tm.color('input_border')};
                border-radius: 8px;
                padding: 7px 12px;
                color: {tm.color('text_main')};
                font-size: 13px;
                font-weight: 500;
            }}
            QComboBox:hover, QSpinBox:hover, QLineEdit#settings_line_edit:hover {{
                border: 1px solid {tm.color('accent')};
                background-color: {tm.color('surface_elevated')};
            }}
            QLineEdit#settings_line_edit:focus {{
                border: 1.5px solid {tm.color('accent')};
                background-color: {tm.color('surface_elevated')};
            }}
            QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {tm.color('surface_elevated')};
                border: 1px solid {tm.color('border_strong')};
                selection-background-color: {tm.color('accent_emerald_bg')};
                selection-color: {tm.color('accent')};
                border-radius: 8px;
                padding: 4px;
                outline: none;
                color: {tm.color('text_main')};
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 6px;
                color: {tm.color('text_main')};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {tm.color('surface_hover')};
                color: {tm.color('text_main')};
            }}
            
            QPushButton#save_btn {{
                background: {tm.color('primary_btn_gradient')};
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 26px;
                border: 1px solid {tm.color('accent')};
                border-radius: 8px;
            }}
            QPushButton#save_btn:hover {{
                background: {tm.color('primary_btn_hover')};
                border-color: {tm.color('accent_hover')};
            }}
            QPushButton#secondary_action_btn {{
                background-color: {tm.color('surface_secondary')};
                color: {tm.color('text_main')};
                border: 1px solid {tm.color('border')};
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#secondary_action_btn:hover {{
                background-color: {tm.color('surface_hover')};
                border-color: {tm.color('border_hover')};
            }}
            QPushButton#danger_btn {{
                background-color: {tm.color('danger_bg')};
                color: {tm.color('danger_text')};
                border: 1px solid {tm.color('danger_border')};
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton#danger_btn:hover {{
                background-color: rgba(255, 69, 58, 0.25);
            }}
        """)
        self._update_theme_btn_styles()

    def _on_sg_mode_changed(self) -> None:
        is_smart = self._sg_mode_combo.currentData() == "smart"
        self._sg_media_timeout_combo.setEnabled(is_smart)

    def _load_values(self) -> None:
        self._selected_theme = self._sm.theme
        self._update_theme_btn_styles()
            
        self._idle_spin.setValue(self._sm.get_int("idle_threshold_s", 300) // 60)
        self._autostart_check.setChecked(is_autostart_enabled())
        self._minimize_tray_check.setChecked(self._sm.get_bool("minimize_to_tray", False))
        self._display_name_edit.setText(self._sm.display_name)
        self._debug_tracking_check.setChecked(self._sm.debug_tracking)
        self._notif_check.setChecked(self._sm.get_bool("notifications_enabled", True))
        self._limit_spin.setValue(self._sm.get_int("daily_limit_minutes", 480))

        self._sg_enable_check.setChecked(self._sm.sleepguard_enabled)
        curr_action = self._sm.sleepguard_action
        idx_act = self._sg_action_combo.findData(curr_action)
        if idx_act >= 0:
            self._sg_action_combo.setCurrentIndex(idx_act)
        
        curr_mode = self._sm.shutdown_mode
        idx = self._sg_mode_combo.findData(curr_mode)
        if idx >= 0:
            self._sg_mode_combo.setCurrentIndex(idx)
            
        self._sg_timeout_spin.setValue(self._sm.idle_timeout_minutes)
        self._sg_countdown_spin.setValue(self._sm.countdown_seconds)
        
        test_timeout = self._sm.testing_idle_timeout_s
        idx_test = self._sg_test_timeout_combo.findData(test_timeout)
        if idx_test >= 0:
            self._sg_test_timeout_combo.setCurrentIndex(idx_test)
        
        media_timeout = self._sm.media_idle_timeout_minutes
        idx2 = self._sg_media_timeout_combo.findData(media_timeout)
        if idx2 >= 0:
            self._sg_media_timeout_combo.setCurrentIndex(idx2)
            
        retention = self._sm.get_int("history_retention_days", 30)
        idx3 = self._retention_combo.findData(retention)
        if idx3 >= 0:
            self._retention_combo.setCurrentIndex(idx3)

        self._auto_update_check.setChecked(self._sm.auto_update_enabled)
        self._notify_update_check.setChecked(self._sm.notify_updates)

        self._on_sg_mode_changed()

    def _on_export_csv(self) -> None:
        days = self._export_range_combo.currentData()
        end = date.today()
        if days == 0:
            start = end
        elif days == 99:
            start = end.replace(day=1)
        else:
            start = end - timedelta(days=days - 1)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report CSV", str(Path.home() / "Documents" / f"digital_wellbeing_report_{start}_{end}.csv"), "CSV Files (*.csv)",
        )

        if file_path:
            try:
                exporter = CSVExporter()
                dest = exporter.export_sessions(start, end, Path(file_path))
                self._data_status_lbl.setText(f"✓ Report exported to: {dest.name}")
                self._data_status_lbl.setStyleSheet("color: #0A84FF; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Export failed: {exc}")
                self._data_status_lbl.setStyleSheet("color: #FF453A; font-weight: 600; font-size: 12px;")

    def _on_backup_db(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", str(Path.home() / "Documents" / f"digital_wellbeing_backup_{date.today()}.db"), "Database Files (*.db)",
        )
        if file_path:
            try:
                repo = Repository()
                dest = repo.backup_database(Path(file_path))
                self._data_status_lbl.setText(f"✓ Database backed up to: {dest.name}")
                self._data_status_lbl.setStyleSheet("color: #0A84FF; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Backup failed: {exc}")
                self._data_status_lbl.setStyleSheet("color: #FF453A; font-weight: 600; font-size: 12px;")

    def _on_restore_db(self) -> None:
        reply = QMessageBox.question(
            self, "Confirm Database Restore", "Restoring database will overwrite your current tracking data. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Database Backup", str(Path.home() / "Documents"), "Database Files (*.db)",
            )
            if file_path:
                try:
                    repo = Repository()
                    repo.restore_database(Path(file_path))
                    self._data_status_lbl.setText(f"✓ Database restored successfully from: {Path(file_path).name}")
                    self._data_status_lbl.setStyleSheet("color: #0A84FF; font-weight: 600; font-size: 12px;")
                except Exception as exc:
                    self._data_status_lbl.setText(f"✗ Restore failed: {exc}")
                    self._data_status_lbl.setStyleSheet("color: #FF453A; font-weight: 600; font-size: 12px;")

    def _on_clear_history(self) -> None:
        reply = QMessageBox.warning(
            self, "Confirm Clear History", "Are you sure you want to permanently delete all tracking history? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                repo = Repository()
                count = repo.clear_all_sessions()
                self._data_status_lbl.setText(f"✓ Cleared {count} sessions from history.")
                self._data_status_lbl.setStyleSheet("color: #0A84FF; font-weight: 600; font-size: 12px;")
            except Exception as exc:
                self._data_status_lbl.setText(f"✗ Clear history failed: {exc}")
                self._data_status_lbl.setStyleSheet("color: #FF453A; font-weight: 600; font-size: 12px;")

    def _save(self) -> None:
        if self._selected_theme:
            self._sm.theme = self._selected_theme
        self._sm.set_int("idle_threshold_s", self._idle_spin.value() * 60)
        self._sm.set_bool("notifications_enabled", self._notif_check.isChecked())
        self._sm.set_bool("minimize_to_tray", self._minimize_tray_check.isChecked())
        self._sm.display_name = self._display_name_edit.text().strip()
        self._sm.debug_tracking = self._debug_tracking_check.isChecked()
        self._sm.set_int("daily_limit_minutes", self._limit_spin.value())

        self._sm.sleepguard_enabled = self._sg_enable_check.isChecked()
        act_val = self._sg_action_combo.currentData()
        if act_val:
            self._sm.sleepguard_action = act_val
        mode_val = self._sg_mode_combo.currentData()
        if mode_val:
            self._sm.shutdown_mode = mode_val
        self._sm.idle_timeout_minutes = self._sg_timeout_spin.value()
        self._sm.countdown_seconds = self._sg_countdown_spin.value()
        
        test_val = self._sg_test_timeout_combo.currentData()
        if test_val is not None:
            self._sm.testing_idle_timeout_s = test_val
        
        media_timeout_val = self._sg_media_timeout_combo.currentData()
        if media_timeout_val is not None:
            self._sm.media_idle_timeout_minutes = media_timeout_val
            
        self._sm.auto_update_enabled = self._auto_update_check.isChecked()
        self._sm.notify_updates = self._notify_update_check.isChecked()

        ret_val = self._retention_combo.currentData()
        if ret_val is not None:
            self._sm.set_int("history_retention_days", ret_val)
            if ret_val > 0:
                from analytics.engine import AnalyticsEngine
                try:
                    AnalyticsEngine().run_cleanup(ret_val)
                except Exception as e:
                    print(f"Cleanup error: {e}")

        if self._autostart_check.isChecked():
            try:
                enable_autostart()
            except Exception as exc:
                QMessageBox.warning(self, "Autostart Failed", str(exc))
        else:
            try:
                disable_autostart()
            except Exception as exc:
                QMessageBox.warning(self, "Autostart Failed", str(exc))

        if self._tracker:
            self._tracker.reload_settings()

        self.settings_changed.emit()
        QMessageBox.information(self, "Settings Saved", "Preferences have been successfully saved.")

    def on_data_changed(self) -> None:
        if hasattr(self, "_display_name_edit"):
            self._display_name_edit.setText(self._sm.display_name)

    # ─── In-App Update Handlers & State Updaters ───────────────────────────

    def _on_check_updates_clicked(self) -> None:
        self._upd_status_lbl.setText("Checking for updates...")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #A1A1A6;")
        self._check_updates_btn.setEnabled(False)
        self.manual_update_requested.emit()

    def _on_update_now_clicked(self) -> None:
        self._update_now_btn.setEnabled(False)
        self._update_later_btn.setEnabled(False)
        self._check_updates_btn.setEnabled(False)
        self.update_now_requested.emit()

    def _on_update_later_clicked(self) -> None:
        self._update_now_btn.setVisible(False)
        self._update_later_btn.setVisible(False)
        self._upd_status_lbl.setText("Update postponed for this session")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #A1A1A6;")
        self.update_later_requested.emit()

    def set_update_status_up_to_date(self) -> None:
        self._upd_status_lbl.setText("You're up to date")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #0A84FF;")
        self._check_updates_btn.setEnabled(True)
        self._update_now_btn.setVisible(False)
        self._update_later_btn.setVisible(False)
        self._upd_progress_lbl.setVisible(False)
        self._upd_progress_bar.setVisible(False)

    def set_update_available(self, version: str) -> None:
        clean_ver = str(version).lstrip("vV")
        self._upd_status_lbl.setText(f"Digital Wellbeing {clean_ver} is available")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #0A84FF;")
        self._check_updates_btn.setEnabled(True)
        self._update_now_btn.setVisible(True)
        self._update_now_btn.setEnabled(True)
        self._update_later_btn.setVisible(True)
        self._update_later_btn.setEnabled(True)
        self._upd_progress_lbl.setVisible(False)
        self._upd_progress_bar.setVisible(False)

    def set_update_error(self, message: str = "Couldn't check for updates right now.") -> None:
        self._upd_status_lbl.setText("Couldn't check for updates right now.")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #A1A1A6;")
        self._check_updates_btn.setEnabled(True)
        self._update_now_btn.setVisible(False)
        self._update_later_btn.setVisible(False)
        self._upd_progress_lbl.setVisible(False)
        self._upd_progress_bar.setVisible(False)

    def set_download_progress(self, percent: int, version: str = "") -> None:
        clean_ver = str(version).lstrip("vV") if version else ""
        ver_str = f"Digital Wellbeing {clean_ver}" if clean_ver else "update"
        self._upd_progress_lbl.setVisible(True)
        self._upd_progress_bar.setVisible(True)
        self._upd_progress_bar.setValue(percent)
        self._upd_progress_lbl.setText(f"Downloading {ver_str} — {percent}%")
        self._upd_status_lbl.setText(f"Downloading {ver_str}...")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #0A84FF;")

    def set_installing_status(self, version: str = "") -> None:
        clean_ver = str(version).lstrip("vV") if version else ""
        ver_str = f"Digital Wellbeing {clean_ver}" if clean_ver else "update"
        self._upd_progress_lbl.setVisible(True)
        self._upd_progress_lbl.setText(f"Installing {ver_str}...")
        self._upd_progress_bar.setVisible(True)
        self._upd_progress_bar.setValue(100)
        self._upd_status_lbl.setText(f"Installing {ver_str}...")
        self._upd_status_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #0A84FF;")
        self._check_updates_btn.setEnabled(False)
        self._update_now_btn.setEnabled(False)
        self._update_later_btn.setEnabled(False)

