"""
win_events.py — Event-driven Win32 foreground/title notifications.

The tracker historically asked Windows "which window is in front?" twice a
second. ``SetWinEventHook`` lets Windows push that answer instead, so the
tracking thread can sleep until something actually changes.

Design notes:
* ``WINEVENT_OUTOFCONTEXT`` delivers callbacks on a dedicated message-pump
  thread owned by this module; the callback must return quickly.
* Two hooks are installed (foreground + title change) rather than one wide
  range, because a range such as 0x0003..0x800C would deliver a large volume of
  unrelated accessibility events.
* Events coalesce into a single ``threading.Event``: if five tab switches occur
  before the tracker wakes, it only needs to re-read the foreground window once.
* Everything degrades gracefully: on non-Windows hosts, when hooks cannot be
  installed, or when ``DW_DISABLE_WINEVENT_HOOK=1`` is set, ``available`` stays
  False and the tracker falls back to bounded polling.
"""
from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from typing import Optional

_EVENT_SYSTEM_FOREGROUND = 0x0003
_EVENT_OBJECT_NAMECHANGE = 0x800C
_OBJID_WINDOW = 0
_WINEVENT_OUTOFCONTEXT = 0x0000
_WINEVENT_SKIPOWNPROCESS = 0x0002
_WM_QUIT = 0x0012
_GA_ROOT = 2

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _WINEVENTPROC = ctypes.WINFUNCTYPE(
        None,
        wintypes.HANDLE,   # HWINEVENTHOOK
        wintypes.DWORD,    # event
        wintypes.HWND,     # hwnd
        wintypes.LONG,     # idObject
        wintypes.LONG,     # idChild
        wintypes.DWORD,    # idEventThread
        wintypes.DWORD,    # dwmsEventTime
    )

    _user32.SetWinEventHook.argtypes = [
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HMODULE,
        _WINEVENTPROC,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
    ]
    _user32.SetWinEventHook.restype = wintypes.HANDLE
    _user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
    _user32.UnhookWinEvent.restype = wintypes.BOOL
    _user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.PeekMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT
    ]
    _user32.PeekMessageW.restype = wintypes.BOOL
    _user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.TranslateMessage.restype = wintypes.BOOL
    _user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    _user32.DispatchMessageW.restype = ctypes.c_ssize_t
    _user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.PostThreadMessageW.restype = wintypes.BOOL
    _user32.GetForegroundWindow.argtypes = []
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    _user32.GetAncestor.restype = wintypes.HWND
    _kernel32.GetCurrentThreadId.argtypes = []
    _kernel32.GetCurrentThreadId.restype = wintypes.DWORD
else:  # pragma: no cover - exercised on non-Windows CI
    _user32 = None
    _kernel32 = None
    _WINEVENTPROC = None


def _log():
    try:
        from core.logger import logger

        return logger
    except Exception:  # pragma: no cover - logger always present in app
        import logging

        return logging.getLogger(__name__)


