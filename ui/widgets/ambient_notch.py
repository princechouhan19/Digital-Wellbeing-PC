"""
ambient_notch.py — Smart, Fluid Desktop Dynamic Island & Notch for Digital Wellbeing.
Fully cloned and integrated from https://github.com/rajsriv/dynamic-island-for-windows
and Vayli (vayli.in) Apple-grade notch silhouette.

Features:
- Pure OLED black body with concave bezier ears/shoulders docked flush to top screen edge (Notch Nook)
- Full interactive information panels:
    * Performance Status panel (CPU, RAM, Storage, Network up/down with animated progress bars)
    * Weather Forecast panel (Large temperature, city, condition description, 5-slot hourly forecast)
    * Calendar & Tasks panel (Next up tasks with category badges, time tags, integrated task manager)
    * Month Progress panel (Month percentage, grid of day dots)
    * Basics panel & Orbiting ControlBalls (Shutdown, Restart, Sleep, File Explorer, Settings, Taskmgr, Chrome, YouTube, CMD)
    * Media Player panel with album art, playback controls, and lrclib synchronized lyrics
    * Deep Work & Focus panel synced with Digital Wellbeing FocusManager and Repository
- Mouse wheel scrolling (wheelEvent) across panels with fluid morphing animations
- Dynamic background blooms: paint_weather_bg, paint_perf_bg, paint_calendar_bg, paint_month_bg
- Fluid Blobs, Glow Sweep, and Neon Border media accent animations
- Charging ears laser beam animation when laptop is plugged in
- Specular shine sweep transition animation
- Signature cyan ambient visualizer micro-dot matrix along the bottom curve
- Right-click context menu (Island Style, Animation Style, Change Location, Compatibility Mode)
- Fullscreen media & gaming suppression
"""
from __future__ import annotations

import datetime
import json
import math
import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

import psutil
import qtawesome as qta
from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Property,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QRegion,
    QTransform,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.logger import logger
from database.repository import Repository
from protection.focus_manager import FocusManager
from settings.manager import SettingsManager
from tracker.media_awareness import detect_foreground_media
from ui.theme import ThemeManager

# Dynamic Island Monitors & Styles
from ui.dynamic_island import (
    KeyLockMonitor,
    MediaMonitor,
    NotificationMonitor,
    PerfMonitor,
    WeatherMonitor,
)
from ui.dynamic_island.app_styles import get_stylesheet

# Optional win32 keyboard control for native Windows media playback
try:
    import win32api
    HAS_WIN32 = True
except Exception:
    HAS_WIN32 = False

try:
    import winreg
    HAS_WINREG = True
except Exception:
    HAS_WINREG = False

try:
    import ctypes
    HAS_CTYPES = True
except Exception:
    HAS_CTYPES = False

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def send_media_key(vk: int) -> None:
    if not HAS_WIN32:
        return
    try:
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, 2, 0)
    except Exception as exc:
        logger.debug("Failed sending media key %s: %s", vk, exc)


def make_rounded_pixmap(pix: QPixmap, size: int, radius: float) -> QPixmap:
    if pix.isNull():
        return pix
    scaled = pix.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.setClipPath(path)
    sx = max(0, (scaled.width() - size) // 2)
    sy = max(0, (scaled.height() - size) // 2)
    p.drawPixmap(0, 0, scaled, sx, sy, size, size)
    p.end()
    return out


def elide_text(text: str, max_chars: int = 22) -> str:
    """Clamps long text with an ellipsis to prevent UI overflow."""
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[:max_chars - 1].rstrip() + "…"


DEFAULT_TASKS = [
    {"name": "Project Sync", "category": "Work", "color": "#00A0FF", "time": "2:00 PM"},
    {"name": "Gym Session", "category": "Health", "color": "#00FF80", "time": "5:30 PM"},
    {"name": "Dinner with Family", "category": "Personal", "color": "#FF5050", "time": "8:00 PM"},
]


# ── Orbiting Floating Control Ball ───────────────────────────────────────────

class ControlBall(QPushButton):
    """
    Orbiting interactive control button ported directly from dynamic-island-for-windows.
    Scales smoothly and executes associated system commands.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlBall")
        self.setFixedSize(40, 40)
        self._ball_scale = 1.0
        self.action_cmd = None
        self.clicked.connect(self.execute_action)
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def get_ball_scale(self) -> float:
        return self._ball_scale

    def set_ball_scale(self, val: float) -> None:
        self._ball_scale = float(val)
        self.update()

    ball_scale = Property(float, get_ball_scale, set_ball_scale)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._ball_scale != 1.0:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.scale(self._ball_scale, self._ball_scale)
            painter.translate(-self.width() / 2, -self.height() / 2)
        super().paintEvent(event)

    def execute_action(self):
        if self.action_cmd:
            if isinstance(self.action_cmd, str) and self.action_cmd.startswith("http"):
                webbrowser.open(self.action_cmd)
            else:
                try:
                    subprocess.Popen(self.action_cmd, shell=True)
                except Exception as exc:
                    logger.debug("Failed executing action %s: %s", self.action_cmd, exc)

    def animate_to(self, pos: QPoint, opacity: float, scale: float = 1.0, duration: int = 600, delay: int = 0):
        if hasattr(self, "_current_anim") and self._current_anim is not None:
            self._current_anim.stop()

        self._current_anim = QParallelAnimationGroup(self)

        p_anim = QPropertyAnimation(self, b"pos")
        p_anim.setDuration(duration)
        p_anim.setEasingCurve(QEasingCurve.Type.OutBack if opacity > 0 else QEasingCurve.Type.OutExpo)
        p_anim.setEndValue(pos)

        o_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        o_anim.setDuration(duration)
        o_anim.setEndValue(opacity)

        s_anim = QPropertyAnimation(self, b"ball_scale")
        s_anim.setDuration(duration)
        s_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        s_anim.setEndValue(scale)

        self._current_anim.addAnimation(p_anim)
        self._current_anim.addAnimation(o_anim)
        self._current_anim.addAnimation(s_anim)

        if delay > 0:
            QTimer.singleShot(delay, self._current_anim.start)
        else:
            self._current_anim.start()


# ── Clean Vector Icon Widgets ────────────────────────────────────────────────

class VectorButton(QPushButton):
    """Vector button for play, pause, next, prev, circle_play, circle_pause."""

    def __init__(self, kind: str, size: int = 24, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._kind = kind
        self._hovered = False
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_kind(self, kind: str) -> None:
        if self._kind != kind:
            self._kind = kind
            self.update()

    def enterEvent(self, e):
        self._hovered = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())

        is_circle = self._kind.startswith("circle_")
        if is_circle:
            bg_col = QColor(48, 50, 56) if self._hovered else QColor(36, 36, 40)
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            p.setBrush(bg_col)
            p.drawEllipse(QRectF(1, 1, w - 2, h - 2))

        col = QColor(56, 189, 248) if (self._hovered and not is_circle) else QColor(255, 255, 255)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)

        sub_kind = self._kind.replace("circle_", "")
        if sub_kind == "play":
            path = QPainterPath()
            path.moveTo(w * 0.36, h * 0.26)
            path.lineTo(w * 0.72, h * 0.50)
            path.lineTo(w * 0.36, h * 0.74)
            path.closeSubpath()
            p.fillPath(path, col)
        elif sub_kind == "pause":
            bar_w = max(2.5, w * 0.13)
            bar_h = h * 0.46
            top_y = h * 0.27
            path1 = QPainterPath()
            path1.addRoundedRect(QRectF(w * 0.31, top_y, bar_w, bar_h), 1.2, 1.2)
            path2 = QPainterPath()
            path2.addRoundedRect(QRectF(w * 0.56, top_y, bar_w, bar_h), 1.2, 1.2)
            p.fillPath(path1, col)
            p.fillPath(path2, col)
        elif sub_kind == "prev":
            bar_path = QPainterPath()
            bar_path.addRoundedRect(QRectF(w * 0.22, h * 0.26, 2.2, h * 0.48), 1.0, 1.0)
            p.fillPath(bar_path, col)
            tri = QPainterPath()
            tri.moveTo(w * 0.74, h * 0.26)
            tri.lineTo(w * 0.38, h * 0.50)
            tri.lineTo(w * 0.74, h * 0.74)
            tri.closeSubpath()
            p.fillPath(tri, col)
        elif sub_kind == "next":
            tri = QPainterPath()
            tri.moveTo(w * 0.26, h * 0.26)
            tri.lineTo(w * 0.62, h * 0.50)
            tri.lineTo(w * 0.26, h * 0.74)
            tri.closeSubpath()
            p.fillPath(tri, col)
            bar_path = QPainterPath()
            bar_path.addRoundedRect(QRectF(w * 0.68, h * 0.26, 2.2, h * 0.48), 1.0, 1.0)
            p.fillPath(bar_path, col)

        p.end()


class StopwatchIcon(QWidget):
    """Vector stopwatch icon."""

    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        p.setPen(QPen(QColor(255, 255, 255, 220), 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(1.5, 3.0, w - 3.0, h - 4.5))
        p.drawLine(QPointF(w / 2.0, 0.8), QPointF(w / 2.0, 3.0))
        p.drawLine(QPointF(w / 2.0 - 2.0, 0.8), QPointF(w / 2.0 + 2.0, 0.8))
        center_x = w / 2.0
        center_y = 3.0 + (h - 4.5) / 2.0
        p.drawLine(QPointF(center_x, center_y), QPointF(center_x, center_y - 3.5))
        p.drawLine(QPointF(center_x, center_y), QPointF(center_x + 2.5, center_y))
        p.end()


class AppleBatteryWidget(QWidget):
    """
    Apple Design System Battery indicator.
    Matches the Apple Dynamic Island battery UI:
    - Glowing Apple Green bolt icon (on the left of the capsule when charging).
    - Rounded Apple battery capsule (translucent border + terminal cap).
    - Apple Green fill (#30D158) or Red (#FF453A when <= 20%).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 16)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._percent = 100
        self._charging = False

    def set_status(self, percent: int, charging: bool) -> None:
        self._percent = max(0, min(100, percent))
        self._charging = charging
        # If charging, expand width to fit lightning bolt + capsule
        self.setFixedSize(36 if charging else 24, 16)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. If charging: draw glowing Apple Green lightning bolt on the left
        bolt_offset_x = 0.0
        if self._charging:
            bolt_color = QColor(48, 209, 88)  # Apple Green #30D158
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bolt_color)

            bolt = QPainterPath()
            bolt.moveTo(6.0, 1.5)
            bolt.lineTo(2.0, 7.5)
            bolt.lineTo(5.0, 7.5)
            bolt.lineTo(3.0, 14.0)
            bolt.lineTo(9.5, 6.5)
            bolt.lineTo(6.5, 6.5)
            bolt.closeSubpath()
            painter.fillPath(bolt, bolt_color)
            bolt_offset_x = 11.0

        # 2. Battery Capsule Outline & Terminal Cap
        cap_x = bolt_offset_x + 1.0
        cap_y = 2.5
        cap_w = 21.0
        cap_h = 11.0
        radius = 3.4

        # Border
        border_col = QColor(255, 255, 255, 95)
        painter.setPen(QPen(border_col, 1.1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(cap_x, cap_y, cap_w, cap_h), radius, radius)

        # Positive terminal nipple on right
        nipple_x = cap_x + cap_w + 0.5
        nipple_y = cap_y + 3.2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(border_col)
        painter.drawRoundedRect(QRectF(nipple_x, nipple_y, 1.4, 4.6), 0.7, 0.7)

        # 3. Inner Fill
        fill_max_w = cap_w - 3.6
        fill_w = max(1.5, fill_max_w * (self._percent / 100.0))
        fill_h = cap_h - 3.6
        fill_x = cap_x + 1.8
        fill_y = cap_y + 1.8

        if self._charging:
            fill_col = QColor(48, 209, 88)  # Apple Green
        elif self._percent <= 20:
            fill_col = QColor(255, 69, 58)  # Apple Red
        else:
            fill_col = QColor(48, 209, 88) if self._percent > 80 else QColor(255, 255, 255, 220)

        painter.setBrush(fill_col)
        painter.drawRoundedRect(QRectF(fill_x, fill_y, fill_w, fill_h), 1.8, 1.8)
        painter.end()


# Alias for backwards compatibility
BatteryWidget = AppleBatteryWidget


class SpeakerIcon(QWidget):
    """Vector speaker icon with sound waves."""

    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 230))
        path = QPainterPath()
        path.moveTo(2, 5.5)
        path.lineTo(5, 5.5)
        path.lineTo(9, 2.5)
        path.lineTo(9, 13.5)
        path.lineTo(5, 10.5)
        path.lineTo(2, 10.5)
        path.closeSubpath()
        p.fillPath(path, QColor(255, 255, 255, 230))
        p.setPen(QPen(QColor(56, 189, 248), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(7.5, 4.5, 4.5, 7.0), -60 * 16, 120 * 16)
        p.drawArc(QRectF(8.5, 2.5, 6.5, 11.0), -60 * 16, 120 * 16)
        p.end()


class SoundbarVisualizerWidget(QWidget):
    """
    Real-time 5-band animated soundbar visualizer.
    Synced dynamically to live sound bass, vocals, pitch, and treble.
    """

    def __init__(self, bar_count: int = 5, size: tuple[int, int] = (26, 16), parent=None):
        super().__init__(parent)
        self.setFixedSize(size[0], size[1])
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._bar_count = bar_count
        self._levels = [0.15] * bar_count
        self._accent = QColor(56, 189, 248)
        self._phase = 0.0

    def set_phase(self, phase: float) -> None:
        self._phase = phase
        if all(lvl <= 0.16 for lvl in self._levels):
            self.update()

    def set_levels(self, levels: list[float]) -> None:
        count = min(len(levels), self._bar_count)
        for i in range(count):
            self._levels[i] = max(0.12, min(1.0, float(levels[i])))
        self.update()

    def set_accent_color(self, color: QColor) -> None:
        self._accent = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent)

        w = float(self.width())
        h = float(self.height())
        bar_w = 2.4
        spacing = (w - (self._bar_count * bar_w)) / max(1, self._bar_count - 1)
        center_y = h / 2.0

        for i in range(self._bar_count):
            lvl = self._levels[i]
            if all(x <= 0.16 for x in self._levels):
                idle_boost = 0.06 * math.sin(self._phase * 2.0 + i * 1.2)
                lvl = max(0.12, lvl + idle_boost)

            bar_h = max(3.0, (h - 2.0) * lvl)
            x = i * (bar_w + spacing)
            y = center_y - bar_h / 2.0
            r = bar_w / 2.0
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), r, r)
        painter.end()


