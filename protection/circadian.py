"""
circadian.py — Evening display warm-up linked to the SleepGuard bedtime.

Uses Win32 gamma ramps (`GetDeviceGammaRamp` / `SetDeviceGammaRamp`) rather than
the undocumented Windows Night Light registry blob. The original ramp of every
active display is captured first, so disabling the feature (or exiting the app)
restores the display exactly.

Schedule:
    daytime ........................ 6500 K
    bedtime - lead_minutes .......... interpolate 6500 K -> target
    bedtime window .................. target (default 3400 K)
    wake / daytime ................. 6500 K
"""
from __future__ import annotations

import atexit
import ctypes
import ctypes.wintypes
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QTimer, Signal

from core.logger import logger

DAY_KELVIN = 6500
_MIN_KELVIN = 1800
_MAX_KELVIN = 6500
_DISPLAY_DEVICE_ACTIVE = 0x00000001
_DISPLAY_DEVICE_MIRRORING_DRIVER = 0x00000008


# ── Colour maths ─────────────────────────────────────────────────────────────


def kelvin_to_rgb(kelvin: float) -> Tuple[float, float, float]:
    """Approximate blackbody colour for a Kelvin temperature (0–255 channels)."""
    kelvin = max(_MIN_KELVIN, min(_MAX_KELVIN, float(kelvin)))
    temp = kelvin / 100.0
    if temp <= 66:
        red = 255.0
        green = 99.4708025861 * math.log(temp) - 161.1195681661
        blue = 0.0 if temp <= 19 else 138.5177312231 * math.log(temp - 10) - 305.0447927307
    else:
        red = 329.698727446 * ((temp - 60) ** -0.1332047592)
        green = 288.1221695283 * ((temp - 60) ** -0.0755148492)
        blue = 255.0
    return (
        max(0.0, min(255.0, red)),
        max(0.0, min(255.0, green)),
        max(0.0, min(255.0, blue)),
    )


def warmth_factors(kelvin: float) -> Tuple[float, float, float]:
    """Per-channel multipliers normalised so the strongest channel stays 1.0."""
    red, green, blue = kelvin_to_rgb(kelvin)
    peak = max(red, green, blue, 1.0)
    return red / peak, green / peak, blue / peak


def interpolate_kelvin(fraction: float, target_kelvin: float) -> int:
    fraction = max(0.0, min(1.0, fraction))
    return int(round(DAY_KELVIN + (target_kelvin - DAY_KELVIN) * fraction))


# ── Win32 gamma ramp ────────────────────────────────────────────────────────


def _parse_hhmm(value: str, fallback: str) -> time:
    try:
        hour, minute = value.strip().split(":")[:2]
        return time(int(hour), int(minute))
    except Exception:
        hour, minute = fallback.split(":")
        return time(int(hour), int(minute))


class _DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.wintypes.DWORD),
        ("DeviceName", ctypes.c_wchar * 32),
        ("DeviceString", ctypes.c_wchar * 128),
        ("StateFlags", ctypes.wintypes.DWORD),
        ("DeviceID", ctypes.c_wchar * 128),
        ("DeviceKey", ctypes.c_wchar * 128),
    ]


