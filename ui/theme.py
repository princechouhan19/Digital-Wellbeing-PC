"""
theme.py — "Aurora" Apple Design System theme engine for Digital Wellbeing v4.0.

macOS Sequoia-inspired light/dark/system theming built on ui/design_system.py:
  • Apple system palette (systemBlue accent, semantic colors, Apple grays)
  • Soft-translucent layering: opaque cards on a subtle backdrop
  • Bundled Inter / Inter Display typography
  • Instant app-wide palette + stylesheet updates via theme_changed signal

Token names are backwards compatible with v3.x (aliases included) so every
existing subscriber continues to work — values now speak Apple.
"""

import os
from pathlib import Path
from typing import Optional, Union, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui import design_system as ds


def is_system_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return True


class ThemeManager(QObject):
    """Centralized Theme Manager for instant, app-wide UI updates."""
    _instance = None
    theme_changed = Signal(bool)  # Emits True if dark mode

    def __init__(self):
        super().__init__()
        self._is_dark = True
        self._tokens = {}

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    def resolve_dark_mode(self, theme_arg: Union[str, bool, None] = None) -> bool:
        if isinstance(theme_arg, bool):
            return theme_arg

        if theme_arg is None:
            try:
                from settings.manager import SettingsManager
                theme_arg = SettingsManager().theme
            except Exception:
                theme_arg = "dark"

        theme_str = str(theme_arg).lower()
        if theme_str == "system":
            return is_system_dark()
        if theme_str == "light":
            return False
        return True

    def set_theme(self, theme_arg: Union[str, bool, None] = None, app: Optional[QApplication] = None) -> None:
        if app is None:
            app = QApplication.instance()

        new_is_dark = self.resolve_dark_mode(theme_arg)
        self._is_dark = new_is_dark
        self._tokens = self._get_tokens(self._is_dark)

        if app:
            self._apply_palette(app, self._is_dark)
            self._apply_global_stylesheet(app, self._is_dark)

        # Notify all widgets to update dynamic styles
        self.theme_changed.emit(self._is_dark)

    def color(self, token: str, default: str = "transparent") -> str:
        """Get a specific theme color by token name."""
        return self._tokens.get(token, default)

    def font_stack(self) -> str:
        return ds.FONT_STACK

    # ─────────────────────────────────────────────────────────────────────
    # Apple palette (Aurora design system)
    # ─────────────────────────────────────────────────────────────────────
    def _get_tokens(self, dark_mode: bool) -> Dict[str, str]:
        if dark_mode:
            accent = ds.APPLE_BLUE_DARK                      # #0A84FF
            return self._compose(dark_mode, {
                # Surfaces — soft obsidian with opaque Apple-gray cards
                "bg": "#1A1A1C",
                "window_bg": "#1A1A1C",
                "sidebar_bg": "rgba(30, 30, 32, 0.72)",
                "surface": "#232326",
                "surface_elevated": "#2A2A2E",
                "surface_secondary": "rgba(255, 255, 255, 0.045)",
                "surface_hover": "rgba(255, 255, 255, 0.07)",
                "surface_pressed": "rgba(255, 255, 255, 0.10)",
                "card_bg": "#232326",
                "card_solid": "#232326",
                "card_hover": "#28282C",
                "card_pressed": "#1F1F22",
                "separator": "rgba(255, 255, 255, 0.06)",

                # Borders — Apple hairlines
                "border": "rgba(255, 255, 255, 0.08)",
                "border_strong": "rgba(255, 255, 255, 0.14)",
                "border_hover": "rgba(255, 255, 255, 0.20)",

                # Inputs — Apple tertiary gray
                "input_bg": "#2C2C2E",
                "input_border": "rgba(255, 255, 255, 0.10)",
                "input_hover": "rgba(255, 255, 255, 0.16)",

                # Text — Apple label ramp
                "text_main": "#F5F5F7",
                "text_sub": "#A1A1A6",
                "text_muted": "#6E6E73",

                "track": "rgba(255, 255, 255, 0.08)",
                "center_circle": "transparent",
                "grid": "rgba(255, 255, 255, 0.045)",
            }, accent)
        else:
            accent = ds.APPLE_BLUE_LIGHT                     # #007AFF
            return self._compose(dark_mode, {
                # Surfaces — Apple silver with white cards
                "bg": "#F5F5F7",
                "window_bg": "#F5F5F7",
                "sidebar_bg": "rgba(251, 251, 253, 0.78)",
                "surface": "#FFFFFF",
                "surface_elevated": "#FFFFFF",
                "surface_secondary": "rgba(0, 0, 0, 0.035)",
                "surface_hover": "rgba(0, 0, 0, 0.05)",
                "surface_pressed": "rgba(0, 0, 0, 0.08)",
                "card_bg": "#FFFFFF",
                "card_solid": "#FFFFFF",
                "card_hover": "#FBFBFD",
                "card_pressed": "#F2F2F5",
                "separator": "rgba(0, 0, 0, 0.07)",

                # Borders — Apple hairlines
                "border": "rgba(0, 0, 0, 0.08)",
                "border_strong": "rgba(0, 0, 0, 0.14)",
                "border_hover": "rgba(0, 0, 0, 0.22)",

                # Inputs
                "input_bg": "#FFFFFF",
                "input_border": "rgba(0, 0, 0, 0.12)",
                "input_hover": "rgba(0, 0, 0, 0.20)",

                # Text — Apple label ramp
                "text_main": "#1D1D1F",
                "text_sub": "#6E6E73",
                "text_muted": "#98989D",

                "track": "rgba(0, 0, 0, 0.07)",
                "center_circle": "transparent",
                "grid": "rgba(0, 0, 0, 0.05)",
            }, accent)

    def _compose(self, dark_mode: bool, base: Dict[str, str], accent: str) -> Dict[str, str]:
        """Compose the full token dict from base surfaces + accent-derived semantics."""
        semantic = {
            # Apple semantic colors: (light, dark)
            "success": ("#34C759", "#30D158"),
            "warning": ("#FF9500", "#FF9F0A"),
            "danger": ("#FF3B30", "#FF453A"),
            "danger_soft": ("#FF3B30", "#FF6B61"),
            "info": ("#32ADE6", "#64D2FF"),
            "indigo": ("#5856D6", "#5E5CE6"),
            "purple": ("#AF52DE", "#BF5AF2"),
            "pink": ("#FF2D55", "#FF375F"),
            "teal": ("#30B0C7", "#40C8E0"),
            "mint": ("#00C7BE", "#63E6E2"),
            "yellow": ("#FFCC00", "#FFD60A"),
            "brown": ("#A2845E", "#AC8E68"),
        }
        i = 1 if dark_mode else 0
        tokens: Dict[str, str] = dict(base)

        # Accent (system blue)
        accent_hover = "#409CFF" if dark_mode else "#0071EB"
        accent_pressed = "#0060DF" if dark_mode else "#005EC4"
        tokens.update({
            "accent": accent,
            "accent_hover": accent_hover,
            "accent_pressed": accent_pressed,
            "accent_tint_bg": ds.rgba(accent, 0.16 if dark_mode else 0.12),
            "accent_tint_border": ds.rgba(accent, 0.34 if dark_mode else 0.30),
            "accent_tint_text": accent_hover if dark_mode else accent,
            "accent_hover_bg": ds.rgba(accent, 0.24),
            # Legacy aliases (v3.x names) → accent tints
            "accent_emerald_bg": ds.rgba(accent, 0.16 if dark_mode else 0.12),
            "accent_amber": semantic["warning"][i],
            "accent_amber_hover": semantic["warning"][i],
            "accent_amber_bg": ds.rgba(semantic["warning"][i], 0.14),

            # Apple buttons are flat — "gradients" collapse to solid fills
            "primary_btn_gradient": accent,
            "primary_btn_hover": accent_hover,
        })

        # Semantic families with tinted bg / border / text variants
        for name, (light_v, dark_v) in semantic.items():
            v = dark_v if dark_mode else light_v
            tokens[f"{name}_bg"] = ds.rgba(v, 0.16 if dark_mode else 0.11)
            tokens[f"{name}_border"] = ds.rgba(v, 0.32)
            tokens[f"{name}_text"] = v
        # Legacy aliases
        tokens["success_text"] = tokens["success_text"]
        tokens["indigo_bg"] = ds.rgba(semantic["indigo"][i], 0.16 if dark_mode else 0.11)
        tokens["window_gradient"] = "transparent"
        return tokens

    def _apply_palette(self, app: QApplication, dark_mode: bool) -> None:
        palette = QPalette()
        if dark_mode:
            palette.setColor(QPalette.ColorRole.Window, QColor("#1A1A1C"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#232326"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2A2A2E"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#2A2A2E"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#2C2C2E"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.Link, QColor(ds.APPLE_BLUE_DARK))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(ds.APPLE_BLUE_DARK))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(255, 255, 255, 80))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(255, 255, 255, 80))
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#1D1D1F"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F5F5F7"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1D1D1F"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#1D1D1F"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1D1D1F"))
            palette.setColor(QPalette.ColorRole.BrightText, QColor("#000000"))
            palette.setColor(QPalette.ColorRole.Link, QColor(ds.APPLE_BLUE_LIGHT))
            palette.setColor(QPalette.ColorRole.Highlight, QColor(ds.APPLE_BLUE_LIGHT))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(0, 0, 0, 80))
            palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(0, 0, 0, 80))
        app.setPalette(palette)

    def _apply_global_stylesheet(self, app: QApplication, dark_mode: bool) -> None:
        scroll_handle = "rgba(255, 255, 255, 0.14)" if dark_mode else "rgba(0, 0, 0, 0.14)"
        scroll_hover = "rgba(255, 255, 255, 0.28)" if dark_mode else "rgba(0, 0, 0, 0.28)"
        selection_bg = self.color("accent_tint_bg")

        glass_styles = f"""
        QWidget {{
            color: {self.color('text_main')};
            font-family: {ds.FONT_STACK};
            font-size: 13px;
            border: none;
            outline: none;
        }}
        QMainWindow, QWidget#content_area {{
            background: {self.color('bg')};
        }}

        /* ─── Scrollbars — macOS overlay style ──────────────────────────────── */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 8px; margin: 2px; }}
        QScrollBar::handle:vertical {{ background: {scroll_handle}; min-height: 36px; border-radius: 3px; }}
        QScrollBar::handle:vertical:hover {{ background: {scroll_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{ border: none; background: transparent; height: 8px; margin: 2px; }}
        QScrollBar::handle:horizontal {{ background: {scroll_handle}; min-width: 36px; border-radius: 3px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

        /* ─── Cards — Apple inset grouped style ─────────────────────────────── */
        QFrame#v2_card, QFrame#stat_card {{
            background-color: {self.color('card_bg')};
            border: 1px solid {self.color('border')};
            border-radius: {ds.RADIUS['lg']}px;
        }}
        QFrame#v2_card:hover, QFrame#stat_card:hover {{
            background-color: {self.color('card_hover')};
            border: 1px solid {self.color('border_hover')};
        }}

        QFrame#dense_card {{
            background-color: {self.color('card_bg')};
            border: 1px solid {self.color('border')};
            border-radius: {ds.RADIUS['lg']}px;
        }}
        QFrame#dense_card:hover {{
            border: 1px solid {self.color('border_hover')};
        }}

        /* ─── Inputs — Apple continuous feel ────────────────────────────────── */
        QComboBox, QSpinBox, QLineEdit {{
            background-color: {self.color('input_bg')};
            border: 1px solid {self.color('input_border')};
            border-radius: {ds.RADIUS['md']}px;
            padding: 8px 12px;
            color: {self.color('text_main')};
            font-size: 13px;
            selection-background-color: {self.color('accent')};
            selection-color: #FFFFFF;
        }}
        QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{
            border-color: {self.color('input_hover')};
        }}
        QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{
            border: 1px solid {self.color('accent')};
            background-color: {self.color('surface_elevated')};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {self.color('text_sub')}; width: 0; height: 0; margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {self.color('surface_elevated')};
            border: 1px solid {self.color('border_strong')};
            border-radius: {ds.RADIUS['md']}px;
            selection-background-color: {selection_bg};
            selection-color: {self.color('accent_tint_text')};
            padding: 4px;
            outline: none;
            color: {self.color('text_main')};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 8px 12px;
            border-radius: {ds.RADIUS['sm']}px;
            color: {self.color('text_main')};
            background-color: transparent;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {self.color('surface_hover')};
            color: {self.color('text_main')};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {selection_bg};
            color: {self.color('accent_tint_text')};
        }}

        /* ─── Menus — Apple context menus ───────────────────────────────────── */
        QMenu {{
            background-color: {self.color('surface_elevated')};
            border: 1px solid {self.color('border_strong')};
            border-radius: {ds.RADIUS['md']}px;
            padding: 5px;
            color: {self.color('text_main')};
        }}
        QMenu::item {{
            padding: 7px 20px;
            border-radius: {ds.RADIUS['sm']}px;
            color: {self.color('text_main')};
            background-color: transparent;
        }}
        QMenu::item:hover, QMenu::item:selected {{
            background-color: {self.color('accent')};
            color: #FFFFFF;
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {self.color('separator')};
            margin: 5px 10px;
        }}

        /* ─── Progress ──────────────────────────────────────────────────────── */
        QProgressBar {{
            background-color: {self.color('track')};
            border: none;
            border-radius: 4px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background-color: {self.color('accent')};
            border-radius: 4px;
        }}

        /* ─── Checkbox — Apple rounded ──────────────────────────────────────── */
        QCheckBox {{
            color: {self.color('text_main')};
            spacing: 10px;
            font-size: 13px;
            font-weight: 500;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 6px;
            border: 1px solid {self.color('input_border')};
            background-color: {self.color('input_bg')};
        }}
        QCheckBox::indicator:hover {{
            border-color: {self.color('accent')};
        }}
        QCheckBox::indicator:checked {{
            background-color: {self.color('accent')};
            border-color: {self.color('accent')};
        }}

        /* ─── Tooltip ───────────────────────────────────────────────────────── */
        QToolTip {{
            background-color: {self.color('surface_elevated')};
            color: {self.color('text_main')};
            border: 1px solid {self.color('border_strong')};
            border-radius: {ds.RADIUS['sm']}px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        """

        app.setStyleSheet(glass_styles)

