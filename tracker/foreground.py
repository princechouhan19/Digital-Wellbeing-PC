from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

import psutil
import threading
import win32gui
import win32process

from core.constants import AppCategory

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_dwmapi = None
try:
    _dwmapi = ctypes.WinDLL("dwmapi")
except Exception:
    pass

# Win32 API signatures
_kernel32.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
_kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
_kernel32.CloseHandle.restype = ctypes.wintypes.BOOL

_kernel32.QueryFullProcessImageNameW.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.DWORD,
    ctypes.wintypes.LPWSTR,
    ctypes.POINTER(ctypes.wintypes.DWORD)
]
_kernel32.QueryFullProcessImageNameW.restype = ctypes.wintypes.BOOL

GA_ROOTOWNER = 3
try:
    _user32.GetAncestor.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.UINT]
    _user32.GetAncestor.restype = ctypes.wintypes.HWND
except Exception:
    pass

DWMWA_CLOAKED = 14
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes.DWORD),
        ('cntUsage', ctypes.wintypes.DWORD),
        ('th32ProcessID', ctypes.wintypes.DWORD),
        ('th32DefaultHeapID', ctypes.POINTER(ctypes.c_ulong)),
        ('th32ModuleID', ctypes.wintypes.DWORD),
        ('cntThreads', ctypes.wintypes.DWORD),
        ('th32ParentProcessID', ctypes.wintypes.DWORD),
        ('pcPriClassBase', ctypes.c_long),
        ('dwFlags', ctypes.wintypes.DWORD),
        ('szExeFile', ctypes.c_wchar * 260)
    ]


class _MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ('dwSize', ctypes.wintypes.DWORD),
        ('th32ModuleID', ctypes.wintypes.DWORD),
        ('th32ProcessID', ctypes.wintypes.DWORD),
        ('GlblcntUsage', ctypes.wintypes.DWORD),
        ('ProccntUsage', ctypes.wintypes.DWORD),
        ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
        ('modBaseSize', ctypes.wintypes.DWORD),
        ('hModule', ctypes.wintypes.HMODULE),
        ('szModule', ctypes.c_wchar * 256),
        ('szExePath', ctypes.c_wchar * 260)
    ]


@dataclass(frozen=True)
class ForegroundApp:
    process_name: str
    exe_path: str
    pid: int
    window_title: str
    hwnd: int
    url: str = ""
    is_fullscreen: bool = False


# Canonical browser process registry (single source of truth).
# Includes Chromium forks, Firefox forks, and niche/privacy browsers.
BROWSER_PROCESSES = frozenset({
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "firefox.exe",
    "opera.exe",
    "operagx.exe",
    "vivaldi.exe",
    "arc.exe",
    "atlas.exe",
    "comet.exe",
    "zen.exe",
    "chromium.exe",
    "tor.exe",
    "waterfox.exe",
    "librewolf.exe",
    "palemoon.exe",
    "browser.exe",
    "sidekick.exe",
    "epic.exe",
    "duckduckgo.exe",
    "floorp.exe",
    "yandex.exe",
    "maxthon.exe",
})

OVERLAY_PROCESSES = {
    "gameoverlayui.exe",
    "discord.exe",
    "geforcenow.exe",
    "obs64.exe",
    "overwolf.exe",
}

_SYSTEM_IGNORED_PROCESSES = {
    "dwm.exe",
    "csrss.exe",
    "winlogon.exe",
    "smss.exe",
    "lockapp.exe",
    "digitalwellbeing.exe",
}

# LRU Cache mapping pid -> (process_name, exe_path, cache_timestamp)
_pid_info_cache: dict[int, tuple[str, str, float]] = {}
_last_valid_app: Optional[ForegroundApp] = None


def _is_window_cloaked(hwnd: int) -> bool:
    if not _dwmapi:
        return False
    try:
        cloaked = ctypes.wintypes.DWORD()
        res = _dwmapi.DwmGetWindowAttribute(
            hwnd,
            ctypes.wintypes.DWORD(DWMWA_CLOAKED),
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked)
        )
        return res == 0 and cloaked.value != 0
    except Exception:
        return False

def _is_generic_overlay(hwnd: int) -> bool:
    try:
        GWL_EXSTYLE = -20
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        
        exstyle = _user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        # If it's transparent to clicks (click-through overlay)
        if (exstyle & WS_EX_TRANSPARENT) != 0:
            return True
            
        # If it's a tool window that shouldn't activate
        if (exstyle & WS_EX_TOOLWINDOW) != 0 and (exstyle & WS_EX_NOACTIVATE) != 0:
            return True
            
        return False
    except Exception:
        return False


