"""
tests/test_picker_regression.py — Comprehensive regression tests for:
1. Reusable process picker caller context (App Locker vs App Timer).
2. App Timer selection does not modify App Locker state.
3. App Locker selection does not modify App Timer state.
4. Friendly-name resolution (UWP/PE/fallback).
5. Icon extraction and fallback behavior.
6. System and helper process filtering safety model.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from database.repository import Repository
from protection.app_locker import AppLockerManager, SYSTEM_SAFE
from protection.core import ProtectionManager
from ui.widgets.process_picker import ProcessPickerDialog
from utils.icon_provider import AppIconProvider
from utils.win_utils import (
    clean_fallback_name,
    is_safe_lock_target,
    is_user_facing_application,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


# ─── 1. Picker Context & Titles ───────────────────────────────────────────────

def test_picker_context_and_title_for_app_locker(qapp):
    """Verify ProcessPickerDialog configured for App Locker mode."""
    dlg = ProcessPickerDialog(mode="locker")
    try:
        assert dlg.mode == "locker"
        assert dlg.title_text == "Add Application to App Locker"
        assert dlg.action_text == "Add to App Locker"

        title_lbl = dlg.findChild(QLabel, "picker_title")
        assert title_lbl is not None
        assert title_lbl.text() == "Add Application to App Locker"

        assert dlg._add_btn.text() == "Add to App Locker"
        assert "directly" in dlg.browse_desc_text.lower()
    finally:
        dlg.deleteLater()
        QApplication.processEvents()


def test_picker_context_and_title_for_app_timer(qapp):
    """Verify ProcessPickerDialog configured for App Timer mode has App Timer copy."""
    dlg = ProcessPickerDialog(mode="timer")
    try:
        assert dlg.mode == "timer"
        assert dlg.title_text == "Add Application to App Timer"
        assert dlg.action_text == "Add to App Timer"

        title_lbl = dlg.findChild(QLabel, "picker_title")
        assert title_lbl is not None
        assert title_lbl.text() == "Add Application to App Timer"

        assert dlg._add_btn.text() == "Add to App Timer"
        assert "time limit" in dlg.browse_desc_text.lower()
        # Verify no App Locker copy leaked into App Timer picker
        assert "locker" not in dlg.title_text.lower()
        assert "locker" not in dlg.action_text.lower()
        assert "locker" not in dlg.browse_desc_text.lower()
    finally:
        dlg.deleteLater()
        QApplication.processEvents()


def test_picker_custom_overrides(qapp):
    """Verify explicit custom titles/action text are respected."""
    dlg = ProcessPickerDialog(
        mode="focus",
        title_text="Add to Focus Session",
        action_text="Allow Application",
    )
    try:
        assert dlg.title_text == "Add to Focus Session"
        assert dlg.action_text == "Allow Application"
        assert dlg.findChild(QLabel, "picker_title").text() == "Add to Focus Session"
        assert dlg._add_btn.text() == "Allow Application"
    finally:
        dlg.deleteLater()
        QApplication.processEvents()


# ─── 2. Caller State Independence ─────────────────────────────────────────────

def test_app_timer_selection_does_not_modify_app_locker_state(tmp_path):
    """Configuring an App Timer must NOT lock the application in App Locker."""
    db_path = tmp_path / "separation_test.db"
    Repository.set_db_path_override(db_path)
    try:
        repo = Repository()
        alm = AppLockerManager(repo=repo)
        pm = ProtectionManager(repo)

        # Baseline: Ensure test app is not locked
        test_proc = "spotify.exe"
        assert alm.is_locked(test_proc) is False
        assert len(alm.get_locked_apps()) == 0

        # Simulate App Timer configuration
        timer_rule = {
            "limit_seconds": 1800,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [5, 1],
            "on_expire": "lock",
        }
        pm.limits.set_limit_rule(test_proc, timer_rule)

        # Verify App Timer rule is stored
        stored_rule = pm.limits.get_limit_rule(test_proc)
        assert stored_rule is not None
        assert stored_rule["limit_seconds"] == 1800

        # CRITICAL: App Locker must remain completely untouched
        assert alm.is_locked(test_proc) is False
        assert len(alm.get_locked_apps()) == 0
    finally:
        Repository.set_db_path_override(None)


def test_app_locker_selection_does_not_modify_app_timer_state(tmp_path):
    """Adding an application to App Locker must NOT create an App Timer."""
    db_path = tmp_path / "separation_test.db"
    Repository.set_db_path_override(db_path)
    try:
        repo = Repository()
        alm = AppLockerManager(repo=repo)
        pm = ProtectionManager(repo)

        test_proc = "discord.exe"
        # Baseline: Ensure no timer exists for test app
        assert pm.limits.get_limit_rule(test_proc) is None

        # Simulate App Locker addition
        ok = alm.add_locked_app(test_proc, "Discord", "C:\\test\\discord.exe")
        assert ok is True
        assert alm.is_locked(test_proc) is True

        # CRITICAL: App Timer must remain completely untouched
        assert pm.limits.get_limit_rule(test_proc) is None
    finally:
        Repository.set_db_path_override(None)


# ─── 3. Friendly-Name Resolution ──────────────────────────────────────────────

def test_clean_fallback_name_resolution():
    """Verify package IDs and ugly stems resolve to human-friendly display names."""
    cases = [
        ("ad2f1837.hpsupportassistant.exe", "HP Support Assistant"),
        ("fingersoft.hillclimbracing.exe", "Hill Climb Racing"),
        ("microsoft.microsoftsolitairecollection.exe", "Microsoft Solitaire Collection"),
        ("code.exe", "Code"),
        ("afterfx.exe", "Afterfx"),
        ("brave.exe", "Brave"),
        ("msedge.exe", "MS Edge"),
    ]
    for raw, expected in cases:
        result = clean_fallback_name(raw)
        assert result == expected, f"Failed resolving {raw} -> expected {expected}, got {result}"


# ─── 4. Icon Extraction & Fallback ────────────────────────────────────────────

def test_icon_provider_returns_valid_icon_and_caches(qapp):
    """Verify AppIconProvider returns a non-null QIcon and caches it."""
    provider = AppIconProvider()

    # Query icon for a real system/installed executable
    icon = provider.get_icon("explorer.exe")
    assert isinstance(icon, QIcon)
    assert not icon.isNull()

    # Second query should hit cache
    cached_icon = provider.get_icon("explorer.exe")
    assert cached_icon is icon

    # Query icon for completely unknown executable should fall back to valid file icon
    fallback_icon = provider.get_icon("unknown_nonexistent_xyz.exe")
    assert isinstance(fallback_icon, QIcon)
    assert not fallback_icon.isNull()


@pytest.mark.skipif(sys.platform != "win32", reason="App discovery scans the Windows Start Menu")
def test_picker_model_rows_have_icons(qapp):
    """Verify that rows in ProcessPickerDialog._model have non-null icons."""
    dlg = ProcessPickerDialog(mode="timer")
    try:
        model = dlg._model
        assert model.rowCount() > 0, "Picker model should discover installed applications"

        # Check first 20 items to verify icons are attached
        check_count = min(model.rowCount(), 20)
        for i in range(check_count):
            item = model.item(i)
            icon = item.icon()
            assert not icon.isNull(), f"Item {item.text()} at row {i} has a null icon"
    finally:
        dlg.deleteLater()
        QApplication.processEvents()


# ─── 5. Safety Model & Filtering ──────────────────────────────────────────────

def test_system_and_helper_filtering():
    """Verify safety validation and user-facing filtering remain strict."""
    # System processes: security validation reject
    for sys_proc in ["svchost.exe", "explorer.exe", "dwm.exe", "services.exe", "digitalwellbeing.exe"]:
        assert is_safe_lock_target(f"C:\\Windows\\{sys_proc}", sys_proc) is False

    # Legitimate user-facing apps: security validation allow
    for app_proc in ["brave.exe", "msedge.exe", "code.exe", "discord.exe", "spotify.exe", "steam.exe"]:
        assert is_safe_lock_target(f"C:\\Apps\\{app_proc}", app_proc) is True

    # Background helpers: user-facing filter rejects
    assert is_user_facing_application(None, "C:\\App\\hpsystemeventutilitybackground.exe", "hpsystemeventutilitybackground.exe") is False
    assert is_user_facing_application(None, "C:\\App\\hpenhancedlighting.bg.exe", "hpenhancedlighting.bg.exe") is False
    assert is_user_facing_application(None, "C:\\App\\msteams_autostarter.exe", "msteams_autostarter.exe") is False
    assert is_user_facing_application(None, "C:\\App\\model3dtranscoderwin32.exe", "model3dtranscoderwin32.exe", display_name="OfficePushNotificationsUtility") is False

    # Legitimate user-facing apps: user-facing filter allows
    assert is_user_facing_application(None, "C:\\App\\hpsupportassistant.exe", "hpsupportassistant.exe", display_name="HP Support Assistant") is True
    assert is_user_facing_application(None, "C:\\App\\hillclimbracing.exe", "hillclimbracing.exe", display_name="Hill Climb Racing") is True
    assert is_user_facing_application(None, "C:\\App\\solitaire.exe", "solitaire.exe", display_name="Solitaire & Casual Games") is True


# ─── 6. Sidebar Navigation Icons ──────────────────────────────────────────────

def test_sidebar_app_timer_icon_exists(qapp):
    """Verify that App Timer has a valid, non-blank icon in the navigation system."""
    from ui.icons import get_icon, ICONS

    # 1. Verify clock and timer are in ICONS definition
    assert "clock" in ICONS, "clock must be defined in ICONS"
    assert "timer" in ICONS, "timer must be defined in ICONS"

    # 2. Verify get_icon('clock') renders a valid icon with non-zero pixels
    clock_icon = get_icon("clock")
    assert not clock_icon.isNull(), "get_icon('clock') returned a null QIcon"
    clock_pm = clock_icon.pixmap(24, 24)
    clock_img = clock_pm.toImage()
    clock_visible_pixels = sum(
        1 for y in range(clock_img.height()) for x in range(clock_img.width())
        if (clock_img.pixel(x, y) >> 24) & 0xFF > 0
    )
    assert clock_visible_pixels > 50, f"clock icon rendered blank ({clock_visible_pixels} pixels)"

    # 3. Verify get_icon('timer') renders a valid icon with non-zero pixels
    timer_icon = get_icon("timer")
    assert not timer_icon.isNull(), "get_icon('timer') returned a null QIcon"
    timer_pm = timer_icon.pixmap(24, 24)
    timer_img = timer_pm.toImage()
    timer_visible_pixels = sum(
        1 for y in range(timer_img.height()) for x in range(timer_img.width())
        if (timer_img.pixel(x, y) >> 24) & 0xFF > 0
    )
    assert timer_visible_pixels > 50, f"timer icon rendered blank ({timer_visible_pixels} pixels)"

