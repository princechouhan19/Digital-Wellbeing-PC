"""
tests/test_theme_system.py - Unit tests for ThemeManager, theme resolution, and token verification.
"""
import pytest
from PySide6.QtWidgets import QApplication
from ui.theme import ThemeManager, is_system_dark
from settings.manager import SettingsManager

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_theme_resolution_explicit(qapp):
    tm = ThemeManager.instance()
    assert tm.resolve_dark_mode("dark") is True
    assert tm.resolve_dark_mode("light") is False
    assert tm.resolve_dark_mode(True) is True
    assert tm.resolve_dark_mode(False) is False
    assert tm.resolve_dark_mode("system") == is_system_dark()

def test_theme_tokens_light_vs_dark(qapp):
    tm = ThemeManager.instance()
    
    # Test Dark Mode Tokens (Aurora — Apple palette)
    tm.set_theme("dark", app=qapp)
    assert tm.is_dark is True
    assert tm.color("text_main") == "#F5F5F7"
    assert tm.color("accent") == "#0A84FF"          # Apple systemBlue (dark)
    assert tm.color("card_bg") == "#232326"
    assert tm.color("accent_emerald_bg") == tm.color("accent_tint_bg")  # legacy alias

    # Test Light Mode Tokens
    tm.set_theme("light", app=qapp)
    assert tm.is_dark is False
    assert tm.color("text_main") == "#1D1D1F"
    assert tm.color("text_sub") == "#6E6E73"
    assert tm.color("text_muted") == "#98989D"
    assert tm.color("accent") == "#007AFF"          # Apple systemBlue (light)
    assert tm.color("card_bg") == "#FFFFFF"

def test_aurora_design_system(qapp):
    """The Aurora design system is the single source of truth for palette + scales."""
    from ui import design_system as ds
    assert ds.APPLE_BLUE_LIGHT == "#007AFF"
    assert ds.APPLE_BLUE_DARK == "#0A84FF"
    assert ds.RADIUS["lg"] == 14 and ds.RADIUS["md"] == 10
    assert ds.DURATION_BASE == 200
    # All 12 categories have colors in both themes
    from core.constants import AppCategory, CATEGORY_COLORS, CATEGORY_COLORS_LIGHT
    for cat in AppCategory:
        assert cat in CATEGORY_COLORS
        assert cat in CATEGORY_COLORS_LIGHT

def test_theme_changed_signal(qapp):
    tm = ThemeManager.instance()
    emitted_values = []
    
    def on_theme_changed(is_dark: bool):
        emitted_values.append(is_dark)
        
    tm.theme_changed.connect(on_theme_changed)
    try:
        tm.set_theme("dark", app=qapp)
        tm.set_theme("light", app=qapp)
        tm.set_theme("dark", app=qapp)
        
        assert emitted_values[-3:] == [True, False, True]
    finally:
        tm.theme_changed.disconnect(on_theme_changed)

def test_settings_manager_theme_storage():
    sm = SettingsManager()
    orig = sm.theme
    try:
        sm.theme = "light"
        assert sm.theme == "light"
        sm.theme = "system"
        assert sm.theme == "system"
        sm.theme = "dark"
        assert sm.theme == "dark"
    finally:
        sm.theme = orig
