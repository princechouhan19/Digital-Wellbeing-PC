from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from core.constants import APP_NAME, APP_VERSION
from core.logger import logger
from settings.manager import SettingsManager
from tracker.manager import TrackingManager
from ui.main_window import MainWindow
from ui.theme import apply_theme
from utils.win_utils import set_dpi_awareness


class DigitalWellbeingApp:
    def __init__(self, start_minimized: bool = False) -> None:
        set_dpi_awareness()

        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setApplicationName(APP_NAME)
        self._app.setOrganizationName("DigitalWellbeing")
        # We manage the quit lifecycle manually — quitOnLastWindowClosed is
        # disabled so that destroying the window (via closeEvent) does not
        # trigger a second quit() call before our cleanup has finished.
        self._app.setQuitOnLastWindowClosed(False)

        # Aurora design system: register bundled Inter fonts BEFORE any widget paints
        from ui.design_system import load_fonts
        load_fonts()

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
        for icp in icon_candidates:
            if icp.is_file():
                ico = QIcon(str(icp))
                if not ico.isNull():
                    self._app.setWindowIcon(ico)
                    break

        # Guard flag: ensures _cleanup() and _quit() are idempotent and re-entrant safe.
        self._shutting_down: bool = False

        # Connect cleanup to aboutToQuit as a safety net for any unexpected exit path.
        self._app.aboutToQuit.connect(self._cleanup)

        # 1. Enforce single-instance execution via QLocalServer
        from PySide6.QtNetwork import QLocalServer, QLocalSocket, QAbstractSocket
        self._server_name = "DigitalWellbeingUniqueLocalServerKey"
        self._already_running = False

        import os
        is_test = os.environ.get("DW_TEST_MODE") == "1"
        is_debug = os.environ.get("DW_DEBUG_MODE") == "1"

        logger.info(f"[SINGLE_INSTANCE] Initializing single-instance check. Server name: {self._server_name}, Test Mode: {is_test}, Debug Mode: {is_debug}")

        if not is_test and not is_debug:
            socket = QLocalSocket(self._app)
            logger.info(f"[SINGLE_INSTANCE] Attempting to connect to existing server '{self._server_name}'...")
            socket.connectToServer(self._server_name)
            
            connected = socket.waitForConnected(200)
            if connected:
                logger.info(f"[SINGLE_INSTANCE] Successfully connected to existing server. Socket state: {socket.state()}")
                # An instance is already active. Notify and exit.
                socket.write(b"show_window")
                if socket.waitForBytesWritten(500):
                    logger.info("[SINGLE_INSTANCE] Successfully wrote 'show_window' request to existing instance.")
                else:
                    logger.warning("[SINGLE_INSTANCE] Failed to write to existing instance.")
                socket.close()
                self._already_running = True
                logger.info("Another active instance was detected. Sent show_window request and exiting.")
                return
            else:
                socket_err = socket.error()
                socket_err_str = socket.errorString()
                logger.info(f"[SINGLE_INSTANCE] Failed to connect to existing server. Connected: False, Error Code: {socket_err}, Error String: '{socket_err_str}'. Assuming no other instance is running.")

            # No active instance. Setup local server for this process.
            logger.info(f"[SINGLE_INSTANCE] Removing any stale server named '{self._server_name}'...")
            QLocalServer.removeServer(self._server_name)
            
            self._server = QLocalServer(self._app)
            listen_success = self._server.listen(self._server_name)
            logger.info(f"[SINGLE_INSTANCE] Starting server listen() result: {listen_success}")
            
            if not listen_success:
                logger.error("Failed to bind single-instance server listener: %s", self._server.errorString())
            else:
                self._server.newConnection.connect(self._on_new_connection)
                logger.info(f"[SINGLE_INSTANCE] Server is now listening on '{self._server_name}'")

        # 2. Standard initialization for primary process
        self._sm = SettingsManager()
        apply_theme(self._app, self._sm.theme)

        self._tracker = TrackingManager()
        from tracker.sleepguard import SleepGuardController
        self._sleepguard = SleepGuardController()
        self._window: Optional[MainWindow] = None
        self._tray: Optional[QSystemTrayIcon] = None

        self._setup_tray()
        
        from notifications.notifier import Notifier
        self._notifier = Notifier()
        if self._tray:
            Notifier.set_tray_icon(self._tray)
            
        self._tracker.start()
        self._sleepguard.start()

        from database.repository import Repository
        from protection.core import ProtectionManager
        self._protection_manager = ProtectionManager(Repository())
        self._tracker.add_active_tick_callback(self._protection_manager.tick)

        self._window = MainWindow(self._tracker, self._sleepguard, self._protection_manager)
        # Connect the window's quit request signal to our controlled shutdown method.
        self._window.quit_requested.connect(self._quit)
        self._window.focus_completed.connect(self._on_focus_completed)

        # A persisted lockout must be visible even when the app was started
        # minimized. Check the cheap settings row before importing the manager.
        try:
            from database.repository import Repository as _Repo

            if _Repo().get_setting("focus_active_session"):
                from protection.focus_manager import FocusManager as _FM

                if _FM.instance().is_lockout:
                    self._window.show()
        except Exception:
            pass

        # Optional loopback bridge for the bundled Web Rules browser extension.
        from protection.extension_bridge import ExtensionBridge
        self._extension_bridge = ExtensionBridge.instance()
        self._extension_bridge.start()

        # Evening display warm-up, scheduled from the SleepGuard bedtime.
        from protection.circadian import CircadianController
        self._circadian = CircadianController.instance()
        self._circadian.start()

        # Recurring Focus blocks (stored locally, checked every 30 seconds).
        from protection.focus_schedule import FocusScheduleEngine
        self._schedule_engine = FocusScheduleEngine()
        self._schedule_engine.start()

        # Gentle in-the-moment fragmentation nudge.
        from protection.attention_nudge import AttentionNudgeController
        self._nudge_controller = AttentionNudgeController()
        self._nudge_controller.nudge_ready.connect(self._show_fragmentation_nudge)
        self._nudge_controller.start()

        # Adult Content Protection Motivation Modal
        from protection.adult_content_shield import AdultContentShield
        from ui.widgets.adult_motivation_dialog import AdultContentMotivationDialog
        self._active_motivation_dialog = None

        def _show_adult_motivation_modal(reason: str, title_context: str):
            def _gui_show():
                if self._active_motivation_dialog and self._active_motivation_dialog.isVisible():
                    return
                dlg = AdultContentMotivationDialog(reason=reason, title_context=title_context, parent=self._window or None)
                dlg.start_focus_requested.connect(self._trigger_quick_focus)
                self._active_motivation_dialog = dlg
                dlg.show()
            QTimer.singleShot(0, _gui_show)

        AdultContentShield.instance().register_motivation_callback(_show_adult_motivation_modal)

        if not start_minimized:
            self._window.show()
        else:
            # Start minimized: don't show the main window. Tray icon remains active.
            logger.info("Starting minimized to tray; main window will not be shown")
            self._window.hide()

        from analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        engine.ensure_historical_snapshots()
        from datetime import date
        self._last_checked_date = date.today()

        # Updater: check GitHub Releases for newer installers (non-blocking)
        try:
            from utils.updater import Updater
            from ui.widgets.update_dialog import UpdateDialog

            self._updater = Updater()
            self._latest_update_info = None
            self._active_update_dialog = None
            self._manual_update_check_in_progress = False
            self._has_checked_startup_update = False
            self._update_dismissed_this_session = False

            def _start_download_flow():
                if not self._latest_update_info:
                    return
                info = self._latest_update_info
                ver = info.get("version", "")
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_download_progress(0, ver)

                self._updater.download_installer(
                    asset_url=info.get("asset_url"),
                    asset_name=info.get("asset_name"),
                    asset_id=info.get("asset_id"),
                    checksum_url=info.get("checksum_url"),
                    checksum_id=info.get("checksum_id"),
                    expected_sha256=info.get("expected_sha256"),
                    version=ver,
                )

            def _on_update_available(info: dict) -> None:
                self._latest_update_info = info
                is_manual = self._manual_update_check_in_progress
                self._manual_update_check_in_progress = False

                ver = info.get("version", "")
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_update_available(ver)

                # If this was an automatic background check and user already dismissed it this session, skip modal dialog
                if not is_manual and self._update_dismissed_this_session:
                    logger.info("Updater: update available (%s) but dismissed for this session. Skipping modal dialog.", ver)
                    return

                # Defer if active SleepGuard countdown or active focus session
                sg_active = False
                try:
                    sg_active = getattr(self, "_sleepguard", None) and getattr(self._sleepguard, "_idle_fired", None) and self._sleepguard._idle_fired.is_set()
                except Exception:
                    pass
                focus_active = False
                try:
                    page = self._loaded_page("_wellbeing_page")
                    if page:
                        ft = getattr(page, "_focus_timer", None)
                        if ft and getattr(ft, "_is_running", False):
                            focus_active = True
                except Exception:
                    pass

                if sg_active or focus_active:
                    logger.info("Updater: deferring update dialog due to active session; will retry in 30s")
                    QTimer.singleShot(30_000, lambda: self._updater.check_for_updates())
                    return

                # Show update dialog
                try:
                    self._active_update_dialog = UpdateDialog(
                        current_version=APP_VERSION,
                        new_version=ver,
                        notes=info.get("notes", ""),
                        parent=self._window or None
                    )

                    self._active_update_dialog.update_now.connect(_start_download_flow)
                    self._active_update_dialog.later.connect(lambda: setattr(self, "_update_dismissed_this_session", True))
                    self._active_update_dialog.show()
                except Exception as exc:
                    logger.exception("Updater: failed to show update dialog: %s", exc)

            def _on_no_update():
                self._manual_update_check_in_progress = False
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_update_status_up_to_date()

            def _on_check_error(msg: str):
                self._manual_update_check_in_progress = False
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_update_error("Couldn't check for updates right now.")

            def _on_download_progress(pct: int):
                ver = self._latest_update_info.get("version", "") if self._latest_update_info else ""
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_download_progress(pct, ver)
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.set_progress(pct)
                    except Exception:
                        pass

            def _on_download_complete(installer_path: str):
                ver = self._latest_update_info.get("version", "") if self._latest_update_info else ""
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_installing_status(ver)
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.set_installing(ver)
                    except Exception:
                        pass

                # Launch Inno Setup installer via detached wrapper script and exit the app cleanly
                self._updater.launch_installer_and_exit(installer_path)
                self._quit()

            def _on_download_error(msg: str):
                page = self._loaded_page("_settings_page")
                if page:
                    page.set_update_error("Couldn't check for updates right now.")
                if self._active_update_dialog:
                    try:
                        self._active_update_dialog.show_error(msg)
                    except Exception:
                        pass

            self._updater.update_available.connect(_on_update_available)
            self._updater.no_update.connect(_on_no_update)
            self._updater.error.connect(_on_check_error)
            self._updater.download_progress.connect(_on_download_progress)
            self._updater.download_complete.connect(_on_download_complete)
            self._updater.error.connect(_on_download_error)

            def _handle_manual_update_request():
                self._manual_update_check_in_progress = True
                self._updater.check_for_updates(force=True)

            self._window.manual_update_requested.connect(_handle_manual_update_request)
            self._window.update_now_requested.connect(_start_download_flow)
            self._window.update_later_requested.connect(lambda: setattr(self, "_update_dismissed_this_session", True))

            # Automatic check on startup (once per session, delayed by 5s)
            def _startup_update_check():
                if not self._has_checked_startup_update:
                    self._has_checked_startup_update = True
                    from utils.updater import GITHUB_OWNER
                    if GITHUB_OWNER:
                        self._updater.check_for_updates()

            QTimer.singleShot(5_000, _startup_update_check)
        except Exception as exc:
            logger.warning("Updater initialization failed: %s", exc)

        # 8. Start Telemetry Heartbeat (10s delay to prevent startup blocking)
        from tracker.telemetry import TelemetryManager
        QTimer.singleShot(10000, lambda: TelemetryManager.instance().start_heartbeat())

        if os.environ.get("DW_SCREENSHOT_MODE") == "1":
            def take_screenshots():
                import time
                if self._window:
                    base_path = r"C:\Users\akshi\.gemini\antigravity-ide\brain\2a916beb-1ca0-41a9-80f8-940c213c0137\scratch"
                    
                    # Dashboard
                    self._window._navigate(0)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_home.png")
                    
                    # Activity
                    self._window._navigate(1)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_activity.png")
                    
                    # Settings
                    self._window._navigate(4)
                    self._app.processEvents()
                    time.sleep(0.2)
                    self._window.grab().save(f"{base_path}\\real_settings.png")
                    
                self._app.quit()
            QTimer.singleShot(2000, take_screenshots)

        self._daily_check_timer = QTimer()
        self._daily_check_timer.setInterval(60_000)
        self._daily_check_timer.timeout.connect(self._on_daily_check_timer)
        self._daily_check_timer.start()

        # SafeBrowse content filter: refresh stale open-source lists in the
        # background and recover any orphaned hosts section after a crash.
        try:
            from protection.content_blocker import ContentBlocker
            QTimer.singleShot(15_000, lambda: ContentBlocker.instance().maybe_auto_sync_on_startup())
            QTimer.singleShot(15_500, lambda: ContentBlocker.instance().cleanup_orphaned_block())
        except Exception as exc:
            logger.warning(f"SafeBrowse startup hook failed: {exc}")

        logger.info("Application started successfully")

    def _loaded_page(self, attr_name: str):
        """Return a MainWindow page only if it has already been instantiated.

        Update notifications must not force lazy pages (Settings, Focus) to be
        built in the background; if the page is not loaded there is no UI to
        update, and it will pick up the current state when first opened.
        """
        window = getattr(self, "_window", None)
        if window is None or not hasattr(window, "get_loaded_page"):
            return None
        return window.get_loaded_page(attr_name)

    def _on_new_connection(self) -> None:
        conn = self._server.nextPendingConnection()
        if conn:
            if conn.waitForReadyRead(500):
                msg = conn.readAll().data().decode("utf-8")
                if msg == "show_window":
                    self._show_window()
            conn.close()

    def _setup_tray(self) -> None:
        icon = self._get_tray_icon()
        self._tray = QSystemTrayIcon(icon, self._app)
        self._tray.setToolTip(APP_NAME)

        menu = QMenu()
        try:
            from ui.theme import ThemeManager
            tm = ThemeManager.instance()
            menu.setStyleSheet(
                f"QMenu {{ background: {tm.color('surface_elevated')}; color: {tm.color('text_main')};"
                f" border: 1px solid {tm.color('border_strong')}; border-radius: 10px; padding: 5px; }}"
                "QMenu::item { padding: 7px 20px; border-radius: 6px; }"
                f"QMenu::item:selected {{ background: {tm.color('accent')}; color: #FFFFFF; }}"
                f"QMenu::separator {{ height: 1px; background: {tm.color('separator')}; margin: 5px 10px; }}"
            )
        except Exception:
            pass

        show_action = QAction("Open Digital Wellbeing", self._app)
        show_action.triggered.connect(self._show_window)

        toggle_tracking = QAction("Pause Tracking", self._app)
        toggle_tracking.triggered.connect(self._toggle_tracking)
        self._toggle_tracking_action = toggle_tracking

        quit_action = QAction("Quit", self._app)
        quit_action.triggered.connect(self._quit)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(toggle_tracking)
        menu.addSeparator()
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _get_tray_icon(self) -> QIcon:
        icon_path = Path(__file__).parent.parent / "assets" / "icons" / "app_icon.ico"
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self) -> None:
        if self._window:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()
            self._window.setWindowState(
                self._window.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive
            )

    def _toggle_tracking(self) -> None:
        if self._tracker.is_running:
            self._tracker.stop()
            self._toggle_tracking_action.setText("Resume Tracking")
            self._notifier.notify(APP_NAME, "Tracking paused.", duration=2)
        else:
            self._tracker.start()
            self._toggle_tracking_action.setText("Pause Tracking")
            self._notifier.notify(APP_NAME, "Tracking resumed.", duration=2)

    def _on_focus_completed(self) -> None:
        self._notifier.notify(
            "Focus Session Complete",
            "Great job! Take a well-deserved break.",
            duration=5,
        )

    def _show_fragmentation_nudge(self, switches: int) -> None:
        import os

        if os.environ.get("DW_TEST_MODE") == "1" or self._window is None:
            return
        from protection.focus_manager import FocusManager
        from ui.widgets.fragmentation_nudge_dialog import FragmentationNudgeDialog

        dialog = FragmentationNudgeDialog(switches, FocusManager.instance(), parent=self._window)
        self._active_nudge_dialog = dialog
        dialog.finished.connect(lambda _: setattr(self, "_active_nudge_dialog", None))
        dialog.show()
        dialog.raise_()

    def _trigger_quick_focus(self) -> None:
        """Starts an immediate 5-minute Focus Reset session to steer attention away from adult content."""
        try:
            self._show_window()
            if hasattr(self, "_window") and self._window:
                self._window._navigate(2)
                from protection.focus_manager import FocusManager
                fm = FocusManager.instance()
                if not fm.is_active:
                    fm.start_focus(5, strict_mode=False)
                    self._notifier.notify(
                        "Focus Reset Activated",
                        "A 5-minute mindful focus reset has been started.",
                        duration=4,
                    )
        except Exception as exc:
            logger.warning("Failed to start quick focus reset: %s", exc)

    def _on_daily_check_timer(self) -> None:
        from datetime import date
        today = date.today()
        from analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine()
        
        # Check for date change to capture historical snapshot
        if self._last_checked_date < today:
            logger.info("Date changed from %s to %s. Generating daily snapshot.", self._last_checked_date, today)
            engine.generate_daily_snapshot(self._last_checked_date)
            self._last_checked_date = today

        if not self._sm.get_bool("notifications_enabled", True):
            return

        limit_min = self._sm.get_int("daily_limit_minutes", 480)
        summary = engine.get_today_summary()
        used_min = summary.active_time_s / 60

        if used_min >= limit_min:
            h = int(limit_min // 60)
            m = int(limit_min % 60)
            self._notifier.notify(
                "Daily Limit Reached",
                f"You've used {h}h {m}m of screen time today.",
                duration=5,
            )
            self._daily_check_timer.setInterval(3_600_000)

    def _cleanup(self) -> None:
        """
        Synchronous resource cleanup. This method is idempotent — calling it
        more than once is safe. It is connected to aboutToQuit as a safety net,
        but is also called directly by _quit() before app.quit() to guarantee
        the tracking thread and tray icon are fully torn down before the process
        exits.
        """
        if self._shutting_down:
            logger.info("[LIFECYCLE] DigitalWellbeingApp._cleanup() called but _shutting_down is already True (ignoring re-entrant call)")
            return
        self._shutting_down = True

        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] Executing clean shutdown: stopping tracker, timers, and tray...")
        log_lifecycle_state("DigitalWellbeingApp._cleanup: BEFORE cleanup operations")

        # 1. Stop the daily check timer first (no more callbacks).
        if hasattr(self, "_daily_check_timer") and self._daily_check_timer:
            logger.info("[LIFECYCLE] Stopping _daily_check_timer")
            self._daily_check_timer.stop()

        # 2. Stop the tracker and sleepguard.
        if hasattr(self, "_tracker") and self._tracker:
            logger.info("[LIFECYCLE] Stopping _tracker")
            self._tracker.stop()

        if hasattr(self, "_sleepguard") and self._sleepguard:
            logger.info("[LIFECYCLE] Stopping _sleepguard")
            self._sleepguard.stop()

        if hasattr(self, "_extension_bridge") and self._extension_bridge:
            logger.info("[LIFECYCLE] Stopping extension bridge")
            self._extension_bridge.stop()

        if hasattr(self, "_circadian") and self._circadian:
            logger.info("[LIFECYCLE] Stopping circadian display schedule")
            self._circadian.stop()

        if hasattr(self, "_schedule_engine") and self._schedule_engine:
            logger.info("[LIFECYCLE] Stopping Focus schedule engine")
            self._schedule_engine.stop()

        if hasattr(self, "_nudge_controller") and self._nudge_controller:
            logger.info("[LIFECYCLE] Stopping attention nudge controller")
            self._nudge_controller.stop()

        # 2b. Close repository connections for this (main) thread. Background threads
        # are responsible for closing their own thread-local connections on exit.
        try:
            from database.repository import Repository
            Repository().close()
            logger.info("Closed main-thread repository DB connection during cleanup")
        except Exception as exc:
            logger.warning("Failed to close main-thread DB connection during cleanup: %s", exc)

        # 3. Close the single-instance server so subsequent launches can connect.
        if hasattr(self, "_server") and self._server:
            logger.info("[LIFECYCLE] Closing QLocalServer")
            self._server.close()
            QLocalServer = type(self._server)
            QLocalServer.removeServer(self._server_name)

        # 4. Hide and destroy the tray icon immediately so it vanishes from the taskbar.
        if hasattr(self, "_tray") and self._tray:
            logger.info("[LIFECYCLE] Destroying QSystemTrayIcon")
            self._tray.hide()
            self._tray.setContextMenu(None)
            self._tray.setParent(None)
            self._tray = None

        log_lifecycle_state("DigitalWellbeingApp._cleanup: AFTER cleanup operations")
        logger.info("[LIFECYCLE] Clean shutdown complete.")

    def _quit(self) -> None:
        """
        The single, authoritative exit point for the application.
        Always call this instead of app.quit() directly to ensure resources
        are released synchronously before the Qt event loop exits.
        """
        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] DigitalWellbeingApp._quit() CALLED")

        if self._shutting_down:
            logger.info("[LIFECYCLE] DigitalWellbeingApp._quit() called but already shutting down")
            return

        # Strict lockout cannot be bypassed through the tray Quit action. The
        # watchdog only covers forceful termination; this is the normal path.
        try:
            from protection.focus_manager import FocusManager

            fm = FocusManager.instance()
            if fm.is_lockout:
                logger.warning("[LIFECYCLE] Quit denied: strict lockout is active.")
                self._notifier.notify(
                    "Lockout active",
                    "This Focus session cannot be ended until its countdown completes.",
                    duration=4,
                )
                if self._window:
                    self._show_window()
                return
        except Exception:
            pass

        logger.info("[LIFECYCLE] Initiating controlled application shutdown...")
        self._cleanup()

        log_lifecycle_state("DigitalWellbeingApp._quit: IMMEDIATELY BEFORE QApplication.quit()")
        logger.info("[LIFECYCLE] Calling self._app.quit()")
        self._app.quit()
        logger.info("[LIFECYCLE] self._app.quit() CALLED")

    def run(self) -> int:
        if self._already_running:
            logger.info("[LIFECYCLE] App already running, returning exit code 0")
            return 0
        from utils.debug_lifecycle import log_lifecycle_state
        logger.info("[LIFECYCLE] DigitalWellbeingApp.run() entering self._app.exec()")
        log_lifecycle_state("DigitalWellbeingApp.run: BEFORE app.exec()")
        
        result = self._app.exec()
        
        logger.info("[LIFECYCLE] DigitalWellbeingApp.run() self._app.exec() RETURNED with code %d", result)
        log_lifecycle_state("DigitalWellbeingApp.run: AFTER app.exec()")
        return result
