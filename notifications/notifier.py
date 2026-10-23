from __future__ import annotations

import os
import sys
import time
import threading
from typing import Optional

from core.logger import logger
from core.constants import APP_NAME, APP_AUMID


class Notifier:
    """
    Production-grade Windows Toast Notification manager for Digital Wellbeing.
    Uses native Windows WinRT Toast Notifications with automatic AUMID registration,
    action center integration, thread safety, deduplication, and resilient fallbacks.
    """
    _tray_icon = None
    _lock = threading.Lock()
    _recent_toasts: dict[str, float] = {}
    _registration_checked = False

    @classmethod
    def set_tray_icon(cls, tray) -> None:
        """Store optional QSystemTrayIcon reference for fallback purposes."""
        cls._tray_icon = tray

    def __init__(self, aumid: str = APP_AUMID) -> None:
        self._aumid = aumid
        self._enabled = True
        self._ensure_registered()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _ensure_registered(self) -> None:
        """
        Ensures the application's AUMID is registered in the Windows registry
        and Start Menu shortcut so Windows Toast notifications display the proper
        app branding, icon, and route to Action Center.
        """
        with self._lock:
            if Notifier._registration_checked:
                return
            Notifier._registration_checked = True

        if sys.platform != "win32":
            return

        try:
            import winreg
            # 1. Register AppUserModelId under HKCU\Software\Classes\AppUserModelId\<AUMID>
            reg_path = rf"Software\Classes\AppUserModelId\{self._aumid}"
            with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
                # Determine absolute path to icon
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                exe_dir = os.path.dirname(sys.executable)
                candidate_icons = [
                    os.path.join(base_dir, "assets", "icons", "app_icon.ico"),
                    os.path.join(base_dir, "_internal", "assets", "icons", "app_icon.ico"),
                    os.path.join(exe_dir, "assets", "icons", "app_icon.ico"),
                    os.path.join(exe_dir, "_internal", "assets", "icons", "app_icon.ico"),
                ]
                icon_path = next((p for p in candidate_icons if os.path.isfile(p)), "")
                if icon_path:
                    winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, os.path.abspath(icon_path))
                winreg.SetValueEx(key, "ShowInSettings", 0, winreg.REG_DWORD, 1)

            # 2. Check and sync Start Menu shortcut AppUserModelID if it exists
            shortcut_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Digital Wellbeing\Digital Wellbeing.lnk")
            if os.path.exists(shortcut_path):
                try:
                    from win32com.propsys import propsys, pscon
                    store = propsys.SHGetPropertyStoreFromParsingName(shortcut_path, None, 2, propsys.IID_IPropertyStore)
                    prop_val = propsys.PROPVARIANTType(self._aumid)
                    store.SetValue(pscon.PKEY_AppUserModel_ID, prop_val)
                    store.Commit()
                except Exception as exc:
                    logger.debug("Shortcut property update: %s", exc)
        except Exception as exc:
            logger.debug("AUMID registration check: %s", exc)

    def _check_windows_user_state(self) -> int:
        """
        Query Windows notification state (SHQueryUserNotificationState).
        Returns integer state code (e.g. 5 = QUNS_ACCEPTS_NOTIFICATIONS, 2 = QUNS_BUSY).
        """
        if sys.platform != "win32":
            return 0
        try:
            import ctypes
            state = ctypes.c_int()
            res = ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
            if res == 0:
                return state.value
        except Exception:
            pass
        return 0

    def _is_duplicate(self, key: str, cooldown: float = 5.0) -> bool:
        """
        Thread-safe deduplication check to prevent duplicate toasts / toast storms.
        Returns True if the identical key was triggered within the cooldown window.
        """
        now = time.time()
        with self._lock:
            # Purge entries older than 60 seconds
            self._recent_toasts = {k: v for k, v in self._recent_toasts.items() if now - v < 60.0}
            last_time = self._recent_toasts.get(key)
            if last_time is not None and (now - last_time < cooldown):
                return True
            self._recent_toasts[key] = now
            return False

    def notify(
        self,
        title: str,
        message: str,
        duration: int = 5,
        tag: Optional[str] = None,
        group: Optional[str] = None,
        debounce: bool = True,
        cooldown: float = 5.0,
    ) -> bool:
        """
        Send a Windows Toast notification.
        - Uses native WinRT ToastNotificationManager with AUMID.
        - Fallbacks gracefully to PowerShell WinRT, QSystemTrayIcon, or logger.
        - Fully thread-safe and non-blocking.
        - Debounces rapid duplicates.
        """
        if not self._enabled:
            logger.info("[NOTIFY] Disabled in notifier instance | Title: %s", title)
            return False

        # Check application settings
        try:
            from settings.manager import SettingsManager
            if not SettingsManager().get_bool("notifications_enabled", True):
                logger.info("[NOTIFY] Disabled in settings: %s", title)
                return False
        except Exception:
            pass

        # Debounce duplicate notifications
        debounce_key = f"{title}::{message}"
        if debounce and self._is_duplicate(debounce_key, cooldown=cooldown):
            logger.info("[NOTIFY] Suppressed duplicate toast within cooldown: %s - %s", title, message)
            return False

        logger.info("[NOTIFY] Sending Windows toast | Title: %s | Body: %s", title, message)

        # Check Windows notification state (Focus Assist, Busy, D3D fullscreen)
        state = self._check_windows_user_state()
        if state in (2, 3, 4, 6):
            state_names = {
                2: "QUNS_BUSY",
                3: "QUNS_RUNNING_D3D_FULL_SCREEN",
                4: "QUNS_PRESENTATION_MODE",
                6: "QUNS_QUIET_TIME (Focus Assist)",
            }
            logger.info("[NOTIFY] Suppressed by Windows state: %s (will route to Action Center)", state_names.get(state, str(state)))

        # Attempt 1: Native WinRT toast
        if sys.platform == "win32":
            try:
                success = self._send_winrt_toast(title, message, tag=tag, group=group)
                if success:
                    logger.info("[NOTIFY] Toast delivered successfully | Title: %s", title)
                    return True
            except Exception as exc:
                logger.warning("[NOTIFY] Toast failed with error: %s", exc)

        # Attempt 2: PowerShell WinRT fallback
        if sys.platform == "win32":
            try:
                success = self._send_powershell_toast(title, message)
                if success:
                    logger.info("[NOTIFY] Toast delivered successfully (via PowerShell) | Title: %s", title)
                    return True
            except Exception as exc:
                logger.warning("[NOTIFY] PowerShell toast failed with error: %s", exc)

        # Attempt 3: QSystemTrayIcon fallback
        if self.__class__._tray_icon:
            try:
                self._send_tray_fallback(title, message, duration)
                logger.info("[NOTIFY] Toast delivered via QSystemTrayIcon fallback | Title: %s", title)
                return True
            except Exception as exc:
                logger.warning("[NOTIFY] QSystemTrayIcon fallback failed: %s", exc)

        # Attempt 4: Logging fallback
        self._send_fallback(title, message)
        return False

    def _send_winrt_toast(
        self,
        title: str,
        message: str,
        tag: Optional[str] = None,
        group: Optional[str] = None,
    ) -> bool:
        import winrt.windows.ui.notifications as notifications
        import winrt.windows.data.xml.dom as xml_dom
        from xml.sax.saxutils import escape

        safe_title = escape(title)
        safe_message = escape(message)

        xml_payload = f"""<toast duration="short">
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_title}</text>
            <text>{safe_message}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default" />
</toast>"""

        doc = xml_dom.XmlDocument()
        doc.load_xml(xml_payload.strip())
        toast = notifications.ToastNotification(doc)
        toast.priority = notifications.ToastNotificationPriority.HIGH
        if tag:
            toast.tag = tag
        if group:
            toast.group = group

        notifier = notifications.ToastNotificationManager.create_toast_notifier_with_id(self._aumid)
        setting = notifier.setting
        if setting != 0:
            logger.warning("[NOTIFY] Notifier setting indicates suppression: %s", setting)

        notifier.show(toast)
        return True

    def _send_powershell_toast(self, title: str, message: str) -> bool:
        import subprocess
        safe_t = title.replace('"', '`"')
        safe_m = message.replace('"', '`"')
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
<toast duration="short">
    <visual>
        <binding template="ToastGeneric">
            <text>{safe_t}</text>
            <text>{safe_m}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default" />
</toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        $toast.Priority = [Windows.UI.Notifications.ToastNotificationPriority]::High
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{self._aumid}")
        $notifier.Show($toast)
        """
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.returncode == 0

    def _send_tray_fallback(self, title: str, message: str, duration: int) -> None:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QSystemTrayIcon
        tray = self.__class__._tray_icon
        if tray:
            # Safely invoke on Qt main thread without QMetaType registration issues
            QTimer.singleShot(0, lambda: tray.showMessage(
                title, message, QSystemTrayIcon.MessageIcon.Information, duration * 1000
            ))

    def _send_fallback(self, title: str, message: str) -> None:
        logger.info("[NOTIFICATION_FALLBACK] %s: %s", title, message)
