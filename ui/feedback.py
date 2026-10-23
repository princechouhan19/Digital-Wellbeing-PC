"""
feedback.py — Haptics-lite interaction feedback for Digital Wellbeing v4.0.

Windows desktops rarely have actuators, so "haptics" is delivered as:
  1. System sounds via the native Windows sound scheme (winsound.MessageBeep)
     — respects the OS sound scheme and the user's `sound_feedback` setting.
  2. A soft visual "pulse" overlay that mimics a spring touch response.

All API calls are no-ops on non-Windows platforms and never raise.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect

from ui.design_system import RADIUS, DURATION_SLOW, EASE_OUT


class Sound:
    """System sound vocabulary (Apple-style semantic feedback)."""

    TAP = "tap"              # subtle UI tap — toggles, selection
    SUCCESS = "success"      # focus completed, settings saved
    WARNING = "warning"      # approaching limits
    ERROR = "error"          # limit reached, blocked app

    _WIN_MAP = {
        "tap": 0x00000000,        # MB_OK      → default beep
        "success": 0x00000040,    # MB_ICONASTERISK → gentle star chime
        "warning": 0x00000030,    # MB_ICONWARNING   → exclamation
        "error": 0x00000010,      # MB_ICONHAND      → critical
    }


def sound_enabled() -> bool:
    """Check the user's sound_feedback preference (default: on)."""
    try:
        from settings.manager import SettingsManager
        return SettingsManager().get_bool("sound_feedback", True)
    except Exception:
        return True


def play(kind: str = Sound.TAP) -> None:
    """Play a semantic system sound. Asynchronous, never blocks or raises."""
    if sys.platform != "win32" or not sound_enabled():
        return
    try:
        import winsound
        winsound.MessageBeep(Sound._WIN_MAP.get(kind, Sound._WIN_MAP["tap"]))
    except Exception:
        pass


def pulse(widget: QWidget, color: str = None, radius: int = None) -> None:
    """
    Visual haptic: a quick soft flash over the widget (like iOS keypress glow).
    Safe on any widget; creates a transient overlay child that fades out.
    """
    if widget is None:
        return
    try:
        if color is None:
            from ui.theme import ThemeManager
            color = ThemeManager.instance().color("accent_tint_bg")
        if radius is None:
            radius = RADIUS["md"]

        overlay = QWidget(widget)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setStyleSheet(
            f"background-color: {color}; border-radius: {radius}px; border: none;")
        overlay.setGeometry(widget.rect().adjusted(0, 0, -1, -1))
        overlay.show()
        overlay.raise_()

        effect = QGraphicsOpacityEffect(overlay)
        effect.setOpacity(0.55)
        overlay.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", overlay)
        anim.setDuration(DURATION_SLOW)
        anim.setStartValue(0.55)
        anim.setEndValue(0.0)
        anim.setEasingCurve(EASE_OUT)
        anim.finished.connect(overlay.deleteLater)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    except Exception:
        pass


def tap(widget: QWidget = None) -> None:
    """Standard interaction feedback: soft tap sound + optional visual pulse."""
    play(Sound.TAP)
    if widget is not None:
        pulse(widget)


def success(widget: QWidget = None) -> None:
    play(Sound.SUCCESS)
    if widget is not None:
        pulse(widget)


def warning(widget: QWidget = None) -> None:
    play(Sound.WARNING)
    if widget is not None:
        pulse(widget)


def error(widget: QWidget = None) -> None:
    play(Sound.ERROR)
    if widget is not None:
        pulse(widget)