class GammaRampController:
    """Captures and restores per-monitor gamma ramps on Windows."""

    def __init__(self) -> None:
        self._available = sys.platform == "win32"
        self._originals: Dict[str, object] = {}
        self._applied_kelvin: Optional[int] = None
        self._user32 = None
        self._gdi32 = None
        if self._available:
            try:
                self._user32 = ctypes.WinDLL("user32", use_last_error=True)
                self._gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
                self._user32.EnumDisplayDevicesW.argtypes = [
                    ctypes.wintypes.LPCWSTR,
                    ctypes.wintypes.DWORD,
                    ctypes.POINTER(_DISPLAY_DEVICEW),
                    ctypes.wintypes.DWORD,
                ]
                self._user32.EnumDisplayDevicesW.restype = ctypes.wintypes.BOOL
                self._gdi32.CreateDCW.argtypes = [
                    ctypes.wintypes.LPCWSTR,
                    ctypes.wintypes.LPCWSTR,
                    ctypes.wintypes.LPCWSTR,
                    ctypes.c_void_p,
                ]
                self._gdi32.CreateDCW.restype = ctypes.wintypes.HDC
                self._gdi32.DeleteDC.argtypes = [ctypes.wintypes.HDC]
                self._gdi32.GetDeviceGammaRamp.argtypes = [ctypes.wintypes.HDC, ctypes.c_void_p]
                self._gdi32.SetDeviceGammaRamp.argtypes = [ctypes.wintypes.HDC, ctypes.c_void_p]
            except Exception as exc:
                logger.debug("[CIRCADIAN] Gamma API unavailable: %s", exc)
                self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def _devices(self) -> List[str]:
        names: List[str] = []
        if not self._available or self._user32 is None:
            return names
        index = 0
        while True:
            device = _DISPLAY_DEVICEW()
            device.cb = ctypes.sizeof(_DISPLAY_DEVICEW)
            if not self._user32.EnumDisplayDevicesW(None, index, ctypes.byref(device), 0):
                break
            index += 1
            flags = device.StateFlags
            if not (flags & _DISPLAY_DEVICE_ACTIVE):
                continue
            if flags & _DISPLAY_DEVICE_MIRRORING_DRIVER:
                continue
            names.append(device.DeviceName)
        return names

    @staticmethod
    def _ramp_buffer():
        # 3 channels × 256 WORD entries.
        return (ctypes.wintypes.WORD * (3 * 256))()

    def _get_ramp(self, hdc) -> Optional[object]:
        ramp = self._ramp_buffer()
        if self._gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(ramp)):
            return ramp
        return None

    def _set_ramp(self, hdc, ramp) -> bool:
        return bool(self._gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp)))

    def apply_kelvin(self, kelvin: int) -> bool:
        """Warm all active displays; returns True if at least one succeeded."""
        if not self._available or self._user32 is None or self._gdi32 is None:
            return False
        if self._applied_kelvin == kelvin:
            return True

        red_f, green_f, blue_f = warmth_factors(kelvin)
        applied = False
        for name in self._devices():
            hdc = self._gdi32.CreateDCW(name, None, None, None)
            if not hdc:
                continue
            try:
                if name not in self._originals:
                    original = self._get_ramp(hdc)
                    if original is None:
                        continue
                    self._originals[name] = original
                original = self._originals[name]
                ramp = self._ramp_buffer()
                factors = (red_f, green_f, blue_f)
                for channel in range(3):
                    factor = factors[channel]
                    base = channel * 256
                    for index in range(256):
                        value = int(original[base + index] * factor)
                        ramp[base + index] = max(0, min(65535, value))
                if self._set_ramp(hdc, ramp):
                    applied = True
            finally:
                self._gdi32.DeleteDC(hdc)

        if applied:
            self._applied_kelvin = kelvin
            logger.debug("[CIRCADIAN] Applied %dK to %d display(s)", kelvin, len(self._devices()))
        return applied

    def restore(self) -> None:
        if not self._available or self._gdi32 is None:
            return
        for name, original in list(self._originals.items()):
            hdc = self._gdi32.CreateDCW(name, None, None, None)
            if not hdc:
                continue
            try:
                self._set_ramp(hdc, original)
            finally:
                self._gdi32.DeleteDC(hdc)
        self._originals.clear()
        self._applied_kelvin = None


# ── Schedule ────────────────────────────────────────────────────────────────


@dataclass
class CircadianState:
    phase: str                 # off | day | winding_down | night
    kelvin: int
    bedtime_start: Optional[datetime]
    bedtime_end: Optional[datetime]
    minutes_to_bedtime: int
    progress: float
    enabled: bool

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "kelvin": self.kelvin,
            "bedtime_start": self.bedtime_start,
            "bedtime_end": self.bedtime_end,
            "minutes_to_bedtime": self.minutes_to_bedtime,
            "progress": round(self.progress, 3),
            "enabled": self.enabled,
        }


