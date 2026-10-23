from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from notifications.notifier import Notifier
from core.logger import logger

class NotificationManager(QObject):
    # Signals to be connected to the main UI thread
    show_limit_dialog = Signal(str, int)  # process_name, limit_seconds
    show_website_limit_dialog = Signal(str, str, int)  # process_name, domain, limit_seconds

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._notifier = Notifier()

    def send_warning(self, process_name: str, remaining_minutes: int) -> None:
        """Send a Windows toast notification for upcoming limits."""
        display_name = process_name.replace(".exe", "").title()
        
        if remaining_minutes == 0:
            title = "Limit Reached"
            msg = f"{display_name} has reached its screen time limit."
        else:
            title = "App Limit Warning"
            msg = f"You have {remaining_minutes} minute{'s' if remaining_minutes > 1 else ''} left for {display_name}."
            
        logger.info(f"NotificationManager: {title} - {msg}")
        self._notifier.notify(title, msg, duration=5)

    def send_website_warning(self, domain: str, remaining_minutes: int) -> None:
        """Send a Windows toast notification for upcoming website limits."""
        if remaining_minutes == 0:
            title = "Website Limit Reached"
            msg = f"{domain} has reached its screen time limit."
        else:
            title = "Website Limit Warning"
            msg = f"You have {remaining_minutes} minute{'s' if remaining_minutes > 1 else ''} left for {domain}."

        logger.info(f"NotificationManager: {title} - {msg}")
        self._notifier.notify(title, msg, duration=5)

    def trigger_lock_dialog(self, process_name: str, limit_seconds: int) -> None:
        """Emit a signal to the UI thread to show the blocking Lock Dialog."""
        logger.info(f"NotificationManager: Triggering lock dialog for {process_name}")
        self.show_limit_dialog.emit(process_name, limit_seconds)

    def trigger_website_lock_dialog(self, process_name: str, domain: str, limit_seconds: int) -> None:
        """Emit a signal to the UI thread to show the website overlay dialog."""
        logger.info(f"NotificationManager: Triggering website lock dialog for {domain} in {process_name}")
        self.show_website_limit_dialog.emit(process_name, domain, limit_seconds)