def _get_root_owner_window(hwnd: int) -> int:
    try:
        root = _user32.GetAncestor(hwnd, GA_ROOTOWNER)
        if root:
            return root
    except Exception:
        pass
    return hwnd


def _get_process_name_toolhelp(pid: int) -> Optional[str]:
    """Query system process table snapshot without creating process handles."""
    h_snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h_snap == -1 or not h_snap:
        return None
    try:
        pe = _PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        if _kernel32.Process32FirstW(h_snap, ctypes.byref(pe)):
            while True:
                if pe.th32ProcessID == pid:
                    return pe.szExeFile
                if not _kernel32.Process32NextW(h_snap, ctypes.byref(pe)):
                    break
    except Exception:
        pass
    finally:
        _kernel32.CloseHandle(h_snap)
    return None


def _get_exe_path_uncached(pid: int) -> str:
    # 1. Try via psutil
    try:
        proc = psutil.Process(pid)
        path = proc.exe()
        if path:
            return path
    except Exception:
        pass

    # 2. Fallback to Windows API OpenProcess & QueryFullProcessImageNameW
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_process = None
    try:
        h_process = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_process:
            size = ctypes.wintypes.DWORD(1024)
            buf = ctypes.create_unicode_buffer(size.value)
            if _kernel32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
                return buf.value
    except Exception:
        pass
    finally:
        if h_process:
            _kernel32.CloseHandle(h_process)

    # 3. Fallback to Toolhelp module snapshot
    try:
        h_snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
        if h_snap != -1 and h_snap:
            try:
                me = _MODULEENTRY32W()
                me.dwSize = ctypes.sizeof(_MODULEENTRY32W)
                if _kernel32.Module32FirstW(h_snap, ctypes.byref(me)):
                    return me.szExePath
            finally:
                _kernel32.CloseHandle(h_snap)
    except Exception:
        pass

    return ""


def _get_process_info(pid: int, hwnd: int = 0) -> tuple[str, str]:
    now = time.monotonic()
    if pid in _pid_info_cache:
        cached_name, cached_path, cached_time = _pid_info_cache[pid]
        # Valid for 5 minutes (300 seconds) if process still exists
        if now - cached_time < 300.0:
            if psutil.pid_exists(pid):
                return cached_name, cached_path
            else:
                _pid_info_cache.pop(pid, None)

    # 1. Try via psutil
    name = None
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except Exception:
        pass

    # 2. Toolhelp32 snapshot fallback (works across integrity levels & anti-cheat hooks)
    if not name:
        name = _get_process_name_toolhelp(pid)

    # 3. Try Window module filename
    if not name and hwnd:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            if _user32.GetWindowModuleFileNameW(hwnd, buf, 1024) > 0:
                name = os.path.basename(buf.value)
        except Exception:
            pass

    path = _get_exe_path_uncached(pid)

    # 4. Fallback name from full exe path
    if not name and path:
        name = os.path.basename(path)

    if name:
        # Evict cache if too large
        if len(_pid_info_cache) > 512:
            _pid_info_cache.clear()
        _pid_info_cache[pid] = (name, path, now)

    return name or "", path


def _get_process_name(pid: int, hwnd: int = 0) -> Optional[str]:
    name, _ = _get_process_info(pid, hwnd)
    return name or None


def _get_exe_path(pid: int) -> str:
    _, path = _get_process_info(pid)
    return path


def _get_real_window_pid(hwnd: int) -> int:
    try:
        tid, pid = win32process.GetWindowThreadProcessId(hwnd)
        name = _get_process_name(pid, hwnd=hwnd)
        if name and name.lower() == "applicationframehost.exe":
            # For UWP apps, search child windows for the real process
            real_pid = [pid]
            def enum_child(child_hwnd, lparam):
                child_tid, child_child_pid = win32process.GetWindowThreadProcessId(child_hwnd)
                child_name = _get_process_name(child_child_pid, hwnd=child_hwnd)
                if child_name and child_name.lower() != "applicationframehost.exe":
                    real_pid[0] = child_child_pid
                    return False  # stop enumeration
                return True
            try:
                win32gui.EnumChildWindows(hwnd, enum_child, None)
            except Exception:
                pass
            return real_pid[0]
        return pid
    except Exception:
        return 0


_PRIVATE_TITLE_REGEX = re.compile(
    r'(?:^|[\s:\-–—\(\[\{])(?:incognito|inprivate|private\s+browsing|private\s+window|private\s+tab|private|tor\s+browser)[\s\)\}\]]*$',
    re.IGNORECASE,
)


