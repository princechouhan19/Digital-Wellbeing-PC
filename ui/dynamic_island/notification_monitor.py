"""
notification_monitor.py — Windows Notification Listener for Dynamic Island.
"""
from __future__ import annotations

import asyncio
from PySide6.QtCore import QThread, Signal


class NotificationMonitor(QThread):
    notification_received = Signal(str, str, str)  # app_name, title, body

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.loop = None
        self.listener = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.setup_listener())
        except Exception:
            pass

    async def setup_listener(self):
        try:
            from winrt.windows.ui.notifications.management import (
                UserNotificationListener,
                UserNotificationListenerAccessStatus,
            )
            self.listener = UserNotificationListener.current
            if not self.listener:
                return

            status = await self.listener.request_access_async()
            if status != UserNotificationListenerAccessStatus.ALLOWED:
                return
        except Exception:
            return

        known_ids = set()
        try:
            initial = await self.listener.get_notifications_async(0x1)
            for n in initial:
                known_ids.add(n.id)
        except Exception:
            pass

        while self._is_running:
            try:
                notifications = await self.listener.get_notifications_async(0x1)
                for n in notifications:
                    if n.id not in known_ids:
                        known_ids.add(n.id)
                        try:
                            app_name = n.app_info.display_info.display_name
                            bindings = n.notification.visual.bindings
                            title = ""
                            body = ""
                            for b in bindings:
                                text_elements = b.get_text_elements()
                                if len(text_elements) > 0:
                                    title = text_elements[0].text
                                if len(text_elements) > 1:
                                    body = text_elements[1].text
                            if title or body:
                                self.notification_received.emit(app_name, title, body)
                        except Exception:
                            pass
            except Exception:
                pass
            await asyncio.sleep(1.0)

    def stop(self):
        self._is_running = False
        self.wait(500)
