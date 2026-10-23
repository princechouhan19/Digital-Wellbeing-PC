"""
main_window.py — V2 Main Application Shell for Digital Wellbeing.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QMainWindow, QSystemTrayIcon
)

from core.constants import APP_NAME, APP_VERSION
from tracker.manager import TrackingManager
from tracker.sleepguard import SleepGuardController
from ui.pages.activity import ActivityPage
from ui.pages.dashboard import DashboardPage
from ui.pages.websites import WebsitesPage

from ui.widgets.limit_dialog import LimitReachedDialog, PinOverrideDialog
from ui.pages.debug import DebugPage
from ui.pages.settings import SettingsPage
from ui.pages.wellbeing import WellbeingPage
from ui.pages.app_locker import AppLockerPage
from ui.pages.insights import InsightsPage
from ui.pages.history import HistoryPage
from ui.pages.sleepguard_page import SleepGuardPage
from ui.widgets.animated_stacked_widget import AnimatedStackedWidget
from ui.widgets.countdown_dialog import ShutdownCountdownDialog


class DataUpdateThread(QThread):
    data_changed = Signal()

    def __init__(self, tracker: TrackingManager, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker

    def notify(self) -> None:
        self.data_changed.emit()



class MainWindow(QMainWindow):
    data_changed_signal = Signal()
    quit_requested = Signal()
    focus_completed = Signal()
    manual_update_requested = Signal()
    update_now_requested = Signal()
    update_later_requested = Signal()

    def __init__(self, tracker: TrackingManager, sleepguard: Optional[SleepGuardController] = None, protection_manager=None, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._protection_manager = protection_manager
        self._owns_sleepguard = sleepguard is None
        self._sleepguard = sleepguard or SleepGuardController(self)
        if self._owns_sleepguard:
            self._sleepguard.start()
        self._sleepguard.shutdown_warning_triggered.connect(self._show_shutdown_warning_dialog)
        
        if self._protection_manager:
            self._protection_manager.notifications.show_limit_dialog.connect(self._show_limit_dialog)
            self._protection_manager.notifications.show_website_limit_dialog.connect(self._show_website_limit_dialog)

        self.data_changed_signal.connect(self._refresh_current_page)
        self._active_nav_btn: Optional[QPushButton] = None
        self._navigation_history: list[int] = []
        self._active_limit_dialogs = set()
        self._setup_ui()
        self._connect_tracker()
        self._setup_shortcuts()
        from settings.manager import SettingsManager
        self._sm = SettingsManager()
        self._onboarding_active = False

        # Trigger initial Home page load without blocking UI layout
        QTimer.singleShot(0, self._refresh_current_page)
        QTimer.singleShot(350, self._check_first_run_onboarding)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "_sm") and not self._sm.onboarding_completed:
            QTimer.singleShot(350, self._check_first_run_onboarding)

    def _check_first_run_onboarding(self) -> None:
        """Launch the first-run onboarding wizard once, on the visible main window."""
        import os
        if os.environ.get("DW_TEST_MODE") == "1":
            return
        if not hasattr(self, "_sm"):
            from settings.manager import SettingsManager
            self._sm = SettingsManager()
        if self._sm.onboarding_completed:
            return
        if not self.isVisible():
            return
        if getattr(self, "_onboarding_active", False):
            return
        self._onboarding_active = True
        try:
            from ui.onboarding import OnboardingFlow
            self._onboarding_dlg = OnboardingFlow(parent=self)
            self._onboarding_dlg.flow_finished.connect(self._on_onboarding_finished)
            self._onboarding_dlg.finished.connect(lambda: setattr(self, "_onboarding_active", False))
            self._onboarding_dlg.show()
            self._onboarding_dlg.raise_()
            self._onboarding_dlg.activateWindow()
        except Exception:
            self._onboarding_active = False
            import logging
            logging.getLogger(__name__).exception("Onboarding failed to open")

    def _on_onboarding_finished(self) -> None:
        # Mark completion even if the dialog is closed mid-flow, so the wizard
        # never re-appears uninvited after the user has seen it once.
        if not self._sm.onboarding_completed:
            self._sm.onboarding_completed = True
        self.refresh_all_pages()

    def _setup_ui(self) -> None:
        from core.constants import APP_NAME, APP_VERSION
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        
        icon_candidates = [
            Path(__file__).resolve().parent.parent / "assets" / "icons" / "app_icon.ico",
            Path(__file__).resolve().parent.parent / "assets" / "icon.ico",
            Path(sys.executable).resolve().parent / "assets" / "icons" / "app_icon.ico",
            Path(sys.executable).resolve().parent / "_internal" / "assets" / "icons" / "app_icon.ico",
            Path("assets/icons/app_icon.ico").resolve(),
            Path("assets/icon.ico").resolve(),
        ]
        if getattr(sys, "_MEIPASS", None):
            icon_candidates.insert(0, Path(sys._MEIPASS) / "assets" / "icons" / "app_icon.ico")
        chosen_icon_path = None
        for icp in icon_candidates:
            if icp.is_file():
                ico = QIcon(str(icp))
                if not ico.isNull():
                    self.setWindowIcon(ico)
                    chosen_icon_path = str(icp)
                    break
        self.setMinimumSize(1024, 720)
        self.resize(1280, 800)

        central_widget = QWidget(self)
        central_widget.setObjectName("central_widget")
        self.setCentralWidget(central_widget)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        hwnd = int(self.winId())
        from ui.theme import ThemeManager, apply_mica
        apply_mica(hwnd, ThemeManager.instance().is_dark)
        ThemeManager.instance().theme_changed.connect(lambda is_dark: apply_mica(hwnd, is_dark))

        # Explicitly apply Win32 taskbar icons to HWND
        if chosen_icon_path and sys.platform == "win32":
            try:
                import ctypes
                WM_SETICON = 0x0080
                ICON_SMALL = 0
                ICON_BIG = 1
                IMAGE_ICON = 1
                LR_LOADFROMFILE = 0x00000010
                
                h_big = ctypes.windll.user32.LoadImageW(None, chosen_icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                h_small = ctypes.windll.user32.LoadImageW(None, chosen_icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                if h_big:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_big)
                if h_small:
                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_small)
            except Exception as e:
                logger.debug(f"Failed to set native Win32 window icon: {e}")

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left Sidebar Navigation Rail
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        self._stack = AnimatedStackedWidget()
        self._stack.setObjectName("content_area")
        self._stack.currentChanged.connect(self._refresh_current_page)

        self._dashboard_page = DashboardPage(on_global_refresh=self.refresh_all_pages, navigate_callback=self._navigate)
        
        from ui.pages.screen_time_details import ScreenTimeDetailsPage
        self._screen_time_details_page = ScreenTimeDetailsPage()
        
        from ui.pages.app_details import AppDetailsPage
        self._app_details_page = AppDetailsPage(protection_manager=self._protection_manager)
        
        self._dashboard_page.request_screen_time_details.connect(self._navigate_to_screen_time_details)
        self._dashboard_page.request_app_details.connect(self._navigate_to_app_details)
        self._dashboard_page.request_focus_session.connect(lambda: self._navigate(2))
        
        self._screen_time_details_page.request_app_details.connect(self._navigate_to_app_details)
        self._screen_time_details_page.back_requested.connect(self._navigate_back)
        
        self._app_details_page.back_requested.connect(self._navigate_back)
        
        self._activity_page = ActivityPage(protection_manager=self._protection_manager)
        self._activity_page.request_historical_details.connect(self._navigate_to_screen_time_details)
        self._wellbeing_page = WellbeingPage(sleepguard=self._sleepguard)
        self._wellbeing_page.focus_completed.connect(self.focus_completed.emit)
        from ui.pages.app_locker import AppLockerPage
        self._app_locker_page = AppLockerPage(protection_manager=self._protection_manager)
        from ui.pages.app_timer import AppTimerPage
        self._app_timer_page = AppTimerPage(protection_manager=self._protection_manager)
        self._insights_page = InsightsPage()
        self._sleepguard_page = SleepGuardPage(sleepguard=self._sleepguard)
        self._history_page = HistoryPage()
        self._settings_page = SettingsPage(tracker=self._tracker, protection_manager=self._protection_manager)
        self._settings_page.settings_changed.connect(self._on_settings_changed)
        self._settings_page.theme_changed_req.connect(self._animate_theme_change)
        self._settings_page.manual_update_requested.connect(self.manual_update_requested.emit)
        self._settings_page.update_now_requested.connect(self.update_now_requested.emit)
        self._settings_page.update_later_requested.connect(self.update_later_requested.emit)
        self._debug_page = DebugPage(tracker=self._tracker)
        self._websites_page = WebsitesPage(protection_manager=self._protection_manager)

        self._stack.addWidget(self._dashboard_page)         # 0: Home
        self._stack.addWidget(self._activity_page)          # 1: Usage
        self._stack.addWidget(self._wellbeing_page)         # 2: Focus
        self._stack.addWidget(self._app_locker_page)        # 3: App Locker
        self._stack.addWidget(self._app_timer_page)         # 4: App Timer
        self._stack.addWidget(self._insights_page)          # 5: Insights
        self._stack.addWidget(self._sleepguard_page)        # 6: SleepGuard
        self._stack.addWidget(self._history_page)           # 7: History
        self._stack.addWidget(self._settings_page)          # 8: Settings
        self._stack.addWidget(self._debug_page)             # 9: Dev Mode
        self._stack.addWidget(self._screen_time_details_page) # 10: Screen Time Details
        self._stack.addWidget(self._app_details_page)         # 11: App Details
        self._stack.addWidget(self._websites_page)            # 12: Websites (Cross-Browser)

        # Wire App Locker lock events to auth dialog
        from protection.app_locker import AppLockerManager
        self._app_locker_mgr = AppLockerManager.instance()
        self._app_locker_mgr.lock_triggered.connect(self._show_lock_auth_dialog)

        # Wire Focus Manager app_blocked signal to feedback dialog
        from protection.focus_manager import FocusManager
        self._focus_mgr = FocusManager.instance()
        self._focus_mgr.app_blocked.connect(self._show_blocked_app_dialog)
        self._active_blocked_dialog = None

        # Stack layout for main content
        root_layout.addWidget(self._stack, 1)
        if self._nav_buttons:
            self._nav_buttons[0].click()

        ThemeManager.instance().theme_changed.connect(self._apply_theme)
        self._apply_theme(ThemeManager.instance().is_dark)



    def _setup_shortcuts(self) -> None:
        self._dev_shortcut = QShortcut(QKeySequence("Ctrl+Shift+D"), self)
        self._dev_shortcut.activated.connect(self._toggle_dev_mode)

        self._refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        self._refresh_shortcut.activated.connect(self.refresh_all_pages)
        
        self._backspace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Backspace), self)
        self._backspace_shortcut.activated.connect(self._navigate_back)
        
        self._alt_left_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        self._alt_left_shortcut.activated.connect(self._navigate_back)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.BackButton or event.button() == Qt.MouseButton.XButton1:
            self._navigate_back()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _toggle_dev_mode(self) -> None:
        from core.logger import logger
        logger.info("[DEV MODE] Hidden developer shortcut Ctrl+Shift+D activated")
        self._navigate(9)  # Dev Mode is now page 9

    def _show_shutdown_warning_dialog(self, countdown_s: int, action: str = "lock") -> None:
        from core.logger import logger
        from PySide6.QtCore import QTimer
        logger.info(
            "[SLEEPGUARD_UI] _show_shutdown_warning_dialog entered. countdown_s=%d, action='%s'",
            countdown_s, action,
        )
        # Instantiate with parent=None to ensure it is a true top-level window 
        # and doesn't inherit hidden state from MainWindow when minimized to tray.
        dialog = ShutdownCountdownDialog(countdown_seconds=countdown_s, action=action, parent=None, is_test=False)
        self._active_warning_dialog = dialog
        dialog.finished.connect(lambda: setattr(self, "_active_warning_dialog", None))
        dialog.shutdown_accepted.connect(self._sleepguard.execute_power_action)
        # Wrap the dialog.cancel connection to avoid recursive re-entry between UI and controller
        def _on_dialog_cancel():
            if getattr(self, "_handling_shutdown_cancel", False):
                return
            try:
                self._handling_shutdown_cancel = True
                self._sleepguard.cancel_warning()
            finally:
                self._handling_shutdown_cancel = False

        dialog.shutdown_cancelled.connect(_on_dialog_cancel)

        # Also connect sleepguard-level cancel notifications back to the dialog so programmatic cancels stop the UI
        try:
            self._sleepguard.programmatic_shutdown_cancelled.connect(dialog._on_cancel)
        except Exception:
            # defensive: if signal/slot not available, continue without UI cancel sync
            logger.warning("Failed to connect sleepguard.programmatic_shutdown_cancelled back to dialog")
        logger.info("[SLEEPGUARD_UI] Starting countdown and showing dialog...")
        # Start the dialog timer and show non-blocking so the main event loop continues.
        dialog.start_countdown()
        dialog.setWindowModality(Qt.ApplicationModal)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        logger.info("[SLEEPGUARD_UI] Dialog shown non-blocking (show + raise + activateWindow)")

        # Log visibility shortly after showing
        QTimer.singleShot(200, lambda: logger.info(f"[SLEEPGUARD_UI] Post-show: dialog visible={dialog.isVisible()}"))

    def _animate_theme_change(self, new_theme: str) -> None:
        from ui.theme import ThemeManager
        from PySide6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PySide6.QtCore import QPropertyAnimation

        tm = ThemeManager.instance()
        if tm.resolve_dark_mode(new_theme) == tm.is_dark:
            return  # No change

        # Screenshot crossfade
        pixmap = self.grab()
        self._overlay = QLabel(self)
        self._overlay.setPixmap(pixmap)
        self._overlay.setGeometry(self.rect())
        self._overlay.show()
        self._overlay.raise_()

        # Instantly update theme underneath
        tm.set_theme(new_theme)
        self.refresh_all_pages()

        # Fade out old image
        effect = QGraphicsOpacityEffect(self._overlay)
        self._overlay.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._overlay.deleteLater)
        self._anim.start()

    def _on_settings_changed(self) -> None:
        self.refresh_all_pages()

    def refresh_all_pages(self) -> None:
        from core.logger import logger
        logger.info("[REFRESH] Executing V2 global refresh for all pages...")
        for i in range(self._stack.count()):
            page = self._stack.widget(i)
            if hasattr(page, "on_data_changed"):
                try:
                    page.on_data_changed()
                except Exception as exc:
                    logger.warning("Error refreshing %s: %s", type(page).__name__, exc)
        logger.info("[REFRESH] Global refresh complete.")

    def _show_lock_auth_dialog(self, process_name: str) -> None:
        """Called when AppLockerManager detects a locked app in the foreground."""
        from core.logger import logger
        from database.repository import Repository
        from protection.pin import PINManager
        from ui.widgets.auth_dialog import AppLockerAuthDialog

        try:
            repo = Repository()
            pin_manager = PINManager(repo)
            alm = self._app_locker_mgr

            # Get display name
            locked_apps = alm.get_locked_apps()
            display_name = next(
                (a["display_name"] for a in locked_apps if a["process_name"] == process_name),
                process_name,
            )

            dialog = AppLockerAuthDialog(
                process_name=process_name,
                display_name=display_name,
                pin_manager=pin_manager,
                auth_method=alm.auth_method.value,
                parent=None,  # Top-level so it shows even when the app is minimized
            )

            from PySide6.QtWidgets import QDialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                alm.grant_temporary_access(process_name)
                logger.info("App Locker: access granted to %s", process_name)
            else:
                alm.on_auth_canceled()
                logger.info("App Locker: access denied for %s", process_name)
        except Exception as exc:
            logger.error("_show_lock_auth_dialog error: %s", exc)
            # Always clear the dialog_open flag so the next tick can try again
            if hasattr(self, "_app_locker_mgr"):
                self._app_locker_mgr.on_auth_canceled()

    def _navigate_to_screen_time_details(self, target_date=None) -> None:
        from datetime import date
        if isinstance(target_date, date):
            self._screen_time_details_page.refresh(target_date)
            self._navigate(10)
        else:
            self._screen_time_details_page.refresh()
            self._navigate(10)

    def _navigate_to_app_details(self, process_name: str) -> None:
        self._app_details_page.set_app(process_name)
        self._navigate(11)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Brand Header
        logo_widget = QWidget()
        logo_layout = QHBoxLayout(logo_widget)
        logo_layout.setContentsMargins(20, 28, 20, 20)
        logo_layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.png"
        pix = QPixmap(str(icon_path))
        if not pix.isNull():
            icon_lbl.setPixmap(pix.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        from core.constants import APP_VERSION
        self._logo_overline = QLabel("DIGITAL")
        self._logo_overline.setObjectName("sidebar_logo_overline")
        self._logo_lbl = QLabel("WELLBEING")
        self._logo_lbl.setObjectName("sidebar_logo_label")
        self._subtitle_lbl = QLabel(f"v{APP_VERSION}")
        self._subtitle_lbl.setObjectName("sidebar_subtitle_label")
        brand_col.addWidget(self._logo_overline)
        brand_col.addWidget(self._logo_lbl)
        brand_col.addWidget(self._subtitle_lbl)

        logo_layout.addWidget(icon_lbl)
        logo_layout.addLayout(brand_col)
        logo_layout.addStretch()
        layout.addWidget(logo_widget)

        self._separator = QFrame()
        self._separator.setFrameShape(QFrame.Shape.HLine)
        self._separator.setMaximumHeight(1)
        layout.addWidget(self._separator)

        # Navigation Rail Items (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(2)
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        from ui.icons import get_icon

        def _make_section_hdr(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setObjectName("nav_section_header")
            return lbl

        def _make_nav_btn(text: str, icon_name: str, page_idx: int) -> QPushButton:
            btn = QPushButton(f"  {text}")
            btn.setIcon(get_icon(icon_name, size=18))
            btn._icon_name = icon_name  # remembered so theme switches can recolor the icon
            btn.setObjectName("nav_btn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self._navigate(page_idx))
            return btn

        # ── OVERVIEW Section ────────────────────────────
        nav_layout.addWidget(_make_section_hdr("OVERVIEW"))
        self._home_btn = _make_nav_btn("Home", "home", 0)
        self._activity_btn = _make_nav_btn("Usage", "usage", 1)
        self._websites_btn = _make_nav_btn("Websites", "globe", 12)
        self._insights_btn = _make_nav_btn("Insights", "insights", 5)
        nav_layout.addWidget(self._home_btn)
        nav_layout.addWidget(self._activity_btn)
        nav_layout.addWidget(self._websites_btn)
        nav_layout.addWidget(self._insights_btn)

        # ── CONTROL Section ─────────────────────────────
        nav_layout.addSpacing(10)
        nav_layout.addWidget(_make_section_hdr("CONTROL"))
        self._focus_btn = _make_nav_btn("Focus", "focus", 2)
        self._timer_btn = _make_nav_btn("App Timer", "clock", 4)
        self._locker_btn = _make_nav_btn("App Locker", "lock", 3)
        self._sleepguard_btn = _make_nav_btn("SleepGuard", "sleepguard", 6)
        nav_layout.addWidget(self._focus_btn)
        nav_layout.addWidget(self._timer_btn)
        nav_layout.addWidget(self._locker_btn)
        nav_layout.addWidget(self._sleepguard_btn)

        nav_layout.addStretch()

        # ── SYSTEM Section (Footer Pinned) ──────────────
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 4, 0, 16)
        footer_layout.setSpacing(2)
        footer_layout.addWidget(_make_section_hdr("SYSTEM"))

        self._settings_btn = _make_nav_btn("Settings", "settings", 8)
        footer_layout.addWidget(self._settings_btn)

        self._debug_btn = _make_nav_btn("Dev Mode", "system", 9)
        self._debug_btn.setVisible(False)
        footer_layout.addWidget(self._debug_btn)

        layout.addWidget(footer_widget)

        # Map stack page index to button for clean active-state pill management
        self._page_to_nav_btn = {
            0: self._home_btn,
            1: self._activity_btn,
            2: self._focus_btn,
            3: self._locker_btn,
            4: self._timer_btn,
            5: self._insights_btn,
            6: self._sleepguard_btn,
            7: self._home_btn,
            8: self._settings_btn,
            9: self._debug_btn,
            12: self._websites_btn,
        }

        # Compatible list of nav buttons
        self._nav_buttons = [
            self._home_btn,
            self._activity_btn,
            self._websites_btn,
            self._focus_btn,
            self._locker_btn,
            self._timer_btn,
            self._insights_btn,
            self._sleepguard_btn,
            self._debug_btn,
            self._settings_btn,
        ]

        return sidebar

    def _refresh_nav_icons(self) -> None:
        """Recolor sidebar SVG icons (theme + active state)."""
        from ui.theme import ThemeManager
        from ui.icons import get_icon
        tm = ThemeManager.instance()
        active_color = tm.color('accent_tint_text')
        active_btn = self._active_nav_btn
        for btn in getattr(self, "_nav_buttons", []):
            icon_name = getattr(btn, "_icon_name", None)
            if not icon_name:
                continue
            if btn is active_btn:
                btn.setIcon(get_icon(icon_name, color=active_color, size=18))
            else:
                btn.setIcon(get_icon(icon_name, color=tm.color('text_sub'), size=18))

    def _apply_theme(self, is_dark: bool) -> None:
        from ui.theme import ThemeManager
        from ui import design_system as ds
        tm = ThemeManager.instance()

        sidebar_bg = tm.color('sidebar_bg')
        hover_bg = tm.color('surface_hover')
        active_bg = tm.color('accent_tint_bg')
        active_color = tm.color('accent_tint_text')

        self._sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background: {sidebar_bg};
                border-right: 1px solid {tm.color('separator')};
            }}
            QLabel#nav_section_header {{
                {ds.type_css('micro', tm.color('text_muted'))}
                text-transform: uppercase;
                margin: 8px 18px 4px 18px;
            }}
            QPushButton#nav_btn {{
                background: transparent;
                color: {tm.color('text_sub')};
                border: none;
                border-radius: {ds.RADIUS['md']}px;
                padding: 9px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
                margin: 1px 12px;
            }}
            QPushButton#nav_btn:hover {{
                background: {hover_bg};
                color: {tm.color('text_main')};
            }}
            QPushButton#nav_btn[active="true"] {{
                background: {active_bg};
                color: {active_color};
                font-weight: 600;
            }}
            QPushButton#nav_btn:pressed {{
                background: {tm.color('surface_pressed')};
            }}

        """)

        self._logo_overline.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {tm.color('text_muted')}; letter-spacing: 2.6px;")
        self._logo_lbl.setStyleSheet(
            f"font-size: 17px; font-weight: 700; color: {tm.color('text_main')}; letter-spacing: 0.4px;")
        self._subtitle_lbl.setStyleSheet(
            f"font-size: 10px; font-weight: 600; color: {active_color}; letter-spacing: 0.6px; margin-top: 1px;")
        self._separator.setStyleSheet(f"background: {tm.color('separator')}; margin: 0 16px;")

        # Recolor sidebar SVG icons for the current theme
        self._refresh_nav_icons()
        
        central = self.centralWidget()
        if central:
            central.setStyleSheet(f"QWidget#central_widget {{ background-color: {tm.color('bg')}; }}")

        # Repolish active button
        if self._active_nav_btn:
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

    def _navigate(self, page_idx: int) -> None:
        curr_idx = self._stack.currentIndex()
        if curr_idx == page_idx:
            return

        if page_idx in getattr(self, "_page_to_nav_btn", {}):
            # Main sidebar navigation, clear history
            self._navigation_history.clear()
        else:
            # Drilling down into a detail page, push current index
            self._navigation_history.append(curr_idx)

        if self._active_nav_btn:
            self._active_nav_btn.setProperty("active", False)
            self._active_nav_btn.style().unpolish(self._active_nav_btn)
            self._active_nav_btn.style().polish(self._active_nav_btn)

        # Highlight sidebar button via mapping
        target_btn = getattr(self, "_page_to_nav_btn", {}).get(page_idx)
        if target_btn:
            target_btn.setProperty("active", True)
            target_btn.style().unpolish(target_btn)
            target_btn.style().polish(target_btn)
            self._active_nav_btn = target_btn

        self._refresh_nav_icons()
        self._stack.setCurrentIndexAnimated(page_idx)

    def _navigate_back(self) -> None:
        if self._navigation_history:
            prev_idx = self._navigation_history.pop()
            
            if self._active_nav_btn:
                self._active_nav_btn.setProperty("active", False)
                self._active_nav_btn.style().unpolish(self._active_nav_btn)
                self._active_nav_btn.style().polish(self._active_nav_btn)

            target_btn = getattr(self, "_page_to_nav_btn", {}).get(prev_idx)
            if target_btn:
                target_btn.setProperty("active", True)
                target_btn.style().unpolish(target_btn)
                target_btn.style().polish(target_btn)
                self._active_nav_btn = target_btn

            self._refresh_nav_icons()
            self._stack.setCurrentIndexAnimated(prev_idx)



    def _show_limit_dialog(self, process_name: str, limit_seconds: int) -> None:
        if process_name in self._active_limit_dialogs:
            return
            
        self._active_limit_dialogs.add(process_name)
        
        if self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()
            
        dlg = LimitReachedDialog(process_name, limit_seconds, self)
        
        def on_close_app(pname: str):
            self._protection_manager.force_close(pname)
            
        def on_override(pname: str):
            pin_dlg = PinOverrideDialog(pname, self._protection_manager.pin, self)
            pin_dlg.override_granted.connect(self._protection_manager.add_override)
            pin_dlg.exec()
            
        dlg.close_app_requested.connect(on_close_app)
        dlg.override_requested.connect(on_override)
        dlg.exec()
        
        # When dialog is closed (for any reason), remove it from active set
        self._active_limit_dialogs.discard(process_name)

    def _show_blocked_app_dialog(self, process_name: str, mode_name: str, seconds_remaining: int) -> None:
        if getattr(self, "_active_blocked_dialog", None) is not None:
            return  # Already showing an active feedback dialog, prevent stacking

        from ui.widgets.blocked_app_dialog import BlockedAppFeedbackDialog
        dlg = BlockedAppFeedbackDialog(process_name, mode_name, seconds_remaining, self)
        self._active_blocked_dialog = dlg

        def on_return_to_focus():
            # Engage suppression so this app doesn't re-trigger an immediate popup loop
            self._focus_mgr.suppress_blocked_app(process_name, duration=12.0)

            # Minimize any remaining visible windows of the blocked app
            try:
                import win32gui, win32process, win32con, psutil
                target_lower = process_name.lower()
                def enum_min_cb(h, _):
                    try:
                        if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h):
                            _, wpid = win32process.GetWindowThreadProcessId(h)
                            if wpid > 4:
                                p = psutil.Process(wpid)
                                if p.name().lower() == target_lower:
                                    win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
                    except Exception:
                        pass
                    return True
                win32gui.EnumWindows(enum_min_cb, None)
            except Exception:
                pass

            if self.isHidden():
                self.show()
            self.raise_()
            self.activateWindow()

            # Forcefully assert foreground focus for the Digital Wellbeing main window on Windows
            try:
                import win32gui, win32con
                hwnd = int(self.winId())
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
            except Exception:
                pass

            # Switch to Focus page (page index 3 in sidebar)
            focus_nav_btn = getattr(self, "_nav_buttons", [None]*4)[3]
            if focus_nav_btn:
                focus_nav_btn.click()

        def on_cancel_focus():
            if self._focus_mgr.is_strict:
                from ui.widgets.pin_dialog import PinDialog
                dialog = PinDialog(self._focus_mgr._pin_manager, self)
                if dialog.exec():
                    self._focus_mgr.stop_focus_after_pin_dialog()
            else:
                self._focus_mgr.stop_focus()

        dlg.return_to_focus.connect(on_return_to_focus)
        dlg.cancel_focus.connect(on_cancel_focus)
        dlg.rejected.connect(lambda: self._focus_mgr.suppress_blocked_app(process_name, duration=8.0))
        dlg.finished.connect(lambda _: setattr(self, "_active_blocked_dialog", None))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _show_website_limit_dialog(self, process_name: str, domain: str, limit_seconds: int) -> None:
        key = f"{process_name}:{domain}"
        if key in self._active_limit_dialogs:
            return

        self._active_limit_dialogs.add(key)

        # Close the offending browser tab so the restricted site doesn't remain usable
        from protection.process import ProcessController
        ProcessController.close_browser_tab()

        if self.isHidden():
            self.show()
            self.raise_()
            self.activateWindow()

        from ui.widgets.limit_dialog import LimitReachedDialog
        dlg = LimitReachedDialog(domain, limit_seconds, self)

        def on_override(dom: str):
            from ui.widgets.limit_dialog import PinOverrideDialog
            pin_dlg = PinOverrideDialog(dom, self._protection_manager.pin, self)
            pin_dlg.override_granted.connect(lambda duration_m: self._protection_manager.add_website_override(domain, duration_m))
            pin_dlg.exec()

        dlg.override_requested.connect(on_override)
        dlg.exec()

        self._active_limit_dialogs.discard(key)

    def _refresh_current_page(self, index: int = -1) -> None:
        if index == -1:
            index = self._stack.currentIndex()
        if index >= 0 and index < self._stack.count():
            page = self._stack.widget(index)
            if hasattr(page, "on_data_changed") and callable(page.on_data_changed):
                page.on_data_changed()

    def _connect_tracker(self) -> None:
        self._data_thread = DataUpdateThread(self._tracker, self)
        self._data_thread.data_changed.connect(self._refresh_current_page)

    def closeEvent(self, event) -> None:
        from settings.manager import SettingsManager
        sm = SettingsManager()
        if sm.get_bool("minimize_to_tray", default=False):
            event.ignore()
            self.hide()
        else:
            if self._owns_sleepguard and hasattr(self, "_sleepguard") and self._sleepguard:
                self._sleepguard.stop()
            try:
                from protection.website_blocker import WebsiteBlocker
                WebsiteBlocker().unblock_all()
            except Exception:
                pass
            event.accept()
            self.quit_requested.emit()