def apply_mica(hwnd: int, dark_mode: bool = True) -> None:
    """Tints the Windows 11 title bar / backdrop to match the Aurora window base."""
    try:
        import ctypes
        from ctypes.wintypes import DWORD, BOOL, HWND
        import sys

        if sys.platform != "win32":
            return

        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2  # Mica — subtle, window-tinted backdrop under the solid base

        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute

        # Enable dark mode context
        value = ctypes.c_int(1 if dark_mode else 0)
        set_window_attribute(HWND(hwnd), DWORD(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(value), ctypes.sizeof(value))

        # Enable Mica (visible only in unpainted margins; base coat is solid)
        backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)
        set_window_attribute(HWND(hwnd), DWORD(DWMWA_SYSTEMBACKDROP_TYPE), ctypes.byref(backdrop), ctypes.sizeof(backdrop))
    except Exception as e:
        from core.logger import logger
        logger.warning(f"Failed to apply Mica backdrop: {e}")


# Legacy bindings mapped to ThemeManager for compatibility
def apply_theme(app: Optional[QApplication] = None, theme_arg: Union[str, bool, None] = None) -> None:
    ThemeManager.instance().set_theme(theme_arg, app)

def get_theme_tokens(dark_mode: Optional[bool] = None) -> dict[str, str]:
    # Used strictly by old code, redirect to ThemeManager tokens
    is_dark = dark_mode if dark_mode is not None else ThemeManager.instance().is_dark
    return ThemeManager.instance()._get_tokens(is_dark)

def get_app_color(app_name: str) -> str:
    """Returns a deterministic accent color for a given application (Apple palette)."""
    if not app_name:
        return "#64D2FF"

    name = app_name.lower().replace(".exe", "")

    brand_colors = {
        "brave": "#FB542B",
        "chrome": "#4285F4",
        "spotify": "#1DB954",
        "code": "#007ACC",
        "github": "#8E8E93",
        "discord": "#5865F2",
        "steam": "#1B2838",
        "chatgpt": "#10A37F",
        "explorer": "#5C8BA6",
        "msedge": "#0078D7",
        "firefox": "#FF7139",
    }

    if name in brand_colors:
        return brand_colors[name]

    # Generate deterministic color from hash (Apple-palette hues, HSL)
    import hashlib
    hash_val = int(hashlib.md5(name.encode()).hexdigest(), 16)

    hue = hash_val % 360
    if 260 <= hue <= 310:
        hue = (hue + 60) % 360

    sat = 58 + (hash_val % 18)   # 58-76% — Apple vibrancy, not oversaturated
    light = 52 + (hash_val % 10) # 52-62% lightness

    # Convert HSL to HEX
    return QColor.fromHsl(hue, int(sat * 2.55), int(light * 2.55)).name()