# Backwards compatibility alias
EqualizerDotsWidget = SoundbarVisualizerWidget


class ProgressBarWidget(QWidget):
    """Capsule progress bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(3)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._progress = 0.0

    def set_progress(self, val: float) -> None:
        self._progress = max(0.0, min(1.0, float(val)))
        self.update()

    def progress(self) -> float:
        return self._progress

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())
        r = h / 2.0
        bg_path = QPainterPath()
        bg_path.addRoundedRect(QRectF(0, 0, w, h), r, r)
        painter.fillPath(bg_path, QColor(255, 255, 255, 45))
        fill_w = max(h, w * self._progress)
        fill_path = QPainterPath()
        fill_path.addRoundedRect(QRectF(0, 0, fill_w, h), r, r)
        painter.fillPath(fill_path, QColor(255, 255, 255, 245))
        painter.end()


# ── Notch Canvas with Apple Concave Bezier Horns & Dynamic Accent Aura ─────────

class NotchCanvas(QFrame):
    """
    Custom-painted Notch body with Apple/Vayli concave bezier horns,
    and background bloom painters ported from dynamic-island-for-windows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._ear_w = 18.0
        self._ear_h = 14.0
        self._r_bottom = 16.0
        self._show_visualizer_dots = False
        self._anim_phase = 0.0
        self._accent_color = QColor(56, 189, 248)
        self._is_charging = False
        self._audio_intensity = 0.0

        # Bloom opacities
        self._weather_bg_opacity = 0.0
        self._perf_bg_opacity = 0.0
        self._calendar_bg_opacity = 0.0
        self._month_bg_opacity = 0.0
        self._shine_phase = -1.0
        self._charging_phase = 0.0
        self._gradient_phase = 0.0
        self._weather_bg_phase = 0.0
        self.island_style = "Notch Nook"
        self.animation_style = "Fluid Blobs"

    def set_bottom_radius(self, r: float) -> None:
        self._r_bottom = r
        self.update()

    def set_audio_intensity(self, intensity: float) -> None:
        self._audio_intensity = max(0.0, min(1.0, float(intensity)))
        self.update()

    def set_visualizer_phase(self, phase: float) -> None:
        self._anim_phase = phase
        self._gradient_phase = (self._gradient_phase + 0.005) % 1.0
        self._weather_bg_phase = (self._weather_bg_phase + 0.003) % 1.0
        self.update()

    def set_accent_color(self, hex_color: str) -> None:
        try:
            self._accent_color = QColor(hex_color)
            self.update()
        except Exception:
            pass

    def set_charging(self, charging: bool) -> None:
        if self._is_charging != charging:
            self._is_charging = charging
            self.update()

    def set_show_visualizer_dots(self, show: bool) -> None:
        self._show_visualizer_dots = show
        self.update()

    def build_notch_path(self, rect: QRectF) -> QPainterPath:
        radius = min(rect.height() / 2.0, 18.0)
        scoop = min(radius * 1.4, 25.0)
        left = rect.left() + scoop
        right = rect.right() - scoop
        top = rect.top()
        bottom = rect.bottom()

        path = QPainterPath()
        path.moveTo(left - scoop, top)
        path.cubicTo(
            left - scoop * 0.05, top,
            left, top + scoop * 0.05,
            left, top + scoop,
        )
        path.lineTo(left, bottom - radius)
        path.quadTo(left, bottom, left + radius, bottom)
        path.lineTo(right - radius, bottom)
        path.quadTo(right, bottom, right, bottom - radius)
        path.lineTo(right, top + scoop)
        path.cubicTo(
            right, top + scoop * 0.05,
            right + scoop * 0.05, top,
            right + scoop, top,
        )
        path.lineTo(left - scoop, top)
        path.closeSubpath()
        return path

    def _draw_shape(self, painter: QPainter, rect: QRectF, radius: float):
        if self.island_style == "Notch Nook":
            painter.drawPath(self.build_notch_path(rect))
        else:
            painter.drawRoundedRect(rect, radius, radius)

    def paint_weather_bg(self, painter: QPainter, rect: QRectF, radius: float):
        painter.save()
        painter.setOpacity(self._weather_bg_opacity)
        p = self._weather_bg_phase * 2 * math.pi

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(20, 40, 100))
        grad.setColorAt(1, QColor(10, 20, 60))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(60, 130, 250, 120), QColor(40, 80, 220, 100)]):
            x = rect.center().x() + math.sin(p + i) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.7 + i * 2) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.6)
            bloom.setColorAt(0, color)
            bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom)
            self._draw_shape(painter, rect, radius)
        painter.restore()

    def paint_perf_bg(self, painter: QPainter, rect: QRectF, radius: float):
        painter.save()
        painter.setOpacity(self._perf_bg_opacity)
        p = self._weather_bg_phase * 2 * math.pi

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(0, 40, 20))
        grad.setColorAt(1, QColor(0, 20, 10))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(50, 255, 50, 80), QColor(200, 255, 0, 60)]):
            x = rect.center().x() + math.sin(p * 0.8 + i * 1.5) * (rect.width() * 0.35)
            y = rect.center().y() + math.cos(p * 0.5 + i) * (rect.height() * 0.25)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.5)
            bloom.setColorAt(0, color)
            bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom)
            self._draw_shape(painter, rect, radius)
        painter.restore()

    def paint_calendar_bg(self, painter: QPainter, rect: QRectF, radius: float):
        painter.save()
        painter.setOpacity(self._calendar_bg_opacity)
        p = self._weather_bg_phase * 2 * math.pi

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(60, 40, 0))
        grad.setColorAt(1, QColor(30, 20, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(255, 180, 0, 90), QColor(255, 255, 0, 60)]):
            x = rect.center().x() + math.sin(p * 0.9 + i * 2) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.6 + i) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.55)
            bloom.setColorAt(0, color)
            bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom)
            self._draw_shape(painter, rect, radius)
        painter.restore()

    def paint_month_bg(self, painter: QPainter, rect: QRectF, radius: float):
        painter.save()
        painter.setOpacity(self._month_bg_opacity)
        p = self._weather_bg_phase * 2 * math.pi

        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, QColor(30, 0, 50))
        grad.setColorAt(1, QColor(15, 0, 30))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for i, color in enumerate([QColor(180, 0, 255, 80), QColor(255, 0, 180, 60)]):
            x = rect.center().x() + math.sin(p * 1.1 + i) * (rect.width() * 0.3)
            y = rect.center().y() + math.cos(p * 0.8 + i * 1.2) * (rect.height() * 0.2)
            bloom = QRadialGradient(QPointF(x, y), rect.width() * 0.5)
            bloom.setColorAt(0, color)
            bloom.setColorAt(1, Qt.GlobalColor.transparent)
            painter.setBrush(bloom)
            self._draw_shape(painter, rect, radius)
        painter.restore()

    def paint_fluid_blobs(self, painter: QPainter, rect: QRectF, radius: float):
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        glow_color = QColor(self._accent_color)
        glow_color.setAlpha(100)
        p = self._gradient_phase * 2 * math.pi
        x1 = rect.width() * (0.2 + 0.15 * math.sin(p))
        y1 = rect.height() * (0.5 + 0.25 * math.cos(p))
        g1 = QRadialGradient(x1, y1, rect.width() * 0.45)
        g1.setColorAt(0, glow_color)
        g1.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g1)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        x2 = rect.width() * (0.8 + 0.15 * math.cos(p * 0.7))
        y2 = rect.height() * (0.5 + 0.25 * math.sin(p * 1.2))
        g2 = QRadialGradient(x2, y2, rect.width() * 0.35)
        g2.setColorAt(0, QColor(glow_color).lighter(125))
        g2.setColorAt(1, Qt.GlobalColor.transparent)
        painter.setBrush(g2)
        self._draw_shape(painter, rect, radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def paint_glow_sweep(self, painter: QPainter, rect: QRectF, radius: float):
        glow = QColor(self._accent_color)
        glow.setAlpha(120)
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        gradient.setSpread(QLinearGradient.Spread.RepeatSpread)
        gradient.setColorAt(0.0, Qt.GlobalColor.transparent)
        gradient.setColorAt(0.5, glow)
        gradient.setColorAt(1.0, Qt.GlobalColor.transparent)
        brush = QBrush(gradient)
        transform = QTransform()
        transform.translate(self._gradient_phase * rect.width() * 2, 0)
        brush.setTransform(transform)
        painter.setBrush(brush)
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

    def paint_neon_border(self, painter: QPainter, rect: QRectF, radius: float):
        conical = QConicalGradient(rect.center(), self._gradient_phase * 360)
        for i, c in enumerate(["#F00", "#FF0", "#0F0", "#0FF", "#00F", "#F0F", "#F00"]):
            conical.setColorAt(i / 6.0, QColor(c))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(conical), 2.2))
        if self.island_style == "Notch Nook":
            painter.drawPath(self.build_notch_path(rect.adjusted(1, 1, -1, -1)))
        else:
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

    def paint_charging_ears(self, painter: QPainter, rect: QRectF, radius: float):
        p = self._charging_phase
        if p <= 0:
            return

        opacity = math.sin(p * math.pi)
        centerY = rect.top() + rect.height() / 2

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)

        glow_path = QPainterPath()
        glow_path.addRoundedRect(rect.adjusted(-20 * opacity, -10 * opacity, 20 * opacity, 10 * opacity), radius + 10, radius + 10)

        for i in range(5):
            alpha = int(70 * opacity / (i + 1))
            color = QColor(0, 255, 255, alpha) if i % 2 == 0 else QColor(140, 0, 255, alpha)
            painter.setPen(QPen(color, 12 + i * 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(glow_path)

        beam_len = 500 * opacity
        left_edge = rect.left()
        right_edge = rect.right()

        for i in range(3):
            beam_w = 4 - i
            if beam_w <= 0:
                continue
            alpha = int(180 * opacity / (i + 1))
            r_beam_grad = QLinearGradient(right_edge, centerY, right_edge + beam_len, centerY)
            r_beam_grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            r_beam_grad.setColorAt(0.1, QColor(0, 240, 255, alpha))
            r_beam_grad.setColorAt(0.5, QColor(160, 0, 255, alpha // 2))
            r_beam_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setPen(QPen(QBrush(r_beam_grad), beam_w + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(right_edge, centerY), QPointF(right_edge + beam_len, centerY))

            l_beam_grad = QLinearGradient(left_edge, centerY, left_edge - beam_len, centerY)
            l_beam_grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            l_beam_grad.setColorAt(0.1, QColor(0, 240, 255, alpha))
            l_beam_grad.setColorAt(0.5, QColor(160, 0, 255, alpha // 2))
            l_beam_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setPen(QPen(QBrush(l_beam_grad), beam_w + 1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(left_edge, centerY), QPointF(left_edge - beam_len, centerY))

        painter.setBrush(QColor(255, 255, 255, int(255 * opacity)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(right_edge, centerY), 4, 3)
        painter.drawEllipse(QPointF(left_edge, centerY), 4, 3)
        painter.restore()

    def paint_shine_sweep(self, painter: QPainter, rect: QRectF, radius: float):
        p = self._shine_phase
        if p <= 0 or p >= 1.0:
            return

        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        start_x = 35
        max_reach = rect.width() * 1.5
        current_expansion = max_reach * p
        base_alpha = int(220 * math.sin(p * math.pi))

        for i in range(2):
            W = current_expansion * (0.6 + i * 0.1)
            h = rect.height()
            target_x = start_x + (current_expansion * 0.4)
            target_y = h / 2.0
            painter.save()
            painter.translate(target_x, target_y)
            painter.scale(2.5, 0.8)
            grad = QRadialGradient(QPointF(0, 0), W / 2)
            alpha = int(base_alpha * (1.0 - i * 0.3))
            grad.setColorAt(0.0, QColor(255, 255, 255, alpha))
            grad.setColorAt(0.3, QColor(0, 160, 255, int(alpha * 0.6)))
            grad.setColorAt(0.6, QColor(90, 0, 255, int(alpha * 0.15)))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), W / 2, W / 2)
            painter.restore()

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        radius = min(rect.height() / 2.0, 18.0 if self.island_style == "Notch Nook" else 24.0)

        # 1. Charging ears animation
        if self._charging_phase > 0.0:
            self.paint_charging_ears(painter, rect, radius)

        # 2. Drop shadow
        for i in range(5):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 15 - i * 3))
            shadow_rect = rect.adjusted(i, 0 if self.island_style == "Notch Nook" else i, -i, -i)
            self._draw_shape(painter, shadow_rect, radius)

        # 3. Pure OLED pitch black background
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.setPen(Qt.PenStyle.NoPen)
        self._draw_shape(painter, rect, radius)

        # 4. Background dynamic blooms
        if self._weather_bg_opacity > 0.0:
            self.paint_weather_bg(painter, rect, radius)
        if self._perf_bg_opacity > 0.0:
            self.paint_perf_bg(painter, rect, radius)
        if self._calendar_bg_opacity > 0.0:
            self.paint_calendar_bg(painter, rect, radius)
        if self._month_bg_opacity > 0.0:
            self.paint_month_bg(painter, rect, radius)

        # 5. Media Animations (Fluid Blobs / Glow Sweep / Neon Border)
        clip_path = QPainterPath()
        if self.island_style == "Notch Nook":
            clip_path = self.build_notch_path(rect)
        else:
            clip_path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(clip_path)

        if self._show_visualizer_dots:
            if self.animation_style == "Glow Sweep":
                self.paint_glow_sweep(painter, rect, radius)
            elif self.animation_style == "Fluid Blobs":
                self.paint_fluid_blobs(painter, rect, radius)
            elif self.animation_style == "Neon Border":
                self.paint_neon_border(painter, rect, radius)

        # 6. Specular shine sweep
        if 0.0 < self._shine_phase < 1.0:
            self.paint_shine_sweep(painter, rect, radius)

        # 7. Dynamic glass rim stroke
        painter.setClipping(False)
        border_col = QColor(255, 255, 255, 25)
        if self._accent_color != QColor(56, 189, 248):
            border_col = QColor(self._accent_color)
            border_col.setAlpha(50)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(border_col, 1.0))
        self._draw_shape(painter, rect.adjusted(0.5, 0.5, -0.5, -0.5), radius)

        # 8. Signature cyan micro-dot matrix along bottom curve
        if self._show_visualizer_dots:
            start_x = rect.left() + 28.0
            end_x = rect.right() - 28.0
            dot_y = rect.bottom() - 4.5
            spacing = 6.2
            num_dots = int((end_x - start_x) / spacing)
            dot_color = QColor(self._accent_color)
            painter.setPen(Qt.PenStyle.NoPen)

            for i in range(num_dots):
                x = start_x + i * spacing
                wave = math.sin(i * 0.35 + self._anim_phase)
                boost = getattr(self, "_audio_intensity", 0.0)
                alpha = int(145 + 105 * wave * (1.0 + 0.5 * boost))
                dot_color.setAlpha(max(50, min(255, alpha)))
                painter.setBrush(dot_color)
                painter.drawEllipse(QRectF(x - 1.1, dot_y - 1.1, 2.2, 2.2))

        painter.end()


# ── Ambient Notch Main Window ────────────────────────────────────────────────

class AmbientNotch(QWidget):
    """Unified Smart Dynamic Island integrating all dynamic-island-for-windows monitors and UI panels."""

    task_completed = Signal(int)

    # Rest Dimensions
    REST_WIDTH_IDLE = 200
    REST_WIDTH_TASK = 240
    REST_WIDTH_MEDIA = 260
    REST_WIDTH_VOLUME = 240
    REST_HEIGHT = 38

    # Expanded Panel Dimensions (matching reference repo)
    PERF_W, PERF_H = 360, 180
    MUSIC_W, MUSIC_H = 420, 80
    LYRIC_W, LYRIC_H = 600, 80
    WEATHER_W, WEATHER_H = 360, 160
    CALENDAR_W, CALENDAR_H = 400, 165
    MONTH_W, MONTH_H = 360, 140
    BASICS_W, BASICS_H = 340, 110
    TASK_W, TASK_H = 400, 125
    EDIT_W, EDIT_H = 500, 480

    EXP_WIDTH_MEDIA = MUSIC_W
    EXP_HEIGHT_MEDIA = MUSIC_H
    EXP_WIDTH_TASK = TASK_W
    EXP_HEIGHT_TASK = TASK_H
    EXP_WIDTH_IDLE = 360
    EXP_HEIGHT_IDLE = 110

    MODE_IDLE = "idle"
    MODE_TASK = "task"
    MODE_MEDIA = "media"
    MODE_VOLUME = "volume"

    MODE_FOCUS = "task"
    MODE_STATUS = "idle"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)

        self._repo = Repository()
        self._fm = FocusManager.instance()
        self._sm = SettingsManager()

        self._is_expanded = False
        self._hover_enabled = False
        self._current_mode: Optional[str] = None
        self._previous_mode = self.MODE_IDLE
        self._focus_active = False
        self.compatibility_mode = False

        # Panels feature index & controls
        self.features = ["perf", "media", "weather", "calendar", "month", "basics"]
        self.current_feature_index = 0
        self.is_editing_tasks = False
        self.island_style = "Notch Nook"
        self.animation_style = "Fluid Blobs"

        # Basic controls orbiting items
        self.basic_controls_index = 0
        self.basic_controls_items = [
            {"name": "Shutdown", "icon": "mdi.power", "cmd": "shutdown /s /t 0"},
            {"name": "Restart", "icon": "mdi.refresh", "cmd": "shutdown /r /t 0"},
            {"name": "Sleep", "icon": "mdi.sleep", "cmd": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"},
            {"name": "File Explorer", "icon": "mdi.folder-outline", "cmd": "explorer ."},
            {"name": "Settings", "icon": "mdi.cog-outline", "cmd": "start ms-settings:"},
            {"name": "Task Manager", "icon": "mdi.chart-bubble", "cmd": "taskmgr"},
            {"name": "Chrome", "icon": "mdi.google-chrome", "cmd": "start chrome"},
            {"name": "YouTube", "icon": "mdi.youtube", "cmd": "https://www.youtube.com"},
            {"name": "CMD", "icon": "mdi.console", "cmd": "start cmd"},
        ]
        self.control_balls: list[ControlBall] = []

        # Task state
        self._active_task: Optional[dict] = None
        self._active_task_id: int = 0
        self._next_task: Optional[dict] = None
        self._poll_count: int = 0
        self._anim_phase: float = 0.0

        # Real media state (from MediaMonitor)
        self._media_playing = False
        self._media_detected = False
        self._media_title = ""
        self._media_artist = ""
        self._media_accent_color = "#38BDF8"
        self._media_thumb_pixmap: Optional[QPixmap] = None
        self._media_lyric = ""
        self._showing_lyrics = False

        # Cached metrics
        self._perf_data = {"cpu": 0.0, "ram": 0.0, "disk": 0.0, "down": 0, "up": 0}
        self._weather_data = {"city": "New Delhi", "temp": "--°C", "desc": "Clear", "hourly": []}

        # Battery
        self._has_battery = False
        self._battery_percent = 100
        self._battery_charging = False
        self._last_power_plugged = psutil.sensors_battery().power_plugged if psutil.sensors_battery() else False

        self._load_config()
        self._init_apple_fonts()
        self._setup_ui()
        self._setup_animations()
        self._init_background_monitors()

        # Master timers
        self._system_timer = QTimer(self)
        self._system_timer.timeout.connect(self._on_system_tick)
        self._system_timer.start(1000)

        self._fx_timer = QTimer(self)
        self._fx_timer.timeout.connect(self._on_fx_tick)
        self._fx_timer.start(16)

        self._transient_timer = QTimer(self)
        self._transient_timer.setSingleShot(True)
        self._transient_timer.timeout.connect(self._restore_pre_transient_mode)

        self._hover_leave_timer = QTimer(self)
        self._hover_leave_timer.setSingleShot(True)
        self._hover_leave_timer.timeout.connect(lambda: self.set_expanded(False))

        # Initial layout
        self.set_mode(self.MODE_IDLE)
        self._sync_battery_and_time()
        self.sync_active_task()
        self._evaluate_smart_mode()
        self._update_position(expanded=False)

    def _init_apple_fonts(self) -> None:
        try:
            base_dir = Path(__file__).resolve().parent.parent.parent
            font_dir = base_dir / "assets" / "fonts"
            if font_dir.is_dir():
                for font_file in font_dir.iterdir():
                    if font_file.suffix.lower() in (".ttf", ".otf"):
                        QFontDatabase.addApplicationFont(str(font_file))
        except Exception as e:
            logger.debug("Failed loading fonts: %s", e)

    def _load_config(self) -> None:
        try:
            cfg_path = Path(__file__).resolve().parent.parent / "dynamic_island" / "config.json"
            if cfg_path.is_file():
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.island_style = data.get("island_style", "Notch Nook")
                    self.animation_style = data.get("animation_style", "Fluid Blobs")
                    self.compatibility_mode = data.get("compatibility_mode", False)
                    if "tasks" in data:
                        self.custom_tasks = data["tasks"]
                    else:
                        self.custom_tasks = DEFAULT_TASKS
            else:
                self.custom_tasks = DEFAULT_TASKS
        except Exception:
            self.custom_tasks = DEFAULT_TASKS

    def _save_config(self) -> None:
        try:
            cfg_path = Path(__file__).resolve().parent.parent / "dynamic_island" / "config.json"
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "location": self._weather_data.get("city", "New Delhi, India"),
                "island_style": self.island_style,
                "animation_style": self.animation_style,
                "compatibility_mode": self.compatibility_mode,
                "tasks": getattr(self, "custom_tasks", DEFAULT_TASKS),
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as exc:
            logger.debug("Failed saving config: %s", exc)

    def closeEvent(self, event):
        self._stop_background_monitors()
        super().closeEvent(event)

    def _init_background_monitors(self) -> None:
        # 1. MediaMonitor
        self._media_monitor = MediaMonitor(self)
        self._media_monitor.media_updated.connect(self._on_media_monitor_updated)
        self._media_monitor.lyrics_updated.connect(self._on_lyrics_updated)
        self._media_monitor.start()

        # 2. KeyLockMonitor
        self._key_monitor = KeyLockMonitor(self)
        self._key_monitor.lock_changed.connect(self._on_key_lock_changed)
        self._key_monitor.start()

        # 3. PerfMonitor
        self._perf_monitor = PerfMonitor(interval_sec=1.5, parent=self)
        self._perf_monitor.metrics_updated.connect(self._on_perf_updated)
        self._perf_monitor.start()

        # 4. WeatherMonitor
        loc = getattr(self, "settings", {}).get("location", "New Delhi, India") if hasattr(self, "settings") else "New Delhi, India"
        self._weather_monitor = WeatherMonitor(city=loc, parent=self)
        self._weather_monitor.weather_updated.connect(self._on_weather_updated)
        self._weather_monitor.start()

        # 5. AudioVisualizerWorker (Real-time live music equalizer)
        try:
            from ui.dynamic_island.audio_visualizer import AudioVisualizerWorker
            self._audio_visualizer = AudioVisualizerWorker(self)
            self._audio_visualizer.levels_updated.connect(self._on_audio_levels_updated)
            self._audio_visualizer.start()
        except Exception as e:
            logger.debug("Failed initializing AudioVisualizerWorker: %s", e)
            self._audio_visualizer = None

    def _stop_background_monitors(self) -> None:
        for m in [
            getattr(self, "_media_monitor", None),
            getattr(self, "_key_monitor", None),
            getattr(self, "_perf_monitor", None),
            getattr(self, "_weather_monitor", None),
            getattr(self, "_audio_visualizer", None),
        ]:
            if m:
                try:
                    m.stop()
                except Exception:
                    pass

    # ── UI Construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._canvas = NotchCanvas(self)
        self._canvas.setObjectName("notch_canvas")
        self._canvas.setMouseTracking(True)
        self._canvas.island_style = self.island_style
        self._canvas.animation_style = self.animation_style
        root_layout.addWidget(self._canvas)

        self._layout = QVBoxLayout(self._canvas)
        self._layout.setContentsMargins(24, 7, 24, 8)
        self._layout.setSpacing(4)

        self._compact_stack = QStackedWidget()
        self._compact_stack.setObjectName("compact_stack")

        # 0. Idle Mode: Live Time (Left) & Apple Battery (Right)
        self._view_idle = QWidget()
        v_idle_layout = QHBoxLayout(self._view_idle)
        v_idle_layout.setContentsMargins(10, 0, 10, 0)
        v_idle_layout.setSpacing(5)

        self._lbl_idle_time = QLabel("10:32 AM")
        self._lbl_idle_time.setObjectName("compact_time_digits")
        v_idle_layout.addWidget(self._lbl_idle_time)

        v_idle_layout.addStretch(1)

        self._battery_widget = AppleBatteryWidget()
        v_idle_layout.addWidget(self._battery_widget)

        self._lbl_idle_battery = QLabel("79")
        self._lbl_idle_battery.setObjectName("compact_battery_digits")
        v_idle_layout.addWidget(self._lbl_idle_battery)

        self._compact_stack.addWidget(self._view_idle)

        # 1. Task Mode: Task Title · Live Timer
        self._view_task = QWidget()
        v_task_layout = QHBoxLayout(self._view_task)
        v_task_layout.setContentsMargins(6, 0, 6, 0)
        v_task_layout.setSpacing(8)

        self._icon_task_stopwatch = StopwatchIcon(14)
        v_task_layout.addWidget(self._icon_task_stopwatch)

        self._lbl_task_name = QLabel("Ready to Focus")
        self._lbl_task_name.setObjectName("compact_title")
        self._lbl_task_name.setMaximumWidth(120)
        self._lbl_task_name.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        v_task_layout.addWidget(self._lbl_task_name)

        v_task_layout.addStretch(1)

        self._lbl_task_timer = QLabel("25:00")
        self._lbl_task_timer.setObjectName("compact_timer_digits")
        v_task_layout.addWidget(self._lbl_task_timer)

        self._btn_compact_pause = VectorButton("circle_pause", 24)
        self._btn_compact_pause.clicked.connect(self._on_toggle_focus_clicked)
        v_task_layout.addWidget(self._btn_compact_pause)

        self._compact_stack.addWidget(self._view_task)

        # 2. Media Mode: Real Playing Song & Live Artwork
        self._view_media = QWidget()
        v_media_layout = QHBoxLayout(self._view_media)
        v_media_layout.setContentsMargins(6, 0, 6, 0)
        v_media_layout.setSpacing(8)

        self._media_thumb = QLabel()
        self._media_thumb.setFixedSize(22, 22)
        self._media_thumb.setScaledContents(True)
        v_media_layout.addWidget(self._media_thumb)

        self._media_title_lbl = QLabel("No Media Playing")
        self._media_title_lbl.setObjectName("compact_title")
        self._media_title_lbl.setMaximumWidth(140)
        self._media_title_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        v_media_layout.addWidget(self._media_title_lbl)

        v_media_layout.addStretch(1)

        self._eq_dots = EqualizerDotsWidget()
        v_media_layout.addWidget(self._eq_dots)

        self._compact_stack.addWidget(self._view_media)

        # 3. Transient HUD (Caps Lock, Num Lock, Volume)
        self._view_hud = QWidget()
        v_hud_layout = QHBoxLayout(self._view_hud)
        v_hud_layout.setContentsMargins(6, 0, 6, 0)
        v_hud_layout.setSpacing(8)

        self._hud_icon_speaker = SpeakerIcon(15)
        v_hud_layout.addWidget(self._hud_icon_speaker)

        self._hud_title_lbl = QLabel("Caps Lock")
        self._hud_title_lbl.setObjectName("vol_label")
        v_hud_layout.addWidget(self._hud_title_lbl)

        self._hud_bar = ProgressBarWidget()
        v_hud_layout.addWidget(self._hud_bar, 1)

        self._hud_sub_lbl = QLabel("ON")
        self._hud_sub_lbl.setObjectName("vol_percent")
        v_hud_layout.addWidget(self._hud_sub_lbl)

        self._compact_stack.addWidget(self._view_hud)
        self._layout.addWidget(self._compact_stack)

        # ── 2. Cloned Expanded Panels from dynamic-island-for-windows ─────────
        self._expanded_container = QWidget()
        self._expanded_container.setObjectName("expanded_container")
        self._expanded_vbox = QVBoxLayout(self._expanded_container)
        self._expanded_vbox.setContentsMargins(0, 0, 0, 0)
        self._expanded_vbox.setSpacing(6)

        # 2.1 Performance Panel
        self.perf_panel = self.create_perf_panel()
        self._expanded_vbox.addWidget(self.perf_panel)

        # 2.2 Weather Panel
        self.weather_panel = self.create_weather_panel()
        self._expanded_vbox.addWidget(self.weather_panel)

        # 2.3 Calendar / Tasks Panel
        self.calendar_panel = self.create_calendar_panel()
        self._expanded_vbox.addWidget(self.calendar_panel)

        # 2.4 Month Progress Panel
        self.month_panel = self.create_month_panel()
        self._expanded_vbox.addWidget(self.month_panel)

        # 2.5 Basics Navigation Panel
        self.basics_panel = self.create_basics_panel()
        self._expanded_vbox.addWidget(self.basics_panel)

        # 2.6 Media Expanded Panel
        self._media_panel = self.create_media_panel()
        self._expanded_vbox.addWidget(self._media_panel)

        # 2.7 Focus Session Panel
        self._task_panel = self.create_task_panel()
        self._expanded_vbox.addWidget(self._task_panel)

        # 2.8 Idle Quick Overview Panel
        self._idle_panel = self.create_idle_overview_panel()
        self._expanded_vbox.addWidget(self._idle_panel)

        self._layout.addWidget(self._expanded_container)
        self._expanded_container.setVisible(False)

        # Orbiting ControlBalls (instantiated on self for floating/orbiting animations)
        for _ in range(4):
            ball = ControlBall(self)
            ball.hide()
            ball.move(-100, -100)
            self.control_balls.append(ball)

        self.setStyleSheet(get_stylesheet(self._media_accent_color))
        self._set_default_cover_art()

    # ── Panel Builders ────────────────────────────────────────────────────────

    def create_action_button(self, app_type: str) -> QPushButton:
        btn = QPushButton(icon=qta.icon("mdi.open-in-new", color="white"))
        btn.setObjectName("ActionButton")
        btn.setFixedSize(30, 30)
        btn.clicked.connect(lambda: self.open_app(app_type))
        return btn

    def open_app(self, app_type: str):
        schemes = {"weather": "bingweather:", "month": "ms-settings:dateandtime", "perf": "taskmgr"}
        if app_type in schemes:
            webbrowser.open(schemes[app_type])

    def create_perf_panel(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 6, 16, 12)
        l.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("System Status")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.create_action_button("perf"))
        l.addLayout(header)

        def add_item(layout, icon, label):
            v = QVBoxLayout()
            v.setSpacing(3)
            h = QHBoxLayout()
            ico = QLabel()
            ico.setPixmap(qta.icon(icon, color="white").pixmap(14, 14))
            txt = QLabel(label)
            txt.setStyleSheet("font-size: 10px; color: #888; font-weight: 600;")
            h.addWidget(ico)
            h.addWidget(txt)
            h.addStretch()
            val = QLabel("0%")
            val.setStyleSheet("font-size: 12px; font-weight: 600;")
            bar = QProgressBar()
            bar.setFixedHeight(4)
            bar.setTextVisible(False)
            bar.setMaximum(100)
            bar.setStyleSheet("QProgressBar { background-color: #222; border-radius: 2px; border: none; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF80, stop:1 #80FF00); border-radius: 2px; }")
            v.addLayout(h)
            v.addWidget(val)
            v.addWidget(bar)
            layout.addLayout(v)
            return bar, val

        r1 = QHBoxLayout()
        r1.setSpacing(24)
        self.cpu_bar_L = add_item(r1, "mdi.cpu-64-bit", "CPU")
        self.ram_bar_L = add_item(r1, "mdi.memory", "RAM")
        l.addLayout(r1)

        r2 = QHBoxLayout()
        r2.setSpacing(24)
        self.disk_bar_L = add_item(r2, "mdi.harddisk", "STORAGE")

        nv = QVBoxLayout()
        nv.setSpacing(3)
        nh = QHBoxLayout()
        nico = QLabel()
        nico.setPixmap(qta.icon("mdi.web", color="white").pixmap(14, 14))
        ntxt = QLabel("NETWORK")
        ntxt.setStyleSheet("font-size: 10px; color: #888; font-weight: 600;")
        nh.addWidget(nico)
        nh.addWidget(ntxt)
        nh.addStretch()
        nv.addLayout(nh)

        self.net_down_L = QLabel("↓ 0 KB/s")
        self.net_up_L = QLabel("↑ 0 KB/s")
        for lb in [self.net_down_L, self.net_up_L]:
            lb.setStyleSheet("font-size: 11px; font-weight: 600;")
        nv.addWidget(self.net_down_L)
        nv.addWidget(self.net_up_L)
        r2.addLayout(nv)
        l.addLayout(r2)
        return w

    def create_weather_panel(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 6, 16, 12)
        l.setSpacing(10)

        h1 = QHBoxLayout()
        self.weather_temp_label = QLabel("--°")
        self.weather_temp_label.setStyleSheet("font-size: 34px; font-weight: bold;")

        info = QVBoxLayout()
        loc_name = getattr(self, "settings", {}).get("location", "New Delhi, India") if hasattr(self, "settings") else "New Delhi, India"
        self.weather_city_label = QLabel(loc_name)
        self.weather_city_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        self.weather_cond_label = QLabel("Loading...")
        self.weather_cond_label.setStyleSheet("font-size: 11px; color: #AAA;")
        info.addWidget(self.weather_city_label)
        info.addWidget(self.weather_cond_label)

        h1.addLayout(info)
        h1.addStretch()
        h1.addWidget(self.weather_temp_label)
        l.addLayout(h1)

        self.hourly_layout = QHBoxLayout()
        self.hourly_layout.setSpacing(5)
        self.hourly_slots = []
        for _ in range(5):
            slot = QVBoxLayout()
            slot.setSpacing(2)
            st = QLabel("--")
            st.setStyleSheet("font-size: 9px; color: #888;")
            st.setAlignment(Qt.AlignmentFlag.AlignCenter)
            si = QLabel()
            si.setPixmap(qta.icon("mdi.weather-cloudy", color="white").pixmap(18, 18))
            si.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stp = QLabel("--°")
            stp.setStyleSheet("font-size: 10px; font-weight: 600;")
            stp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slot.addWidget(st)
            slot.addWidget(si)
            slot.addWidget(stp)
            self.hourly_layout.addLayout(slot)
            self.hourly_slots.append((st, si, stp))

        l.addLayout(self.hourly_layout)
        return w

    def create_calendar_panel(self) -> QWidget:
        self.calendar_panel_widget = QWidget()
        cal_layout = QVBoxLayout(self.calendar_panel_widget)
        cal_layout.setContentsMargins(0, 0, 0, 0)
        cal_layout.setSpacing(0)

        # View Mode Container
        self.task_view_widget = QWidget()
        view_layout = QVBoxLayout(self.task_view_widget)
        view_layout.setContentsMargins(18, 8, 18, 14)
        view_layout.setSpacing(8)

        h = QHBoxLayout()
        t = QLabel("Next Up")
        t.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.ev_count_label = QLabel("0 tasks")
        self.ev_count_label.setStyleSheet("color: #888; font-size: 11px;")
        eb = self.create_action_button("calendar")
        eb.setIcon(qta.icon("mdi.pencil", color="white"))
        eb.clicked.connect(self.open_task_editor)
        h.addWidget(eb)
        h.addSpacing(5)
        h.addWidget(t)
        h.addWidget(self.ev_count_label)
        h.addStretch()
        view_layout.addLayout(h)

        self.tasks_container_widget = QWidget()
        self.tasks_container_layout = QVBoxLayout(self.tasks_container_widget)
        self.tasks_container_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_container_layout.setSpacing(8)
        view_layout.addWidget(self.tasks_container_widget)
        view_layout.addStretch()

        # Edit Mode Container
        self.task_edit_widget = QWidget()
        self.task_edit_widget.hide()
        edit_layout = QVBoxLayout(self.task_edit_widget)
        edit_layout.setContentsMargins(18, 12, 18, 12)
        edit_layout.setSpacing(10)

        self.edit_list = QListWidget()
        input_grid = QGridLayout()
        input_grid.setSpacing(8)
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("Task Name")
        self.edit_time = QLineEdit()
        self.edit_time.setPlaceholderText("Time (e.g. 3:00 PM)")
        self.edit_cat = QComboBox()
        self.edit_cat.addItems(["Work", "Health", "Personal", "Study", "Other"])

        input_grid.addWidget(self.edit_name, 0, 0, 1, 2)
        input_grid.addWidget(self.edit_time, 1, 0)
        input_grid.addWidget(self.edit_cat, 1, 1)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.setObjectName("DialogBtn")
        add_btn.clicked.connect(self.add_task_integrated)
        del_btn = QPushButton("Delete Selected")
        del_btn.setObjectName("DialogBtn")
        del_btn.clicked.connect(self.delete_task_integrated)
        save_btn = QPushButton("Save and Close")
        save_btn.setStyleSheet(f"background-color: {self._media_accent_color}; color: white; border-radius: 8px; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_and_close_editor)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)

        edit_layout.addWidget(QLabel("Manage Tasks", styleSheet="font-weight: bold; font-size: 15px;"))
        edit_layout.addWidget(self.edit_list)
        edit_layout.addLayout(input_grid)
        edit_layout.addLayout(btn_layout)
        edit_layout.addWidget(save_btn)

        cal_layout.addWidget(self.task_view_widget)
        cal_layout.addWidget(self.task_edit_widget)
        self.refresh_calendar_panel()
        return self.calendar_panel_widget

    def add_task_integrated(self):
        name = self.edit_name.text().strip()
        if name:
            tasks = getattr(self, "custom_tasks", DEFAULT_TASKS)
            tasks.append({
                "name": name,
                "category": self.edit_cat.currentText(),
                "time": self.edit_time.text().strip() or "N/A",
                "color": "#00A0FF",
            })
            self.custom_tasks = tasks
            self._save_config()
            self.refresh_calendar_panel()
            self.edit_name.clear()
            self.edit_time.clear()

    def delete_task_integrated(self):
        idx = self.edit_list.currentRow()
        tasks = getattr(self, "custom_tasks", DEFAULT_TASKS)
        if 0 <= idx < len(tasks):
            tasks.pop(idx)
            self.custom_tasks = tasks
            self._save_config()
            self.refresh_calendar_panel()

    def save_and_close_editor(self):
        self._save_config()
        self.open_task_editor()

    def open_task_editor(self):
        self.is_editing_tasks = not self.is_editing_tasks
        self.task_view_widget.setVisible(not self.is_editing_tasks)
        self.task_edit_widget.setVisible(self.is_editing_tasks)
        self._update_position(expanded=True)

    def refresh_calendar_panel(self):
        for child in self.tasks_container_widget.findChildren(QWidget):
            child.hide()
            child.setParent(None)
            child.deleteLater()

        while self.tasks_container_layout.count():
            item = self.tasks_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tasks = getattr(self, "custom_tasks", DEFAULT_TASKS)
        self.ev_count_label.setText(f"{len(tasks)} tasks")

        self.edit_list.clear()
        for t in tasks:
            item = QListWidgetItem(f"{t['name']} • {t['time']}\n{t.get('category', 'Task').upper()}")
            self.edit_list.addItem(item)

        for t in tasks[:3]:
            row = QHBoxLayout()
            bar = QFrame()
            bar.setFixedWidth(3)
            bar.setStyleSheet(f"background-color: {t.get('color', '#00A0FF')}; border-radius: 1px;")
            det = QVBoxLayout()
            det.setContentsMargins(0, 0, 0, 0)
            det.setSpacing(1)
            n = QLabel(t["name"])
            n.setStyleSheet("font-size: 12px; font-weight: 600; padding: 0px;")
            c = QLabel(t.get("category", "Task"))
            c.setStyleSheet("font-size: 9px; color: #888; padding: 0px;")
            det.addWidget(n)
            det.addWidget(c)
            tm = QLabel(t.get("time", ""))
            tm.setStyleSheet("font-size: 11px; font-weight: 500;")
            row.addWidget(bar)
            row.addLayout(det)
            row.addStretch()
            row.addWidget(tm)
            self.tasks_container_layout.addLayout(row)

    def create_month_panel(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(18, 8, 18, 14)
        l.setSpacing(8)

        now = datetime.datetime.now()
        days = (datetime.date(now.year, now.month + 1, 1) - datetime.date(now.year, now.month, 1)).days if now.month < 12 else 31
        header = QHBoxLayout()
        title = QLabel(now.strftime("%B Progress"))
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        perc = QLabel(f"{int(now.day / days * 100)}%")
        perc.setStyleSheet("color: #00A0FF; font-weight: bold; font-size: 13px;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(perc)
        header.addWidget(self.create_action_button("month"))
        l.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(7)
        grid.setContentsMargins(0, 4, 0, 0)
        for i in range(days):
            dot = QFrame()
            dot.setFixedSize(11, 11)
            color = "#00A0FF" if (i + 1) <= now.day else "#333333"
            dot.setStyleSheet(f"background-color: {color}; border-radius: 5px;")
            grid.addWidget(dot, i // 10, i % 10)
        l.addLayout(grid)
        return w

    def create_basics_panel(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 8, 16, 10)
        l.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        btn_l = QPushButton("<", objectName="NavButton")
        btn_r = QPushButton(">", objectName="NavButton")
        btn_l.setFixedSize(24, 24)
        btn_r.setFixedSize(24, 24)
        btn_l.clicked.connect(lambda: self.scroll_controls(-1))
        btn_r.clicked.connect(lambda: self.scroll_controls(1))

        lbl = QLabel("Quick Actions")
        lbl.setObjectName("basics_title")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header.addWidget(btn_l)
        header.addStretch(1)
        header.addWidget(lbl)
        header.addStretch(1)
        header.addWidget(btn_r)
        l.addLayout(header)

        self._basics_row = QHBoxLayout()
        self._basics_row.setContentsMargins(0, 0, 0, 0)
        self._basics_row.setSpacing(12)
        self._basics_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._basics_buttons: list[QPushButton] = []
        for _ in range(4):
            btn = QPushButton()
            btn.setObjectName("ControlBall")
            btn.setFixedSize(44, 44)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.clicked.connect(self._on_basics_btn_clicked)
            self._basics_row.addWidget(btn)
            self._basics_buttons.append(btn)

        l.addLayout(self._basics_row)
        self._refresh_basics_buttons()
        return w

    def _on_basics_btn_clicked(self) -> None:
        btn = self.sender()
        if isinstance(btn, QPushButton):
            cmd = btn.property("cmd")
            if cmd:
                self._execute_action_cmd(cmd)

    def _refresh_basics_buttons(self) -> None:
        if not hasattr(self, "_basics_buttons") or not self._basics_buttons:
            return
        n = len(self.basic_controls_items)
        for i, btn in enumerate(self._basics_buttons):
            item_idx = (self.basic_controls_index + i) % n
            item = self.basic_controls_items[item_idx]
            btn.setIcon(qta.icon(item["icon"], color="white"))
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(item["name"])
            btn.setProperty("cmd", item["cmd"])

    def _execute_action_cmd(self, cmd: str) -> None:
        if not cmd:
            return
        if cmd.startswith("http"):
            webbrowser.open(cmd)
        else:
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                logger.debug("Failed executing action %s: %s", cmd, e)

    def scroll_controls(self, delta: int):
        n = len(self.basic_controls_items)
        self.basic_controls_index = (self.basic_controls_index + delta) % n
        self._refresh_basics_buttons()

    def animate_control_balls(self, show: bool):
        pass

    def create_media_panel(self) -> QWidget:
        w = QWidget()
        media_layout = QVBoxLayout(w)
        media_layout.setContentsMargins(6, 2, 6, 4)
        media_layout.setSpacing(6)

        # Top row: Thumbnail, Title + Artist, Soundbar, Time remain, Controls
        row_top = QHBoxLayout()
        row_top.setContentsMargins(0, 0, 0, 0)
        row_top.setSpacing(8)

        self._exp_thumb = QLabel()
        self._exp_thumb.setFixedSize(36, 36)
        self._exp_thumb.setScaledContents(True)
        row_top.addWidget(self._exp_thumb)

        col_text = QVBoxLayout()
        col_text.setContentsMargins(0, 0, 0, 0)
        col_text.setSpacing(2)

        self._exp_media_title = QLabel("No Media Playing")
        self._exp_media_title.setObjectName("exp_media_title")
        col_text.addWidget(self._exp_media_title)

        self._exp_media_artist = QLabel("")
        self._exp_media_artist.setObjectName("exp_media_artist")
        col_text.addWidget(self._exp_media_artist)
        row_top.addLayout(col_text, 1)

        # Real-time dancing audio soundbar in expanded view
        self._exp_soundbar = SoundbarVisualizerWidget(bar_count=5, size=(28, 16))
        row_top.addWidget(self._exp_soundbar)

        self._exp_time_remain = QLabel("")
        self._exp_time_remain.setObjectName("exp_time_remain")
        row_top.addWidget(self._exp_time_remain)

        self._btn_prev = VectorButton("prev", 20)
        self._btn_prev.clicked.connect(self._on_prev_media)
        row_top.addWidget(self._btn_prev)

        self._btn_play = VectorButton("pause", 24)
        self._btn_play.clicked.connect(self._on_toggle_media)
        row_top.addWidget(self._btn_play)

        self._btn_next = VectorButton("next", 20)
        self._btn_next.clicked.connect(self._on_next_media)
        row_top.addWidget(self._btn_next)

        media_layout.addLayout(row_top)

        # Bottom row: Capsule Progress Bar
        self._progress_bar = ProgressBarWidget()
        self._progress_bar.setFixedHeight(4)
        media_layout.addWidget(self._progress_bar)

        return w

    def create_task_panel(self) -> QWidget:
        w = QWidget()
        task_layout = QVBoxLayout(w)
        task_layout.setContentsMargins(12, 6, 12, 6)
        task_layout.setSpacing(6)

        t_header = QHBoxLayout()
        t_header.setSpacing(8)

        self._exp_stopwatch_icon = StopwatchIcon(16)
        t_header.addWidget(self._exp_stopwatch_icon)

        self._exp_digits = QLabel("18:40")
        self._exp_digits.setObjectName("exp_digits")
        t_header.addWidget(self._exp_digits)

        self._task_priority = QLabel("Normal")
        self._task_priority.setObjectName("priority_tag")
        t_header.addWidget(self._task_priority)
        t_header.addStretch(1)

        self._btn_circle_pause = VectorButton("circle_pause", 26)
        self._btn_circle_pause.clicked.connect(self._on_toggle_focus_clicked)
        t_header.addWidget(self._btn_circle_pause)
        task_layout.addLayout(t_header)

        self._exp_task_title = QLabel("Deep Work Session")
        self._exp_task_title.setObjectName("exp_task_title")
        task_layout.addWidget(self._exp_task_title)

        t_sub = QHBoxLayout()
        self._target_label = QLabel("Target: Any app")
        self._target_label.setObjectName("notch_target_label")
        t_sub.addWidget(self._target_label, 1)

        self._next_task_label = QLabel("Next: None")
        self._next_task_label.setObjectName("notch_next_task")
        t_sub.addWidget(self._next_task_label)
        task_layout.addLayout(t_sub)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_done = QPushButton("✓ Done")
        self._btn_done.setObjectName("notch_btn_done")
        self._btn_done.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_done.clicked.connect(self._on_mark_done_clicked)
        btn_row.addWidget(self._btn_done)

        self._btn_plus5 = QPushButton("+5m")
        self._btn_plus5.setObjectName("notch_btn_action")
        self._btn_plus5.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_plus5.clicked.connect(self._on_plus5_clicked)
        btn_row.addWidget(self._btn_plus5)

        self._btn_skip = QPushButton("⏭ Skip")
        self._btn_skip.setObjectName("notch_btn_action")
        self._btn_skip.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_skip.clicked.connect(self._on_skip_task_clicked)
        btn_row.addWidget(self._btn_skip)

        task_layout.addLayout(btn_row)
        return w

    def create_idle_overview_panel(self) -> QWidget:
        w = QWidget()
        idle_layout = QVBoxLayout(w)
        idle_layout.setContentsMargins(12, 6, 12, 6)
        idle_layout.setSpacing(6)

        idle_row1 = QHBoxLayout()
        self._exp_idle_date = QLabel("Today")
        self._exp_idle_date.setObjectName("exp_task_title")
        idle_row1.addWidget(self._exp_idle_date, 1)

        self._btn_quick_focus = QPushButton("▶ Start 25m Focus")
        self._btn_quick_focus.setObjectName("notch_btn_done")
        self._btn_quick_focus.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn_quick_focus.clicked.connect(self._on_quick_focus_clicked)
        idle_row1.addWidget(self._btn_quick_focus)
        idle_layout.addLayout(idle_row1)

        self._lbl_perf_bar = QLabel("CPU: 0%  RAM: 0%  ·  Weather: --°C")
        self._lbl_perf_bar.setObjectName("notch_target_label")
        idle_layout.addWidget(self._lbl_perf_bar)
        return w

    def _setup_animations(self) -> None:
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(240)
        self._anim.setEasingCurve(QEasingCurve.Type.OutExpo)

    def _set_default_cover_art(self) -> None:
        for size, lbl in [(24, self._media_thumb), (42, self._exp_thumb)]:
            img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            grad = QLinearGradient(0, 0, 0, size)
            grad.setColorAt(0.0, QColor(30, 41, 59))
            grad.setColorAt(1.0, QColor(15, 23, 42))

            r = 6.0 if size == 24 else 8.0
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, size, size), r, r)
            p.fillPath(path, grad)

            note = QPainterPath()
            note.addEllipse(QRectF(size * 0.25, size * 0.58, size * 0.28, size * 0.22))
            note.addRect(QRectF(size * 0.46, size * 0.26, size * 0.08, size * 0.42))
            note.addRect(QRectF(size * 0.46, size * 0.26, size * 0.26, size * 0.10))
            p.fillPath(note, QColor(56, 189, 248))
            p.end()

            lbl.setPixmap(QPixmap.fromImage(img))

    # ── Geometry & Layout Transitions ─────────────────────────────────────────

    def wheelEvent(self, event):
        if not self.is_editing_tasks:
            delta = event.angleDelta().y()
            if delta != 0:
                step = 1 if delta < 0 else -1
                self.current_feature_index = (self.current_feature_index + step) % len(self.features)
                if not self._is_expanded:
                    self.set_expanded(True)
                else:
                    self._update_expanded_panel_visibility()
                    self._update_position(expanded=True)
                    self.trigger_shine_sweep()
        super().wheelEvent(event)

    def trigger_shine_sweep(self):
        self._canvas._shine_phase = 0.0
        self._canvas.update()

    def _update_expanded_panel_visibility(self):
        feat = self.features[self.current_feature_index]
        self.perf_panel.setVisible(feat == "perf")
        self.weather_panel.setVisible(feat == "weather")
        self.calendar_panel.setVisible(feat == "calendar")
        self.month_panel.setVisible(feat == "month")
        self.basics_panel.setVisible(feat == "basics")
        self._media_panel.setVisible(feat == "media")
        self._task_panel.setVisible(False)
        self._idle_panel.setVisible(False)

        # Orbiting control balls
        self.animate_control_balls(feat == "basics")

        # Set bloom opacities
        self._canvas._weather_bg_opacity = 1.0 if feat == "weather" else 0.0
        self._canvas._perf_bg_opacity = 1.0 if feat == "perf" else 0.0
        self._canvas._calendar_bg_opacity = 1.0 if feat == "calendar" else 0.0
        self._canvas._month_bg_opacity = 1.0 if feat == "month" else 0.0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_canvas") and self._canvas:
            self._canvas.setGeometry(self.rect())

    def _update_position(self, expanded: bool) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.geometry()
        center_x = geo.x() + geo.width() // 2

        if expanded:
            feat = self.features[self.current_feature_index]
            if self.is_editing_tasks:
                target_w, target_h = self.EDIT_W, self.EDIT_H
            elif feat == "perf":
                target_w, target_h = self.PERF_W, self.PERF_H
            elif feat == "weather":
                target_w, target_h = self.WEATHER_W, self.WEATHER_H
            elif feat == "calendar":
                target_w, target_h = self.CALENDAR_W, self.CALENDAR_H
            elif feat == "month":
                target_w, target_h = self.MONTH_W, self.MONTH_H
            elif feat == "basics":
                target_w, target_h = self.BASICS_W, self.BASICS_H
            elif feat == "media":
                target_w = self.LYRIC_W if (self._showing_lyrics and self._media_lyric) else self.MUSIC_W
                target_h = self.MUSIC_H
            else:
                target_w, target_h = self.EXP_WIDTH_IDLE, self.EXP_HEIGHT_IDLE
        else:
            if self._current_mode == self.MODE_MEDIA:
                target_w = self.REST_WIDTH_MEDIA
            elif self._current_mode == self.MODE_TASK:
                target_w = self.REST_WIDTH_TASK
            elif self._current_mode == self.MODE_VOLUME:
                target_w = self.REST_WIDTH_VOLUME
            else:
                target_w = self.REST_WIDTH_IDLE
            target_h = self.REST_HEIGHT

        target_x = center_x - target_w // 2
        target_y = geo.y()

        curr_w = self.width()
        curr_h = self.height()
        start_x = center_x - curr_w // 2
        start_y = target_y

        self._anim.stop()
        self._anim.setStartValue(QRect(start_x, start_y, curr_w, curr_h))
        self._anim.setEndValue(QRect(target_x, target_y, target_w, target_h))
        self._anim.start()

    # ── Hover & Expansion ─────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(250, lambda: setattr(self, "_hover_enabled", True))

    def enterEvent(self, event):
        self._hover_leave_timer.stop()
        if getattr(self, "_hover_enabled", False):
            if not self._is_expanded and self._current_mode != self.MODE_VOLUME:
                self.set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._is_expanded and not self.is_editing_tasks:
            self._hover_leave_timer.start(500)
        super().leaveEvent(event)

    def set_expanded(self, expanded: bool) -> None:
        if self._is_expanded == expanded:
            return
        self._is_expanded = expanded

        if expanded:
            # Map current mode to starting feature panel
            if self._current_mode == self.MODE_MEDIA:
                self.current_feature_index = self.features.index("media") if "media" in self.features else 0
            elif self._current_mode == self.MODE_TASK:
                self.current_feature_index = self.features.index("calendar") if "calendar" in self.features else 0

            self._compact_stack.setVisible(False)
            self._expanded_container.setVisible(True)
            self._update_expanded_panel_visibility()
            self._update_position(expanded=True)
            self.trigger_shine_sweep()
        else:
            self.animate_control_balls(False)
            self._compact_stack.setVisible(True)
            self._expanded_container.setVisible(False)
            self._canvas._weather_bg_opacity = 0.0
            self._canvas._perf_bg_opacity = 0.0
            self._canvas._calendar_bg_opacity = 0.0
            self._canvas._month_bg_opacity = 0.0
            self._update_position(expanded=False)

    # ── Smart Mode Switching ──────────────────────────────────────────────────

    def _evaluate_smart_mode(self) -> None:
        if self._current_mode == self.MODE_VOLUME and self._transient_timer.isActive():
            return

        if self._media_detected and self._media_playing:
            self.set_mode(self.MODE_MEDIA)
        elif self._focus_active or self._fm.is_active or (self._active_task and self._active_task.get("status") == "in_progress"):
            self.set_mode(self.MODE_TASK)
        else:
            self.set_mode(self.MODE_IDLE)

    def set_mode(self, mode: str) -> None:
        if self._current_mode == mode:
            return
        self._current_mode = mode

        if self._current_mode == self.MODE_IDLE:
            self._compact_stack.setCurrentIndex(0)
            self._canvas.set_show_visualizer_dots(False)
        elif self._current_mode == self.MODE_TASK:
            self._compact_stack.setCurrentIndex(1)
            self._canvas.set_show_visualizer_dots(True)
        elif self._current_mode == self.MODE_MEDIA:
            self._compact_stack.setCurrentIndex(2)
            self._canvas.set_show_visualizer_dots(True)
        elif self._current_mode == self.MODE_VOLUME:
            self._compact_stack.setCurrentIndex(3)
            self._canvas.set_show_visualizer_dots(False)

        if not self._is_expanded:
            self._update_position(expanded=False)

    # ── Background Monitors Slots ─────────────────────────────────────────────

    def _on_media_monitor_updated(
        self,
        status: str,
        title: str,
        artist: str,
        accent_color: str,
        thumb_bytes: bytes,
        pos: float,
        dur: float,
    ) -> None:
        if status in ("Playing", "Paused"):
            self._media_detected = True
            self._media_playing = (status == "Playing")
            self._media_title = title
            self._media_artist = artist
            self._media_accent_color = accent_color

            self._canvas.set_accent_color(accent_color)
            self._eq_dots.set_accent_color(QColor(accent_color))
            if hasattr(self, "_exp_soundbar") and self._exp_soundbar:
                self._exp_soundbar.set_accent_color(QColor(accent_color))

            clean_title = elide_text(title, 20)
            self._media_title_lbl.setText(f"<b>{clean_title}</b>")
            self._exp_media_title.setText(elide_text(title, 34))
            self._exp_media_artist.setText(f"· {elide_text(artist, 24)}" if artist else "")

            if dur > 0:
                rem_sec = max(0, int(dur - pos))
                rem_m = rem_sec // 60
                rem_s = rem_sec % 60
                self._exp_time_remain.setText(f"-{rem_m}:{rem_s:02d}")
                self._progress_bar.set_progress(pos / dur)
            else:
                self._exp_time_remain.setText("")
                self._progress_bar.set_progress(0.40)

            if thumb_bytes:
                pix = QPixmap()
                if pix.loadFromData(thumb_bytes):
                    self._media_thumb_pixmap = pix
                    self._media_thumb.setPixmap(make_rounded_pixmap(pix, 24, 6.0))
                    self._exp_thumb.setPixmap(make_rounded_pixmap(pix, 42, 8.0))
            elif not self._media_thumb_pixmap:
                self._set_default_cover_art()

            self._btn_play.set_kind("pause" if self._media_playing else "play")
            self._evaluate_smart_mode()
        else:
            self._media_detected = False
            self._media_playing = False
            self._media_thumb_pixmap = None
            self._showing_lyrics = False
            self._media_lyric = ""
            self._canvas.set_accent_color("#38BDF8")
            self._eq_dots.set_accent_color(QColor(56, 189, 248))
            if hasattr(self, "_exp_soundbar") and self._exp_soundbar:
                self._exp_soundbar.set_accent_color(QColor(56, 189, 248))
            self._set_default_cover_art()
            self._evaluate_smart_mode()

    def _on_audio_levels_updated(self, levels: list) -> None:
        if not levels:
            return
        if hasattr(self, "_eq_dots") and self._eq_dots:
            self._eq_dots.set_levels(levels)
        if hasattr(self, "_exp_soundbar") and self._exp_soundbar:
            self._exp_soundbar.set_levels(levels)
        avg_intensity = sum(levels) / max(1, len(levels))
        if hasattr(self, "_canvas") and self._canvas:
            self._canvas.set_audio_intensity(avg_intensity)

    def _on_lyrics_updated(self, lyric_text: str) -> None:
        self._media_lyric = lyric_text
        self._showing_lyrics = bool(lyric_text)
        if lyric_text and self._is_expanded and self.features[self.current_feature_index] == "media":
            self._exp_media_artist.setText(f"♪ {lyric_text}")
            self._update_position(expanded=True)

    def _on_key_lock_changed(self, name: str, active: bool) -> None:
        state_txt = "ON" if active else "OFF"
        self._hud_icon_speaker.setVisible(False)
        self._hud_title_lbl.setText(name)
        self._hud_sub_lbl.setText(state_txt)
        self._hud_bar.setVisible(False)
        self._show_transient_hud()

    def _on_perf_updated(self, data: dict) -> None:
        self._perf_data = data
        cpu, ram, disk = data.get("cpu", 0), data.get("ram", 0), data.get("disk", 0)
        down, up = data.get("down", 0), data.get("up", 0)

        self.cpu_bar_L[0].setValue(int(cpu))
        self.cpu_bar_L[1].setText(f"{int(cpu)}%")
        self.ram_bar_L[0].setValue(int(ram))
        self.ram_bar_L[1].setText(f"{int(ram)}%")
        self.disk_bar_L[0].setValue(int(disk))
        self.disk_bar_L[1].setText(f"{int(disk)}%")

        def fmt(b):
            if b < 1024:
                return f"{int(b)} B/s"
            if b < 1024 * 1024:
                return f"{int(b / 1024)} KB/s"
            return f"{b / (1024 * 1024):.1f} MB/s"

        self.net_down_L.setText(f"↓ {fmt(down)}")
        self.net_up_L.setText(f"↑ {fmt(up)}")

    def _on_weather_updated(self, data: dict) -> None:
        self._weather_data = data
        self.weather_temp_label.setText(data.get("temp", "--°"))
        self.weather_city_label.setText(data.get("city", "New Delhi, India"))
        self.weather_cond_label.setText(data.get("desc", "Clear"))

        hourly = data.get("hourly", [])
        for i, slot in enumerate(hourly):
            if i < len(self.hourly_slots):
                st, si, stp = self.hourly_slots[i]
                st.setText(slot.get("time", "--"))
                icon_name = slot.get("icon", "mdi.weather-cloudy")
                si.setPixmap(qta.icon(icon_name, color="white").pixmap(18, 18))
                stp.setText(slot.get("temp", "--°"))

    # ── Media Control Handlers ────────────────────────────────────────────────

    def _on_prev_media(self) -> None:
        send_media_key(VK_MEDIA_PREV_TRACK)

    def _on_next_media(self) -> None:
        send_media_key(VK_MEDIA_NEXT_TRACK)

    def _on_toggle_media(self) -> None:
        send_media_key(VK_MEDIA_PLAY_PAUSE)
        self._media_playing = not self._media_playing
        self._btn_play.set_kind("pause" if self._media_playing else "play")

    # ── Focus & Task Handlers ─────────────────────────────────────────────────

    def _on_focus_tick(self, seconds_left: int) -> None:
        mins = seconds_left // 60
        secs = seconds_left % 60
        digits = f"{mins:02d}:{secs:02d}"
        self._lbl_task_timer.setText(digits)
        self._exp_digits.setText(digits)

        if self._active_task_id > 0:
            self._repo.add_smart_task_active_time(self._active_task_id, 1.0)

    def _on_focus_state_changed(self, is_active: bool) -> None:
        self._focus_active = is_active
        btn_kind = "circle_pause" if is_active else "circle_play"
        self._btn_compact_pause.set_kind(btn_kind)
        self._btn_circle_pause.set_kind(btn_kind)
        self.sync_active_task()
        self._evaluate_smart_mode()

    def _on_focus_completed(self) -> None:
        self._lbl_task_timer.setText("00:00")
        self._exp_digits.setText("00:00")
        self.sync_active_task()
        self._evaluate_smart_mode()

    def _on_toggle_focus_clicked(self) -> None:
        if self._fm.is_active:
            self._fm.stop_focus()
        else:
            mins = 25
            if self._active_task:
                mins = self._active_task.get("estimated_minutes", 25)
            self._fm.start_focus(minutes=mins)

    def _on_quick_focus_clicked(self) -> None:
        self._fm.start_focus(minutes=25)
        self.set_expanded(False)

    def _on_plus5_clicked(self) -> None:
        if self._fm.is_active:
            self._fm._seconds_remaining += 300
            self._fm.tick.emit(self._fm._seconds_remaining)

    def _on_mark_done_clicked(self) -> None:
        target_id = self._active_task_id
        if target_id <= 0:
            pending = self._repo.get_smart_tasks(status="pending")
            if pending:
                target_id = pending[0]["id"]

        if target_id > 0:
            self._repo.update_smart_task_status(target_id, "completed")
            self.task_completed.emit(target_id)
            remaining = self._repo.get_smart_tasks(status="pending")
            if remaining and self._fm.is_active:
                self._repo.update_smart_task_status(remaining[0]["id"], "in_progress")
            self.sync_active_task()
        else:
            if self._fm.is_active:
                self._fm.stop_focus()
            self.sync_active_task()
        self._evaluate_smart_mode()

    def _on_skip_task_clicked(self) -> None:
        pending = self._repo.get_smart_tasks(status="pending")
        if self._active_task and self._active_task.get("status") == "in_progress":
            self._repo.update_smart_task_status(self._active_task["id"], "pending")
        if pending:
            self._repo.update_smart_task_status(pending[0]["id"], "in_progress")
        self.sync_active_task()
        self._evaluate_smart_mode()

    # ── Task Synchronization & System Monitoring ──────────────────────────────

    def sync_active_task(self) -> None:
        try:
            tasks = self._repo.get_smart_tasks()
        except Exception:
            tasks = []

        in_prog = [t for t in tasks if t.get("status") == "in_progress"]
        pending = [t for t in tasks if t.get("status") == "pending"]

        if in_prog:
            self._active_task = in_prog[0]
            self._active_task_id = self._active_task["id"]
            self._next_task = pending[0] if pending else None
        elif pending:
            if self._fm.is_active:
                self._active_task = pending[0]
                self._active_task_id = self._active_task["id"]
                try:
                    self._repo.update_smart_task_status(self._active_task_id, "in_progress")
                except Exception:
                    pass
                self._next_task = pending[1] if len(pending) > 1 else None
            else:
                self._active_task = pending[0]
                self._active_task_id = self._active_task["id"]
                self._next_task = pending[1] if len(pending) > 1 else None
        else:
            self._active_task = None
            self._active_task_id = 0
            self._next_task = None

        if self._active_task:
            title = self._active_task.get("title", "")
            self._lbl_task_name.setText(title)
            self._exp_task_title.setText(title)
            prio = self._active_task.get("priority", 2)
            self._task_priority.setText("High" if prio == 1 else ("Normal" if prio == 2 else "Low"))
            targets = (self._active_task.get("target_processes") or []) + (self._active_task.get("target_domains") or [])
            self._target_label.setText(f"Target: {', '.join(targets[:2]) if targets else 'Any app'}")
        else:
            self._lbl_task_name.setText("Ready to Focus")
            self._exp_task_title.setText("Deep Work Session")
            self._task_priority.setText("General")
            self._target_label.setText("Target: Any app")

        if self._next_task:
            nt = self._next_task.get("title", "")
            trunc = nt if len(nt) <= 12 else nt[:10] + ".."
            self._next_task_label.setText(f"Next: {trunc}")
        else:
            self._next_task_label.setText("Queue: Clear" if not pending else "Next: None")

    def _sync_battery_and_time(self) -> None:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        self._lbl_idle_time.setText(time_str)

        try:
            b = psutil.sensors_battery()
            if b is not None:
                self._has_battery = True
                self._battery_percent = int(b.percent)
                self._battery_charging = bool(b.power_plugged)
                self._battery_widget.setVisible(True)
                self._battery_widget.set_status(self._battery_percent, self._battery_charging)
                self._canvas.set_charging(self._battery_charging)

                # Laser charging animation trigger when freshly plugged in
                if self._battery_charging and not self._last_power_plugged:
                    self._trigger_charging_ears_anim()
                self._last_power_plugged = self._battery_charging

                self._lbl_idle_battery.setText(f"{self._battery_percent}")
            else:
                self._has_battery = False
                self._battery_widget.setVisible(False)
                self._canvas.set_charging(False)
                self._lbl_idle_battery.setText(now.strftime("%a, %b %d"))
        except Exception:
            self._has_battery = False
            self._battery_widget.setVisible(False)
            self._canvas.set_charging(False)
            self._lbl_idle_battery.setText(now.strftime("%a, %b %d"))

    def _trigger_charging_ears_anim(self):
        self._canvas._charging_phase = 1.0
        self._canvas.update()
        QTimer.singleShot(3000, self._cleanup_charging_anim)

    def _cleanup_charging_anim(self):
        self._canvas._charging_phase = 0.0
        self._canvas.update()

    def _on_system_tick(self) -> None:
        self._poll_count += 1
        self._sync_battery_and_time()

        try:
            fg_media = detect_foreground_media()
            if getattr(fg_media, "is_fullscreen", False):
                self.hide()
                return
            elif not self.isVisible() and self._sm.get_bool("ambient_notch_enabled", True):
                self.show()
        except Exception:
            pass

        if self._poll_count % 2 == 0:
            self.sync_active_task()
            self._evaluate_smart_mode()

    def _on_fx_tick(self) -> None:
        self._anim_phase += 0.08
        self._canvas.set_visualizer_phase(self._anim_phase)
        if self._eq_dots.isVisible():
            self._eq_dots.set_phase(self._anim_phase)

    # ── Transient HUD Display ─────────────────────────────────────────────────

    def trigger_volume_hud(self, percent: int) -> None:
        self._hud_icon_speaker.setVisible(True)
        self._hud_title_lbl.setText("Volume")
        self._hud_bar.setVisible(True)
        self._hud_bar.set_progress(percent / 100.0)
        self._hud_sub_lbl.setText(f"{percent}%")
        self._show_transient_hud()

    def _show_transient_hud(self) -> None:
        if self._current_mode != self.MODE_VOLUME:
            self._previous_mode = self._current_mode or self.MODE_IDLE
        self.set_mode(self.MODE_VOLUME)
        self._transient_timer.start(1800)

    def _restore_pre_transient_mode(self) -> None:
        self.set_mode(self._previous_mode)
        self._evaluate_smart_mode()

    # ── Context Menu & Style Switching ────────────────────────────────────────

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #111; color: #fff; border: 1px solid #333; padding: 4px; border-radius: 8px; } QMenu::item:selected { background-color: " + self._media_accent_color + "; }")

        am = menu.addMenu("Animation Style")
        for s in ["Fluid Blobs", "Glow Sweep", "Neon Border"]:
            a = am.addAction(s)
            a.setCheckable(True)
            a.setChecked(self.animation_style == s)
            a.triggered.connect(lambda _, st=s: self.set_animation_style(st))

        sm = menu.addMenu("Island Style")
        for s in ["Notch Nook", "Default", "Liquid Glass"]:
            a = sm.addAction(s)
            a.setCheckable(True)
            a.setChecked(self.island_style == s)
            a.triggered.connect(lambda _, st=s: self.set_island_style(st))

        menu.addSeparator()
        comp_action = menu.addAction("Fix Big Box (Compatibility Mode)")
        comp_action.setCheckable(True)
        comp_action.setChecked(self.compatibility_mode)
        comp_action.triggered.connect(self.toggle_compatibility_mode)

        loc_action = menu.addAction("Change Location")
        loc_action.triggered.connect(self.change_location_dialog)

        menu.addSeparator()
        qa = menu.addAction("Hide Dynamic Island")
        qa.triggered.connect(self.hide)

        menu.exec(self.mapToGlobal(event.pos()))

    def set_animation_style(self, style: str):
        self.animation_style = style
        self._canvas.animation_style = style
        self._save_config()
        self._canvas.update()

    def set_island_style(self, style: str):
        self.island_style = style
        self._canvas.island_style = style
        self._save_config()
        self._update_position(expanded=self._is_expanded)
        self._canvas.update()

    def toggle_compatibility_mode(self):
        self.compatibility_mode = not self.compatibility_mode
        self._save_config()
        self._update_position(expanded=self._is_expanded)

    def change_location_dialog(self):
        city, ok = QInputDialog.getText(self, "Change Location", "Enter City Name:", text=self._weather_data.get("city", "New Delhi"))
        if ok and city:
            success, msg = self._weather_monitor.set_location(city)
            if success:
                self._save_config()
                self._on_key_lock_changed("Weather", True)
