import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from settings.manager import SettingsManager
from ui.pages.settings import SettingsPage
from ui.pages.tasks import TaskEditDialog
from ui.styles.focus import build_focus_stylesheet
from ui.theme import ThemeManager
from ui.widgets.focus_timer import AppleFocusRing, FocusTimerWidget


def test_liquid_glass_settings_toggle(qapp):
    sm = SettingsManager()
    # Default is True
    original = sm.liquid_glass_enabled
    try:
        sm.liquid_glass_enabled = False
        assert sm.liquid_glass_enabled is False

        sm.liquid_glass_enabled = True
        assert sm.liquid_glass_enabled is True
    finally:
        sm.liquid_glass_enabled = original


def test_liquid_glass_stylesheet_generation():
    tm = ThemeManager.instance()
    # Liquid glass dark
    qss_glass = build_focus_stylesheet(tm, "#0A84FF", is_dark=True, liquid_glass=True)
    assert "rgba(24, 24, 30, 0.78)" in qss_glass
    assert "border-top: 1px solid rgba(255, 255, 255, 0.28)" in qss_glass

    # Classic solid dark
    qss_solid = build_focus_stylesheet(tm, "#0A84FF", is_dark=True, liquid_glass=False)
    assert "border-top: 1px solid rgba(255, 255, 255, 0.28)" not in qss_solid


def test_focus_ring_and_widget_liquid_glass(qapp):
    ring = AppleFocusRing()
    ring.update_state("25:00", 0.5, "Deep Focus", "Active", "#0A84FF", is_active=True)
    ring.show()
    QApplication.processEvents()
    ring.hide()

    widget = FocusTimerWidget()
    widget.update_theme_style()
    assert widget is not None


def test_task_edit_dialog_no_clipping(qapp):
    dialog = TaskEditDialog()
    dialog.show()
    QApplication.processEvents()

    # Verify that Saturday and Sunday are within dialog geometry
    assert len(dialog._day_buttons) == 7
    sun_btn = dialog._day_buttons[6]
    assert sun_btn.geometry().right() <= dialog.width()
    # Verify cat_combo is placed cleanly without overflow
    assert dialog._cat_combo.geometry().right() <= dialog.width()
    dialog.hide()
