from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
from enum import Enum, auto
from typing import Callable, Optional

import win32con
import win32gui


class SessionEvent(Enum):
    LOCK = auto()
    UNLOCK = auto()
    SLEEP = auto()
    RESUME = auto()
    LOGOFF = auto()
    SHUTDOWN = auto()


WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
WTS_SESSION_LOGOFF = 0x6
WTS_REMOTE_DISCONNECT = 0x4
WTS_REMOTE_CONNECT = 0x3

PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMPOWERSTATUSCHANGE = 0x000A

WM_WTSSESSION_CHANGE = 0x02B1
WM_POWERBROADCAST = 0x0218
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016

NOTIFY_FOR_THIS_SESSION = 0
_CLASS_NAME = "DWSessionMonitor_v2"


class SessionMonitor:
    def __init__(self, callback: Callable[[SessionEvent], None]) -> None:
        self._callback = callback
        self._hwnd: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._wts_registered = False

    def start(self) -> None:
        from core.logger import logger
        logger.info("[LIFECYCLE] SessionMonitor.start() creating thread")
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="SessionMonitor",
        )
        self._thread.start()
        logger.info("[LIFECYCLE] SessionMonitor thread started (ident=%s, daemon=%s)", self._thread.ident, self._thread.daemon)
        self._ready.wait(timeout=5.0)

    def stop(self) -> None:
        from core.logger import logger
        logger.info("[LIFECYCLE] SessionMonitor.stop() posting WM_QUIT to hwnd %s", self._hwnd)
        if self._hwnd:
            try:
                win32gui.PostMessage(self._hwnd, win32con.WM_QUIT, 0, 0)
            except Exception as exc:
                logger.warning("[LIFECYCLE] SessionMonitor.stop() PostMessage failed: %s", exc)

        # Wait for the Win32 message loop thread to exit so WTSUnregister
        # and DestroyWindow have completed before the process continues shutdown.
        if self._thread is not None and self._thread.is_alive():
            logger.info("[LIFECYCLE] Waiting for SessionMonitor thread (ident=%s) to exit...", self._thread.ident)
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                logger.warning("[LIFECYCLE] SessionMonitor thread did not exit within 5 seconds.")
            else:
                logger.info("[LIFECYCLE] SessionMonitor thread exited cleanly.")
        self._thread = None

    def _run(self) -> None:
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = _CLASS_NAME
        wc.lpfnWndProc = self._wnd_proc
        wc.hInstance = win32gui.GetModuleHandle(None)

        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        try:
            self._hwnd = win32gui.CreateWindow(
                _CLASS_NAME,
                "DW Session Monitor",
                0, 0, 0, 0, 0,
                0, 0, None, None,
            )
        except Exception as exc:
            from core.logger import logger
            logger.error("SessionMonitor: CreateWindow failed: %s", exc)
            self._ready.set()
            return

        try:
            import win32ts
            win32ts.WTSRegisterSessionNotification(self._hwnd, NOTIFY_FOR_THIS_SESSION)
            self._wts_registered = True
        except Exception as exc:
            from core.logger import logger
            logger.warning("SessionMonitor: WTSRegisterSessionNotification failed: %s", exc)

        self._ready.set()

        try:
            win32gui.PumpMessages()
        finally:
            if self._wts_registered and self._hwnd:
                try:
                    import win32ts
                    win32ts.WTSUnRegisterSessionNotification(self._hwnd)
                except Exception:
                    pass
            if self._hwnd:
                try:
                    win32gui.DestroyWindow(self._hwnd)
                except Exception:
                    pass

    def _fire(self, event: SessionEvent) -> None:
        try:
            self._callback(event)
        except Exception as exc:
            from core.logger import logger
            logger.error("SessionMonitor callback error: %s", exc)

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK:
                self._fire(SessionEvent.LOCK)
            elif wparam == WTS_SESSION_UNLOCK:
                self._fire(SessionEvent.UNLOCK)
            elif wparam == WTS_SESSION_LOGOFF:
                self._fire(SessionEvent.LOGOFF)
            elif wparam == WTS_REMOTE_DISCONNECT:
                self._fire(SessionEvent.LOCK)
            elif wparam == WTS_REMOTE_CONNECT:
                self._fire(SessionEvent.UNLOCK)

        elif msg == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                self._fire(SessionEvent.SLEEP)
            elif wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                self._fire(SessionEvent.RESUME)

        elif msg == WM_QUERYENDSESSION:
            self._fire(SessionEvent.SHUTDOWN)
            return 1

        elif msg == WM_ENDSESSION:
            if wparam:
                self._fire(SessionEvent.SHUTDOWN)

        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
