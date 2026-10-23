from __future__ import annotations

import ctypes
import ctypes.wintypes
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from core.constants import AppCategory


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint),
    ]


class _XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", ctypes.c_ushort),
        ("bLeftTrigger", ctypes.c_ubyte),
        ("bRightTrigger", ctypes.c_ubyte),
        ("sThumbLX", ctypes.c_short),
        ("sThumbLY", ctypes.c_short),
        ("sThumbRX", ctypes.c_short),
        ("sThumbRY", ctypes.c_short),
    ]


class _XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", ctypes.wintypes.DWORD),
        ("Gamepad", _XINPUT_GAMEPAD),
    ]


class _JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("dwXpos", ctypes.wintypes.DWORD),
        ("dwYpos", ctypes.wintypes.DWORD),
        ("dwZpos", ctypes.wintypes.DWORD),
        ("dwRpos", ctypes.wintypes.DWORD),
        ("dwUpos", ctypes.wintypes.DWORD),
        ("dwVpos", ctypes.wintypes.DWORD),
        ("dwButtons", ctypes.wintypes.DWORD),
        ("dwButtonNumber", ctypes.wintypes.DWORD),
        ("dwPOV", ctypes.wintypes.DWORD),
        ("dwReserved1", ctypes.wintypes.DWORD),
        ("dwReserved2", ctypes.wintypes.DWORD),
    ]


_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_user32.GetLastInputInfo.argtypes = [ctypes.c_void_p]
_user32.GetLastInputInfo.restype = ctypes.wintypes.BOOL
_kernel32.GetTickCount.argtypes = []
_kernel32.GetTickCount.restype = ctypes.wintypes.DWORD

_LASTINPUTINFO_SIZE = ctypes.sizeof(_LASTINPUTINFO)
_TICK_MAX = 0xFFFFFFFF

# Load XInput DLL (try 1.4 -> 9.1.0 -> 1.3)
_xinput = None
for _dll_name in ("xinput1_4.dll", "xinput9_1_0.dll", "xinput1_3.dll"):
    try:
        _xinput = ctypes.WinDLL(_dll_name)
        _xinput.XInputGetState.argtypes = [ctypes.wintypes.DWORD, ctypes.POINTER(_XINPUT_STATE)]
        _xinput.XInputGetState.restype = ctypes.wintypes.DWORD
        break
    except Exception:
        pass

# Load WinMM DLL for joystick fallback
_winmm = None
try:
    _winmm = ctypes.WinDLL("winmm.dll")
    _winmm.joyGetPosEx.argtypes = [ctypes.c_uint, ctypes.POINTER(_JOYINFOEX)]
    _winmm.joyGetPosEx.restype = ctypes.c_uint
except Exception:
    pass

JOY_RETURNALL = 0x000000FF

# Standard XInput deadzones
XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE = 7849
XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE = 8689
XINPUT_GAMEPAD_TRIGGER_THRESHOLD = 30

_last_xinput_states: list[Optional[tuple[int, int, int, int, int, int, int]]] = [None] * 4
_last_joy_states: list[Optional[tuple[int, int, int, int, int, int]]] = [None] * 2
_last_controller_activity_tick: int = 0

# XInput/joyGetPosEx are cheap native calls but they cross the Win32 boundary
# six times per sample. Sampling them at 2 s is far below perceptible input
# latency (SleepGuard thresholds are minutes) and cuts their cost by ~2x.
_CONTROLLER_PROBE_INTERVAL_S = 2.0
_last_controller_probe_mono: float = 0.0


def _check_controller_activity(tick_now: int) -> None:
    """Throttled wrapper around the XInput / WinMM controller probe."""
    global _last_controller_probe_mono
    now = time.monotonic()
    if (
        _last_controller_probe_mono > 0.0
        and (now - _last_controller_probe_mono) < _CONTROLLER_PROBE_INTERVAL_S
    ):
        return
    _last_controller_probe_mono = now
    _poll_controllers(tick_now)


