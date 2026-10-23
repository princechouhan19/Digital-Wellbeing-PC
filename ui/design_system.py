"""
design_system.py — "Aurora" Apple Design System for Digital Wellbeing v4.0.

Single source of truth for the macOS Sequoia-inspired design language:
  • Color tokens (Apple system palette, light + dark)
  • Typography scale (bundled Inter / Inter Display, SF Pro-metrics)
  • Radius, spacing and elevation scales
  • Motion (durations + easing curves)
  • Font loading at application bootstrap

Everything visual should reference THIS module (or ThemeManager tokens,
which are generated from it). No hardcoded hex values in feature code.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve
from PySide6.QtGui import QColor, QFont, QFontDatabase

# ─────────────────────────────────────────────────────────────────────────────
# Color Palette — Apple System Colors (HIG)
# ─────────────────────────────────────────────────────────────────────────────
# systemBlue  #007AFF / #0A84FF · systemGreen #34C759 / #30D158
# systemRed   #FF3B30 / #FF453A · systemOrange #FF9500 / #FF9F0A
# systemPurple#AF52DE / #BF5AF2 · systemTeal #30B0C7 / #40C8E0
# systemIndigo#5856D6 / #5E5CE6 · systemPink #FF2D55 / #FF375F
# systemMint  #00C7BE / #63E6E2 · systemCyan #32ADE6 / #64D2FF
# systemYellow#FFCC00 / #FFD60A · systemBrown #A2845E / #AC8E68

APPLE_BLUE_LIGHT = "#007AFF"
APPLE_BLUE_DARK = "#0A84FF"

SYSTEMATIC_COLORS = {
    # name: (light, dark)
    "blue": (APPLE_BLUE_LIGHT, APPLE_BLUE_DARK),
    "green": ("#34C759", "#30D158"),
    "red": ("#FF3B30", "#FF453A"),
    "orange": ("#FF9500", "#FF9F0A"),
    "yellow": ("#FFCC00", "#FFD60A"),
    "purple": ("#AF52DE", "#BF5AF2"),
    "pink": ("#FF2D55", "#FF375F"),
    "teal": ("#30B0C7", "#40C8E0"),
    "indigo": ("#5856D6", "#5E5CE6"),
    "mint": ("#00C7BE", "#63E6E2"),
    "cyan": ("#32ADE6", "#64D2FF"),
    "brown": ("#A2845E", "#AC8E68"),
    "gray": ("#8E8E93", "#8E8E93"),
}


def rgba(hex_color: str, alpha: float) -> str:
    """Hex color → Qt rgba() string with 0-1 alpha."""
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {round(alpha, 3)})"


# ─────────────────────────────────────────────────────────────────────────────
# Typography — Inter (SF Pro metrics), bundled in assets/fonts
# ─────────────────────────────────────────────────────────────────────────────
FONT_STACK = '"Inter", "Segoe UI Variable Text", "Segoe UI", sans-serif'
FONT_STACK_DISPLAY = '"Inter Display", "Inter", "Segoe UI Variable Display", "Segoe UI", sans-serif'

TYPE_SCALE = {
    # token: (size_px, weight, letter_spacing_px)
    "display": (40, 800, -1.2),    # hero numerals (3h 42m)
    "display_sm": (32, 800, -0.8),
    "title1": (26, 700, -0.6),     # page titles
    "title2": (19, 700, -0.3),
    "title3": (16, 600, -0.2),
    "headline": (14, 600, 0.0),    # section titles, card headers
    "body": (13, 400, 0.0),
    "body_medium": (13, 500, 0.0),
    "callout": (12, 500, 0.0),
    "caption": (11, 500, 0.0),
    "micro": (10, 700, 1.4),       # uppercase eyebrows / section headers
}


def type_css(token: str, color: str = None, family: str = None) -> str:
    """Generate a QSS font snippet for a type-scale token."""
    size, weight, tracking = TYPE_SCALE[token]
    parts = [f"font-size: {size}px", f"font-weight: {weight}"]
    if tracking:
        parts.append(f"letter-spacing: {tracking}px")
    if color:
        parts.append(f"color: {color}")
    if family:
        parts.append(f"font-family: {family}")
    return "; ".join(parts) + ";"


# ─────────────────────────────────────────────────────────────────────────────
# Radius & Spacing scales
# ─────────────────────────────────────────────────────────────────────────────
RADIUS = {
    "xs": 6,       # tags, tiny chips
    "sm": 8,       # small controls, tooltips
    "md": 10,      # buttons, inputs, rows, menu items
    "lg": 14,      # standard cards
    "xl": 18,      # hero cards, dialogs
    "xxl": 24,     # sheets
    "pill": 999,   # pills, toggles
}

SPACING = {
    "xxs": 4,
    "xs": 8,
    "sm": 12,
    "md": 16,
    "lg": 20,
    "xl": 24,
    "xxl": 32,
    "xxxl": 40,
}

# ─────────────────────────────────────────────────────────────────────────────
# Motion — Apple-style timing
# ─────────────────────────────────────────────────────────────────────────────
DURATION_FAST = 120
DURATION_BASE = 200
DURATION_SLOW = 320
DURATION_PAGE = 260

EASE_OUT = QEasingCurve.Type.OutCubic          # standard entrance
EASE_IN_OUT = QEasingCurve.Type.InOutCubic     # state changes
EASE_OUT_BACK = QEasingCurve.Type.OutBack      # playful pop (thumb, badges)
EASE_OUT_QUINT = QEasingCurve.Type.OutQuint    # silky page transitions


# ─────────────────────────────────────────────────────────────────────────────
# Elevation (subtle, Apple-like — not Material)
# ─────────────────────────────────────────────────────────────────────────────
SHADOW_CARD_DARK = "0 1px 3px rgba(0, 0, 0, 0.28)"
SHADOW_CARD_LIGHT = "0 1px 3px rgba(0, 0, 0, 0.06)"
# Note: Qt QSS ignores box-shadow; retained for documentation / custom painting.


# ─────────────────────────────────────────────────────────────────────────────
# Font bootstrap
# ─────────────────────────────────────────────────────────────────────────────
_FONTS_LOADED = False


def load_fonts() -> None:
    """Register bundled Inter families with Qt. Idempotent; safe to call once at startup.

    Must be called AFTER the QApplication instance exists (QFontDatabase requires it);
    the guard below skips gracefully otherwise.
    """
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return

    from PySide6.QtWidgets import QApplication
    if QApplication.instance() is None:
        try:
            from core.logger import logger
            logger.warning("Design system: load_fonts() called before QApplication; skipping")
        except Exception:
            pass
        return

    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if not fonts_dir.exists():
        return
    loaded = 0
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0:
            loaded += 1
    _FONTS_LOADED = True

    try:
        from core.logger import logger
        logger.info("Design system: loaded %d bundled font files from %s", loaded, fonts_dir)
    except Exception:
        pass


def fallback_font() -> QFont:
    """Best available UI font (used for painting contexts, not QSS)."""
    return QFont("Inter", 10)


# ─────────────────────────────────────────────────────────────────────────────
# Category colors — Apple palette mapping (used by charts & rows)
# ─────────────────────────────────────────────────────────────────────────────
def category_color(name: str, dark: bool) -> str:
    """Deterministic Apple-palette color for a category name."""
    idx = abs(hash(name)) % len(SYSTEMATIC_COLORS)
    key = list(SYSTEMATIC_COLORS.keys())[idx]
    return SYSTEMATIC_COLORS[key][1 if dark else 0]