def is_private_browsing(process_name: str, window_title: str) -> bool:
    """Detect if the foreground window is an Incognito/Private browsing session."""
    if not process_name or not window_title:
        return False

    proc_lower = process_name.lower()

    if proc_lower == "tor.exe":
        return True

    if proc_lower not in BROWSER_PROCESSES and "browser" not in proc_lower:
        return False

    title_clean = window_title.strip()
    if not title_clean:
        return False

    return bool(_PRIVATE_TITLE_REGEX.search(title_clean))


def _try_recover_fullscreen_game(fallback: Optional[ForegroundApp]) -> Optional[ForegroundApp]:
    if fallback and fallback.pid > 4 and psutil.pid_exists(fallback.pid):
        from tracker.categorizer import categorize
        if categorize(fallback.process_name, fallback.exe_path) == AppCategory.GAMING:
            return fallback
    return None


def is_window_fullscreen(hwnd: int) -> bool:
    if not hwnd or hwnd <= 0:
        return False
    try:
        if not win32gui.IsWindowVisible(hwnd):
            return False
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        screen_w = _user32.GetSystemMetrics(0)  # SM_CXSCREEN
        screen_h = _user32.GetSystemMetrics(1)  # SM_CYSCREEN
        return width >= screen_w and height >= screen_h
    except Exception:
        return False


_thread_desktop_attached = threading.local()

def _ensure_interactive_desktop() -> None:
    if getattr(_thread_desktop_attached, "done", False):
        return
    try:
        h_desk = _user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if h_desk:
            _user32.SetThreadDesktop(h_desk)
            _thread_desktop_attached.done = True
    except Exception:
        pass


def get_foreground_app(last_known_app: Optional[ForegroundApp] = None) -> Optional[ForegroundApp]:
    global _last_valid_app
    _ensure_interactive_desktop()
    try:
        hwnd = win32gui.GetForegroundWindow()
        fallback = last_known_app or _last_valid_app

        if not hwnd or not win32gui.IsWindowVisible(hwnd) or _is_window_cloaked(hwnd) or _is_generic_overlay(hwnd):
            recovered = _try_recover_fullscreen_game(fallback)
            if recovered:
                return recovered
            return None

        root_hwnd = _get_root_owner_window(hwnd) or hwnd

        title: str = ""
        try:
            title = win32gui.GetWindowText(root_hwnd) or win32gui.GetWindowText(hwnd) or ""
        except Exception:
            pass

        pid = _get_real_window_pid(root_hwnd) or _get_real_window_pid(hwnd)
        if pid <= 4:
            recovered = _try_recover_fullscreen_game(fallback)
            if recovered:
                return recovered
            return None

        name = _get_process_name(pid, hwnd=root_hwnd)
        if name is None:
            recovered = _try_recover_fullscreen_game(fallback)
            if recovered:
                return recovered
            return None

        name_lower = name.lower()
        if name_lower in _SYSTEM_IGNORED_PROCESSES:
            recovered = _try_recover_fullscreen_game(fallback)
            if recovered:
                return recovered
            return None

        # Fallback window title if title is blank for a valid app window
        if not title.strip():
            from tracker.categorizer import display_name
            title = display_name(name)

        exe_path = _get_exe_path(pid)

        # Sanitize window title if the active window is an Incognito/Private browser session
        url = ""
        if is_private_browsing(name, title):
            title = "Private Browsing"
        else:
            try:
                from tracker.browser_domain import get_active_browser_domain
                url = get_active_browser_domain(name, title, hwnd=root_hwnd or hwnd)
            except Exception:
                url = ""

        # Safely detect fullscreen on the root window or the actual foreground window (e.g. video child window)
        is_fs = False
        try:
            is_fs = is_window_fullscreen(hwnd) or is_window_fullscreen(root_hwnd)
        except Exception:
            pass

        app = ForegroundApp(
            process_name=name,
            exe_path=exe_path,
            pid=pid,
            window_title=title[:512],
            hwnd=hwnd,
            url=url,
            is_fullscreen=is_fs,
        )
        _last_valid_app = app
        return app
    except Exception:
        return _try_recover_fullscreen_game(last_known_app or _last_valid_app)


def apps_are_same(
    a: Optional[ForegroundApp],
    b: Optional[ForegroundApp],
    category: Optional[AppCategory] = None,
) -> bool:
    """Check if two foreground app states represent the same application.

    For gaming apps, only process_name is compared because games frequently
    change their window title during gameplay (loading screens, round changes,
    etc.), which should not trigger session splits.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if a.process_name != b.process_name:
        return False
    # For games, process_name match is sufficient — skip title comparison
    if category == AppCategory.GAMING:
        return True
    return a.window_title == b.window_title and a.url == b.url