def _poll_controllers(tick_now: int) -> None:
    global _last_controller_activity_tick

    # 1. Check XInput Gamepads (ports 0..3)
    if _xinput is not None:
        for i in range(4):
            state = _XINPUT_STATE()
            if _xinput.XInputGetState(i, ctypes.byref(state)) == 0:
                gp = state.Gamepad
                # Check for active buttons, triggers, or sticks outside deadzones
                buttons = gp.wButtons
                lt = gp.bLeftTrigger
                rt = gp.bRightTrigger
                lx = gp.sThumbLX if abs(gp.sThumbLX) > XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE else 0
                ly = gp.sThumbLY if abs(gp.sThumbLY) > XINPUT_GAMEPAD_LEFT_THUMB_DEADZONE else 0
                rx = gp.sThumbRX if abs(gp.sThumbRX) > XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE else 0
                ry = gp.sThumbRY if abs(gp.sThumbRY) > XINPUT_GAMEPAD_RIGHT_THUMB_DEADZONE else 0
                
                curr_state = (buttons, lt > XINPUT_GAMEPAD_TRIGGER_THRESHOLD, rt > XINPUT_GAMEPAD_TRIGGER_THRESHOLD,
                              lx >> 11, ly >> 11, rx >> 11, ry >> 11)
                prev_state = _last_xinput_states[i]
                _last_xinput_states[i] = curr_state

                # Only genuine input changes outside deadzones count as activity
                if prev_state is not None and curr_state != prev_state:
                    if buttons != 0 or lt > XINPUT_GAMEPAD_TRIGGER_THRESHOLD or rt > XINPUT_GAMEPAD_TRIGGER_THRESHOLD or lx or ly or rx or ry:
                        _last_controller_activity_tick = tick_now
            else:
                _last_xinput_states[i] = None

    # 2. Check WinMM Joysticks (ports 0..1)
    if _winmm is not None:
        for j in range(2):
            ji = _JOYINFOEX()
            ji.dwSize = ctypes.sizeof(_JOYINFOEX)
            ji.dwFlags = JOY_RETURNALL
            if _winmm.joyGetPosEx(j, ctypes.byref(ji)) == 0:
                state_tuple = (
                    ji.dwXpos >> 11,
                    ji.dwYpos >> 11,
                    ji.dwZpos >> 11,
                    ji.dwRpos >> 11,
                    ji.dwButtons,
                    ji.dwPOV,
                )
                prev_state = _last_joy_states[j]
                _last_joy_states[j] = state_tuple
                if prev_state is not None and state_tuple != prev_state:
                    if ji.dwButtons != 0 or any(abs((s << 11) - 32767) > 8000 for s in state_tuple[:4]):
                        _last_controller_activity_tick = tick_now
            else:
                _last_joy_states[j] = None


def _elapsed_ms(tick_now: int, last_input: int) -> int:
    if tick_now >= last_input:
        return tick_now - last_input
    return (_TICK_MAX - last_input) + tick_now + 1


def get_last_input_tick() -> int:
    """Return the raw Windows GetLastInputInfo tick count directly."""
    try:
        from tracker.foreground import _ensure_interactive_desktop
        _ensure_interactive_desktop()
    except Exception:
        pass
    lii = _LASTINPUTINFO()
    lii.cbSize = _LASTINPUTINFO_SIZE
    if _user32.GetLastInputInfo(ctypes.byref(lii)):
        return int(lii.dwTime)
    return int(_kernel32.GetTickCount())


def get_idle_seconds(strict_user_input: bool = False) -> float:
    try:
        from tracker.foreground import _ensure_interactive_desktop
        _ensure_interactive_desktop()
    except Exception:
        pass
    lii = _LASTINPUTINFO()
    lii.cbSize = _LASTINPUTINFO_SIZE
    has_lii = _user32.GetLastInputInfo(ctypes.byref(lii))

    tick_now: int = _kernel32.GetTickCount()
    last_win32: int = lii.dwTime if has_lii else tick_now
    elapsed_win32 = _elapsed_ms(tick_now, last_win32)

    if strict_user_input:
        return max(0.0, elapsed_win32 / 1000.0)

    _check_controller_activity(tick_now)
    elapsed_ctrl = (
        _elapsed_ms(tick_now, _last_controller_activity_tick)
        if _last_controller_activity_tick > 0
        else elapsed_win32
    )

    elapsed_ms = min(elapsed_win32, elapsed_ctrl)
    return max(0.0, elapsed_ms / 1000.0)


def is_idle(
    threshold_s: float,
    current_category: Optional["AppCategory"] = None,
    is_media_playing: bool = False,
    mode: str = "smart",
    media_timeout_s: Optional[float] = None,
) -> bool:
    """Return True when the user has been input-idle for at least *threshold_s* seconds."""
    idle_s = get_idle_seconds()

    if is_media_playing:
        if mode == "media":
            return False
        if mode == "smart" and media_timeout_s is not None:
            return idle_s >= media_timeout_s

    if current_category is not None:
        try:
            from core.constants import AppCategory as _Cat
            if current_category == _Cat.GAMING:
                return idle_s >= threshold_s * 2.5
            if current_category == _Cat.ENTERTAINMENT and is_media_playing:
                return idle_s >= threshold_s * 3.0
        except Exception:
            pass

    return idle_s >= threshold_s