class ForegroundEventWatcher:
    """Push-based notification source for foreground/title changes.

    Public API:
        start() -> bool       install hooks on a message-pump thread
        stop()                unhook and join the thread
        wait(timeout) -> bool wake the caller when an event (or timeout) fires
        available             True when at least one hook is installed
    """

    _NAME_THROTTLE_S = 0.20

    def __init__(self) -> None:
        self._event_cond = threading.Condition()
        self._state_lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: int = 0
        self._hooks: list = []
        self._callback = None
        self._ready = threading.Event()
        self._running = False
        self._available = False
        self._generation = 0
        self._seen_generation = 0
        self._event_count = 0
        self._last_reason = ""
        self._last_name_notify = 0.0

    # ─── Public API ─────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        return self._available

    @property
    def event_count(self) -> int:
        return self._event_count

    def start(self) -> bool:
        """Install the hooks. Safe to call repeatedly; returns availability."""
        if not _IS_WINDOWS or _WINEVENTPROC is None:
            return False
        if os.environ.get("DW_DISABLE_WINEVENT_HOOK") == "1":
            _log().info("[WINEVENTS] Disabled via DW_DISABLE_WINEVENT_HOOK")
            return False
        with self._state_lock:
            if self._running:
                return self._available
            self._running = True
            self._ready.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="ForegroundEventWatcher",
            daemon=True,
        )
        self._thread.start()
        self._ready.wait(timeout=2.0)
        if not self._available:
            _log().warning("[WINEVENTS] SetWinEventHook unavailable; tracker will poll.")
        else:
            _log().info("[WINEVENTS] Foreground/title hooks installed (events=%d).", self._event_count)
        return self._available

    def stop(self) -> None:
        with self._state_lock:
            self._running = False
            thread = self._thread
            thread_id = self._thread_id
        if thread_id:
            try:
                _user32.PostThreadMessageW(thread_id, _WM_QUIT, 0, 0)
            except Exception:
                pass
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self._available = False
        # Wake any tracking loop blocked in wait() so shutdown is immediate.
        with self._event_cond:
            self._event_cond.notify_all()

    def wait(self, timeout: float) -> bool:
        """Block until a new event arrives or ``timeout`` elapses.

        Uses a generation counter rather than a plain Event so an event that
        arrives just before this call is never cleared away ("lost wakeup").
        Only one consumer (the tracking loop) is expected.
        """
        with self._event_cond:
            if self._generation != self._seen_generation:
                self._seen_generation = self._generation
                return True
            self._event_cond.wait(timeout)
            signalled = self._generation != self._seen_generation
            self._seen_generation = self._generation
            return signalled

    def notify(self, reason: str = "manual") -> None:
        """Inject a notification (used by tests and fallback triggers)."""
        with self._event_cond:
            self._generation += 1
            self._event_count += 1
            self._last_reason = reason
            self._event_cond.notify_all()

    @property
    def last_reason(self) -> str:
        return self._last_reason

    @property
    def generation(self) -> int:
        return self._generation

    # ─── Message-pump thread ────────────────────────────────────────────────

    def _run(self) -> None:
        hooks: list = []
        msg = wintypes.MSG()
        try:
            self._thread_id = int(_kernel32.GetCurrentThreadId())
            # Force creation of the thread message queue before publishing the
            # thread id, so stop()'s PostThreadMessage can never be dropped.
            _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

            self._callback = _WINEVENTPROC(self._on_event)
            # Foreground events from our own process must still wake the
            # tracker (our windows are ignored, so the previous app's session
            # ends promptly). Title events from our own UI are pure noise.
            foreground_hook = _user32.SetWinEventHook(
                _EVENT_SYSTEM_FOREGROUND,
                _EVENT_SYSTEM_FOREGROUND,
                None,
                self._callback,
                0,
                0,
                _WINEVENT_OUTOFCONTEXT,
            )
            title_hook = _user32.SetWinEventHook(
                _EVENT_OBJECT_NAMECHANGE,
                _EVENT_OBJECT_NAMECHANGE,
                None,
                self._callback,
                0,
                0,
                _WINEVENT_OUTOFCONTEXT | _WINEVENT_SKIPOWNPROCESS,
            )
            hooks = [h for h in (foreground_hook, title_hook) if h]
            self._hooks = hooks
            if not hooks:
                return
            self._available = True
            self._ready.set()

            while self._running:
                result = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result <= 0:  # WM_QUIT or error
                    break
                _user32.TranslateMessage(ctypes.byref(msg))
                _user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as exc:  # pragma: no cover - defensive
            _log().warning("[WINEVENTS] Message pump failed: %s", exc)
        finally:
            for hook in hooks:
                try:
                    _user32.UnhookWinEvent(hook)
                except Exception:
                    pass
            self._hooks = []
            self._available = False
            self._running = False
            self._ready.set()

    def _on_event(self, hook, event, hwnd, id_object, id_child, event_thread, event_time) -> None:
        """Win32 callback. Must be fast and must never raise."""
        try:
            if event == _EVENT_OBJECT_NAMECHANGE:
                if id_object != _OBJID_WINDOW or not hwnd:
                    return
                # Only title changes of the foreground window can affect
                # tracking. This filters out background apps that constantly
                # rewrite their captions (terminals, media players, ...).
                foreground = _user32.GetForegroundWindow()
                if not foreground:
                    return
                if hwnd != foreground and _user32.GetAncestor(hwnd, _GA_ROOT) != foreground:
                    return
                now = time.monotonic()
                if now - self._last_name_notify < self._NAME_THROTTLE_S:
                    return
                self._last_name_notify = now
                self.notify("title")
            elif event == _EVENT_SYSTEM_FOREGROUND:
                self.notify("foreground")
        except Exception:
            # A failing callback would be called on every system event; never
            # let an exception escape into the Win32 dispatcher.
            return