def compute_state(
    now: datetime,
    bedtime_start: str,
    bedtime_end: str,
    lead_minutes: int,
    target_kelvin: int,
    enabled: bool = True,
) -> CircadianState:
    """Pure schedule calculation (testable without touching the display)."""
    target_kelvin = max(_MIN_KELVIN, min(DAY_KELVIN, int(target_kelvin)))
    lead_minutes = max(0, min(360, int(lead_minutes)))
    if not enabled:
        return CircadianState("off", DAY_KELVIN, None, None, 0, 0.0, False)

    start_t = _parse_hhmm(bedtime_start, "23:00")
    end_t = _parse_hhmm(bedtime_end, "06:00")
    if start_t == end_t:
        return CircadianState("day", DAY_KELVIN, None, None, 0, 0.0, True)

    start_dt = datetime.combine(now.date(), start_t)
    end_dt = datetime.combine(now.date(), end_t)

    if start_t < end_t:
        # Same-day window, e.g. 01:00 -> 07:00.
        if start_dt <= now < end_dt:
            return CircadianState("night", target_kelvin, start_dt, end_dt, 0, 1.0, True)
        if now >= end_dt:
            start_dt += timedelta(days=1)
            end_dt += timedelta(days=1)
    else:
        # Cross-midnight window, e.g. 23:00 -> 06:00.
        if now >= start_dt:
            end_dt += timedelta(days=1)
            return CircadianState("night", target_kelvin, start_dt, end_dt, 0, 1.0, True)
        if now < end_dt:
            start_dt -= timedelta(days=1)
            end_dt -= timedelta(days=1)
            return CircadianState("night", target_kelvin, start_dt, end_dt, 0, 1.0, True)

    # Daytime: look toward the next bedtime window.
    lead_delta = timedelta(minutes=lead_minutes)
    lead_start = start_dt - lead_delta
    minutes_to = max(0, int((start_dt - now).total_seconds() // 60))

    if lead_minutes > 0 and now >= lead_start:
        span = max(1.0, (start_dt - lead_start).total_seconds())
        progress = max(0.0, min(1.0, (now - lead_start).total_seconds() / span))
        kelvin = interpolate_kelvin(progress, target_kelvin)
        return CircadianState("winding_down", kelvin, start_dt, end_dt, minutes_to, progress, True)

    return CircadianState("day", DAY_KELVIN, start_dt, end_dt, minutes_to, 0.0, True)


# ── Controller ──────────────────────────────────────────────────────────────


class CircadianController(QObject):
    """QTimer-driven scheduler; applies gamma slowly and restores on stop."""

    state_changed = Signal(object)

    _instance: Optional["CircadianController"] = None

    @classmethod
    def instance(cls) -> "CircadianController":
        if cls._instance is None:
            cls._instance = CircadianController()
        return cls._instance

    def __init__(
        self,
        settings=None,
        applier: Optional[GammaRampController] = None,
        clock: Optional[Callable[[], datetime]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        if settings is None:
            from settings.manager import SettingsManager

            settings = SettingsManager()
        self._settings = settings
        self._applier = applier if applier is not None else GammaRampController()
        if applier is None and os.environ.get("DW_TEST_MODE") == "1":
            # Never touch the developer's display while running the test suite.
            self._applier._available = False
        self._clock = clock or datetime.now
        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.tick)
        self._last_state: Optional[dict] = None
        self._running = False
        # Safety net for a normal interpreter exit; stop() is the primary path.
        try:
            atexit.register(self._applier.restore)
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.tick()
        self._timer.start()
        logger.info("[CIRCADIAN] Display schedule started (enabled=%s).", self._settings.get_bool("circadian_enabled", False))

    def stop(self) -> None:
        self._running = False
        self._timer.stop()
        try:
            self._applier.restore()
        except Exception:
            pass
        logger.info("[CIRCADIAN] Display schedule stopped; gamma restored.")

    def current_state(self) -> CircadianState:
        enabled = self._settings.get_bool("circadian_enabled", False)
        lead = self._settings.get_int("circadian_lead_minutes", 90)
        target = self._settings.get_int("circadian_target_kelvin", 3400)
        return compute_state(
            self._clock(),
            self._settings.bedtime_start,
            self._settings.bedtime_end,
            lead,
            target,
            enabled=enabled,
        )

    def tick(self) -> CircadianState:
        state = self.current_state()
        payload = state.to_dict()
        if payload != self._last_state:
            self._last_state = payload
            try:
                if state.phase in ("off", "day") or state.kelvin >= DAY_KELVIN:
                    self._applier.restore()
                else:
                    self._applier.apply_kelvin(state.kelvin)
            except Exception as exc:
                logger.debug("[CIRCADIAN] Gamma apply failed: %s", exc)
            self.state_changed.emit(payload)
        return state
