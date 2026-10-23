"""
tests/conftest.py — Cross-platform test bootstrap.

On non-Windows hosts (Linux CI / sandbox validation), Windows-only extension
modules are stubbed with permissive mocks so UI, protection, and analytics
modules can be imported. On Windows the real modules load and this file does
nothing. Tracking behavior itself is never exercised through these stubs —
they exist purely to satisfy import-time dependencies.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DW_TEST_MODE", "1")


def _try_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


if not _try_import("win32gui") and os.name != "nt":

    def _stub(name: str, **attrs):
        mod = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(mod, k, v)
        sys.modules[name] = mod
        return mod

    class _Any:
        def __init__(self, *a, **k):
            pass

        def __call__(self, *a, **k):
            return _Any()

        def __getattr__(self, n):
            return _Any()

        def __or__(self, o):
            return self

        def __enter__(self):
            return _Any()

        def __exit__(self, *a):
            return False

        def __iter__(self):
            return iter([])

        def __bool__(self):
            return False

        def __int__(self):
            return 0

        def __float__(self):
            return 0.0

    _stub("win32gui", **{n: _Any() for n in [
        "GetForegroundWindow", "EnumWindows", "IsWindow", "IsWindowVisible",
        "ShowWindow", "SetForegroundWindow", "BringWindowToTop",
        "GetWindowThreadProcessId", "GetWindowText", "GetClassName",
        "GetWindowRect", "GetWindowLong", "SetWindowLong",
        "EnumChildWindows", "GetWindowTextLength", "GetLastActivePopup",
    ]})

    # ctypes.WinDLL / wintypes so Linux can import win32-dependent modules
    import ctypes
    if not hasattr(ctypes, "WinDLL"):
        class _FakeDLL(_Any):
            def __init__(self, *a, **k):
                super().__init__()
        ctypes.WinDLL = _FakeDLL
        ctypes.WINDLL = type("WINDLL", (), {"__getattr__": staticmethod(lambda n: _Any())})
        ctypes.oledll = type("oledll", (), {"__getattr__": staticmethod(lambda n: _Any())})

    if not hasattr(ctypes, "wintypes"):
        import ctypes as _c

        class _RECT(_c.Structure):
            _fields_ = [("left", _c.c_long), ("top", _c.c_long), ("right", _c.c_long), ("bottom", _c.c_long)]

        wt = _stub(
            "ctypes.wintypes",
            DWORD=_c.c_uint32, BOOL=_c.c_int, HWND=_c.c_void_p, WORD=_c.c_uint16,
            HANDLE=_c.c_void_p, LPWSTR=_c.c_wchar_p, LPCWSTR=_c.c_wchar_p,
            UINT=_c.c_uint, ULONG=_c.c_ulong, LPARAM=_c.c_ssize_t, WPARAM=_c.c_size_t,
            LRESULT=_c.c_ssize_t, LONG=_c.c_long, BYTE=_c.c_byte, CHAR=_c.c_char,
            RECT=_RECT, LPVOID=_c.c_void_p, LPCVOID=_c.c_void_p, INT=_c.c_int,
            FLOAT=_c.c_float, DOUBLE=_c.c_double, LCID=_c.c_ulong, LANGID=_c.c_uint16,
            ATOM=_c.c_uint16, COLORREF=_c.c_ulong, PBYTE=_c.POINTER(_c.c_ubyte),
            HGDIOBJ=_c.c_void_p, HBRUSH=_c.c_void_p, HBITMAP=_c.c_void_p,
            HICON=_c.c_void_p, HCURSOR=_c.c_void_p, HMENU=_c.c_void_p,
            HACCEL=_c.c_void_p, HHOOK=_c.c_void_p, HMODULE=_c.c_void_p,
            HKEY=_c.c_void_p, HDC=_c.c_void_p, HINSTANCE=_c.c_void_p,
            DWORDPTR=_c.POINTER(_c.c_uint32), ULONGPTR=_c.POINTER(_c.c_ulong),
        )
        ctypes.wintypes = wt

    _stub("win32api", **{n: _Any() for n in ["GetLastError", "keybd_event"]})
    _stub("win32process", **{n: _Any() for n in [
        "GetWindowThreadProcessId", "OpenProcess",
        "QueryFullProcessImageNameW", "GetModuleFileNameExW",
    ]})
    _stub("win32con", **{n: _Any() for n in ["SW_HIDE", "SW_MINIMIZE", "SW_RESTORE", "VK_CONTROL", "VK_W"]})
    _stub("win32ts", **{n: _Any() for n in [
        "WTSRegisterSessionNotification", "WTSUnRegisterSessionNotification",
        "NOTIFY_FOR_THIS_SESSION",
    ]})
    _stub("win32com")
    _stub("win32com.propsys")
    _stub("win32com.shell")
    _stub("win32event", **{n: _Any() for n in ["CreateEvent", "SetEvent", "WAIT_TIMEOUT"]})
    _stub("winreg", **{n: _Any() for n in [
        "OpenKey", "QueryValueEx", "CloseKey", "HKEY_CURRENT_USER",
        "CreateKey", "SetValueEx", "DeleteValue",
    ]})
    _stub("winrt")
    _stub("winrt.windows")
    _stub("winrt.windows.foundation")
    _stub("winrt.windows.ui")
    _stub("winrt.windows.ui.notifications")
    _stub("winrt.windows.data")
    _stub("winrt.windows.data.xml")
    _stub("winrt.windows.data.xml.dom")
    _stub("winrt.windows.security")
    _stub("winrt.windows.security.credentials")
    _stub("winrt.windows.security.credentials.ui", **{
        "UserConsentVerifier": _Any(), "UserConsentVerificationResult": _Any(),
    })
    _stub("uiautomation", **{n: _Any() for n in [
        "GetRootControl", "ControlFromHandle", "WalkControl",
    ]})
    _stub("xinput", **{"XInputGetState": _Any()})

    # subprocess.CREATE_NO_WINDOW is Windows-only; tests reference it directly
    import subprocess as _sp
    if not hasattr(_sp, "CREATE_NO_WINDOW"):
        _sp.CREATE_NO_WINDOW = 0x08000000

    # colorama is imported unconditionally by pyqtgraph's cprint
    import enum as _enum
    _stub("colorama")
    _stub("colorama.win32", windll=_Any(), COORD=None)
    _cwm = _stub("colorama.winterm", enable_vt_processing=_Any(), WinTerm=_Any, WinColor=_Any, WinStyle=_Any)
    _cwm.WinColor = _enum.Enum(
        "WinColor",
        "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE GREY GREY_BRIGHT "
        "RED_BRIGHT GREEN_BRIGHT YELLOW_BRIGHT BLUE_BRIGHT MAGENTA_BRIGHT "
        "CYAN_BRIGHT WHITE_BRIGHT",
        start=0,
    )
    _cwm.WinStyle = _enum.Enum("WinStyle", "NORMAL BRIGHT DIM", start=0)
    _stub("colorama.ansitowin32", AnsiToWin32=_Any)
