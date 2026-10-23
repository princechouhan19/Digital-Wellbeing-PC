"""
tests/test_unified_timer_dashboard.py — Comprehensive tests for the Unified Timer Dashboard:
1. No timers configured -> unified empty state ("No Timers Configured", "Set First Timer").
2. Only application timers -> applications displayed with APPLICATION badge.
3. Only website timers -> websites displayed with WEBSITE badge and domain.
4. Both application + website timers -> both displayed in one coherent list.
5. Active timer count includes correct timer types.
6. Exceeded count includes correct timer types.
7. Website timer usage is displayed correctly.
8. Application timer usage is displayed correctly.
9. Edit application timer still works.
10. Edit website timer still works.
11. Delete application timer still works.
12. Delete website timer still works.
13. App Locker remains independent (no side effects).
14. Focus Mode remains unaffected (no side effects).
15. Dark theme rendering.
16. Light theme rendering.
17. Empty state button interaction opens add timer choice.
18. Long application names rendering.
19. Long domains rendering.
20. Timer with Unlimited / zero limit handling.
21. Filter pills: ALL, APPLICATIONS, WEBSITES.
22. AddTimerChoiceDialog modal choices.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QProgressBar, QMessageBox

from database.repository import Repository
from protection.core import ProtectionManager
from protection.app_locker import AppLockerManager
from protection.focus_manager import FocusManager
from ui.pages.app_timer import (
    AppTimerPage,
    AddTimerChoiceDialog,
    _UnifiedTimerRow,
    _format_time_short,
    get_website_display_name,
)
from ui.theme import ThemeManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_repo(tmp_path):
    db_path = tmp_path / "unified_timer_test.db"
    Repository.set_db_path_override(db_path)
    repo = Repository()
    yield repo
    Repository.set_db_path_override(None)


@pytest.fixture
def pm(mock_repo):
    manager = ProtectionManager(mock_repo)
    return manager


# ============================================================================
# 1. EMPTY STATE & INITIAL RENDERING
# ============================================================================

def test_1_no_timers_configured_unified_empty_state(qapp, pm):
    """Empty state shows 'No Timers Configured', correct copy, and 'Set First Timer' button."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        assert not page._empty_frame.isHidden()
        assert page._filter_container.isHidden()
        assert len(page._timer_rows) == 0

        # Check copy
        empty_title = page._empty_frame.findChild(QLabel, "empty_title")
        assert empty_title is not None
        assert empty_title.text() == "No Timers Configured"

        empty_sub = page._empty_frame.findChild(QLabel, "empty_sub")
        assert empty_sub is not None
        assert "applications and websites" in empty_sub.text().lower()

        # Check Top KPI Cards
        assert page._kpi_active_timers.text() == "0 timers"
        assert page._kpi_over_limit.text() == "0 timers"
        assert page._kpi_resets.text() == "Resets at Midnight"
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 2. ONLY APPLICATION TIMERS
# ============================================================================

def test_2_only_application_timers_displayed(qapp, pm):
    """Only application timers configured -> displayed with APPLICATION badge, empty state hidden."""
    pm.limits.set_limit_rule("discord.exe", {
        "limit_seconds": 3600,
        "repeat_days": [0, 1, 2, 3, 4, 5, 6],
    })

    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        assert page._empty_frame.isHidden()
        assert not page._filter_container.isHidden()
        assert len(page._timer_rows) == 1

        row = page._timer_rows[0]
        assert row.timer_type == "app"
        assert row.identifier == "discord.exe"
        assert row._lbl_type_badge.text() == "APPLICATION"
        assert page._kpi_active_timers.text() == "1 timer"
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 3. ONLY WEBSITE TIMERS
# ============================================================================

def test_3_only_website_timers_displayed(qapp, pm):
    """Only website timers configured -> displayed with WEBSITE badge and domain, empty state hidden."""
    pm.website_limits.set_limit_rule("*", "youtube.com", {
        "limit_seconds": 1800,
        "repeat_days": [0, 1, 2, 3, 4, 5, 6],
    })

    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        assert page._empty_frame.isHidden()
        assert not page._filter_container.isHidden()
        assert len(page._timer_rows) == 1

        row = page._timer_rows[0]
        assert row.timer_type == "website"
        assert row.identifier == "youtube.com"
        assert row._lbl_type_badge.text() == "WEBSITE"
        assert row._lbl_name.text() == "YouTube"
        assert row._lbl_domain.text() == "youtube.com"
        assert page._kpi_active_timers.text() == "1 timer"
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 4. BOTH APPLICATION AND WEBSITE TIMERS
# ============================================================================

def test_4_both_app_and_website_timers_displayed(qapp, pm):
    """Both app and website timers configured -> both displayed in one coherent list."""
    pm.limits.set_limit_rule("chrome.exe", {"limit_seconds": 7200})
    pm.website_limits.set_limit_rule("*", "reddit.com", {"limit_seconds": 3600})

    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        assert page._empty_frame.isHidden()
        assert len(page._timer_rows) == 2

        types = {r.timer_type for r in page._timer_rows}
        assert types == {"app", "website"}

        identifiers = {r.identifier for r in page._timer_rows}
        assert identifiers == {"chrome.exe", "reddit.com"}
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 5. ACTIVE TIMER COUNT
# ============================================================================

def test_5_active_timer_count_aggregates_both_types(qapp, pm):
    """Active timer count combines active app timers and active website timers."""
    pm.limits.set_limit_rule("app1.exe", {"limit_seconds": 3600})
    pm.limits.set_limit_rule("app2.exe", {"limit_seconds": 1800})
    pm.website_limits.set_limit_rule("*", "twitter.com", {"limit_seconds": 2400})

    page = AppTimerPage(protection_manager=pm)
    try:
        assert page._kpi_active_timers.text() == "3 timers"
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 6. EXCEEDED TIMER COUNT
# ============================================================================

def test_6_exceeded_count_includes_both_types(qapp, pm):
    """Exceeded count includes both app and website timers exceeding their limits."""
    # App timer exceeded: limit 1000s, used 1200s
    pm.limits.set_limit_rule("game.exe", {"limit_seconds": 1000})
    pm.timer.add_time("game.exe", 1200.0)

    # Website timer exceeded: limit 500s, used 600s
    pm.website_limits.set_limit_rule("*", "twitch.tv", {"limit_seconds": 500})
    pm.website_timer.add_time("twitch.tv", 600.0)

    # Non-exceeded website timer: limit 3600s, used 100s
    pm.website_limits.set_limit_rule("*", "github.com", {"limit_seconds": 3600})
    pm.website_timer.add_time("github.com", 100.0)

    page = AppTimerPage(protection_manager=pm)
    try:
        assert page._kpi_over_limit.text() == "2 timers"
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 7. WEBSITE TIMER USAGE DISPLAY
# ============================================================================

def test_7_website_timer_usage_displayed_correctly(qapp, pm):
    """Website timer displays 32m used / 1h limit and remaining time correctly."""
    # 32m = 1920s used, 1h = 3600s limit -> 28m remaining
    pm.website_limits.set_limit_rule("*", "youtube.com", {"limit_seconds": 3600})
    pm.website_timer.add_time("youtube.com", 1920.0)

    page = AppTimerPage(protection_manager=pm)
    try:
        row = next(r for r in page._timer_rows if r.identifier == "youtube.com")
        assert "32m used  /  1h limit" in row._lbl_usage_text.text()
        assert "28m left" in row._lbl_remaining.text()
        assert row._progress_bar.value() == int((1920 / 3600) * 100)
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 8. APPLICATION TIMER USAGE DISPLAY
# ============================================================================

def test_8_application_timer_usage_displayed_correctly(qapp, pm):
    """Application timer displays 1h 24m used / 2h limit and remaining time correctly."""
    # 1h 24m = 5040s used, 2h = 7200s limit -> 36m remaining
    pm.limits.set_limit_rule("chrome.exe", {"limit_seconds": 7200})
    pm.timer.add_time("chrome.exe", 5040.0)

    page = AppTimerPage(protection_manager=pm)
    try:
        row = next(r for r in page._timer_rows if r.identifier == "chrome.exe")
        assert "1h 24m used  /  2h limit" in row._lbl_usage_text.text()
        assert "36m left" in row._lbl_remaining.text()
        assert row._progress_bar.value() == int((5040 / 7200) * 100)
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 9. EDIT APPLICATION TIMER
# ============================================================================

def test_9_edit_application_timer_updates_rule(qapp, pm):
    """Editing an application timer updates the stored rule."""
    pm.limits.set_limit_rule("spotify.exe", {"limit_seconds": 1800})
    page = AppTimerPage(protection_manager=pm)
    try:
        new_rule = {"limit_seconds": 3600, "repeat_days": [0, 1]}
        with patch("ui.widgets.app_timer_widgets.TimerConfigDialog.exec", return_value=True), \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog.get_rule", return_value=new_rule):
            page._on_configure_item("app", "spotify.exe")

        saved = pm.limits.get_limit_rule("spotify.exe")
        assert saved["limit_seconds"] == 3600
        assert saved["repeat_days"] == [0, 1]
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 10. EDIT WEBSITE TIMER
# ============================================================================

def test_10_edit_website_timer_updates_rule(qapp, pm):
    """Editing a website timer updates the stored rule."""
    pm.website_limits.set_limit_rule("*", "netflix.com", {"limit_seconds": 3600})
    page = AppTimerPage(protection_manager=pm)
    try:
        new_rule = {"limit_seconds": 7200, "repeat_days": [0, 1, 2, 3, 4, 5, 6]}
        with patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog.exec", return_value=True), \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog.get_data", return_value=("netflix.com", new_rule)):
            page._on_configure_item("website", "netflix.com")

        saved = pm.website_limits.get_limit_rule("*", "netflix.com")
        assert saved["limit_seconds"] == 7200
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 11. DELETE APPLICATION TIMER
# ============================================================================

def test_11_delete_application_timer_removes_timer(qapp, pm):
    """Deleting an application timer removes the limit and updates the page."""
    pm.limits.set_limit_rule("slack.exe", {"limit_seconds": 3600})
    page = AppTimerPage(protection_manager=pm)
    try:
        assert len(page._timer_rows) == 1
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
            page._on_remove_item("app", "slack.exe", "Slack")

        assert pm.limits.get_limit_rule("slack.exe") is None
        assert len(page._timer_rows) == 0
        assert not page._empty_frame.isHidden()
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 12. DELETE WEBSITE TIMER
# ============================================================================

def test_12_delete_website_timer_removes_timer(qapp, pm):
    """Deleting a website timer removes the limit and updates the page."""
    pm.website_limits.set_limit_rule("*", "instagram.com", {"limit_seconds": 1800})
    page = AppTimerPage(protection_manager=pm)
    try:
        assert len(page._timer_rows) == 1
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
            page._on_remove_item("website", "instagram.com", "Instagram")

        assert pm.website_limits.get_limit_rule("*", "instagram.com") is None
        assert len(page._timer_rows) == 0
        assert not page._empty_frame.isHidden()
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 13. APP LOCKER INDEPENDENCE
# ============================================================================

def test_13_app_locker_remains_independent(qapp, pm, mock_repo):
    """Adding, editing, or deleting timers NEVER alters App Locker state."""
    alm = AppLockerManager(repo=mock_repo)
    proc = "vlc.exe"
    assert alm.is_locked(proc) is False

    page = AppTimerPage(protection_manager=pm)
    try:
        # Add app timer
        pm.limits.set_limit_rule(proc, {"limit_seconds": 3600})
        page._refresh_timers()
        assert alm.is_locked(proc) is False
        assert len(alm.get_locked_apps()) == 0

        # Remove app timer
        with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Yes):
            page._on_remove_item("app", proc, "VLC")
        assert alm.is_locked(proc) is False
        assert len(alm.get_locked_apps()) == 0

        # Website timer operations also don't touch locker
        pm.website_limits.set_limit_rule("*", "tiktok.com", {"limit_seconds": 1800})
        page._refresh_timers()
        assert len(alm.get_locked_apps()) == 0
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 14. FOCUS MODE INDEPENDENCE
# ============================================================================

def test_14_focus_mode_remains_unaffected(qapp, pm, mock_repo):
    """Configuring or modifying timers has zero impact on Focus Mode state."""
    fm = FocusManager(repo=mock_repo)
    assert fm.is_active is False

    page = AppTimerPage(protection_manager=pm)
    try:
        pm.limits.set_limit_rule("code.exe", {"limit_seconds": 7200})
        pm.website_limits.set_limit_rule("*", "stackoverflow.com", {"limit_seconds": 3600})
        page._refresh_timers()

        assert fm.is_active is False
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 15. DARK THEME RENDERING
# ============================================================================

def test_15_dark_theme_rendering(qapp, pm):
    """AppTimerPage applies dark theme styles cleanly without errors."""
    page = AppTimerPage(protection_manager=pm)
    try:
        ThemeManager.instance().set_theme("dark")
        page._apply_theme(is_dark=True)
        assert page.styleSheet() != ""
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 16. LIGHT THEME RENDERING
# ============================================================================

def test_16_light_theme_rendering(qapp, pm):
    """AppTimerPage applies light theme styles cleanly without errors."""
    page = AppTimerPage(protection_manager=pm)
    try:
        ThemeManager.instance().set_theme("light")
        page._apply_theme(is_dark=False)
        assert page.styleSheet() != ""
    finally:
        ThemeManager.instance().set_theme("dark")
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 17. EMPTY STATE BUTTON INTERACTION
# ============================================================================

def test_17_empty_state_button_opens_add_timer(qapp, pm):
    """Clicking 'Set First Timer' invokes _on_add_timer()."""
    page = AppTimerPage(protection_manager=pm)
    try:
        with patch.object(page, "_on_add_timer") as mock_add:
            # Find the 'Set First Timer' button inside empty frame
            btn = page._empty_frame.findChild(QPushButton, "timer_primary_add_btn")
            assert btn is not None
            assert btn.text() == "Set First Timer"
            btn.click()
            mock_add.assert_called_once()
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 18. LONG APPLICATION NAMES
# ============================================================================

def test_18_long_application_names(qapp, pm):
    """Long application names are handled gracefully without truncation crashes."""
    long_name = "EnterpriseCloudResourceProvisioningServiceManagerClientExecutable.exe"
    pm.limits.set_limit_rule(long_name, {"limit_seconds": 3600})

    page = AppTimerPage(protection_manager=pm)
    try:
        assert len(page._timer_rows) == 1
        row = page._timer_rows[0]
        assert row.identifier == long_name.lower()
        assert row._lbl_name.text() != ""
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 19. LONG DOMAINS
# ============================================================================

def test_19_long_domains(qapp, pm):
    """Long domains are handled gracefully without formatting failures."""
    long_domain = "very-long-subdomain-analytics-engine-portal.cloudinfrastructure.aws.internal.co.uk"
    pm.website_limits.set_limit_rule("*", long_domain, {"limit_seconds": 1800})

    page = AppTimerPage(protection_manager=pm)
    try:
        assert len(page._timer_rows) == 1
        row = page._timer_rows[0]
        assert row.identifier == long_domain
        assert row._lbl_domain.text() == long_domain
    finally:
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 20. UNLIMITED LIMIT HANDLING
# ============================================================================

def test_20_unlimited_limit_handling(qapp):
    """Timer row with unlimited (0) limit displays Unlimited status pill."""
    row = _UnifiedTimerRow(
        timer_type="app",
        identifier="test.exe",
        display_name="Test App",
        secondary_text="test.exe",
        rule={"limit_seconds": 0},
        used_seconds=120.0
    )
    try:
        assert row._lbl_remaining.text() == "Unlimited"
        assert "2m used" in row._lbl_usage_text.text()
    finally:
        row.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 21. FILTER PILLS (ALL, APPLICATIONS, WEBSITES)
# ============================================================================

def test_21_filter_pills(qapp, pm):
    """Filter pills toggle row visibility between ALL, APPLICATIONS, and WEBSITES."""
    pm.limits.set_limit_rule("app.exe", {"limit_seconds": 3600})
    pm.website_limits.set_limit_rule("*", "site.com", {"limit_seconds": 1800})

    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        assert len(page._timer_rows) == 2
        app_row = next(r for r in page._timer_rows if r.timer_type == "app")
        web_row = next(r for r in page._timer_rows if r.timer_type == "website")

        # Default: ALL
        assert not app_row.isHidden()
        assert not web_row.isHidden()

        # Filter: APPLICATIONS
        page._btn_filter_apps.click()
        assert not app_row.isHidden()
        assert web_row.isHidden()

        # Filter: WEBSITES
        page._btn_filter_web.click()
        assert app_row.isHidden()
        assert not web_row.isHidden()

        # Back to: ALL
        page._btn_filter_all.click()
        assert not app_row.isHidden()
        assert not web_row.isHidden()
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 22. ADD TIMER CHOICE DIALOG MODAL
# ============================================================================

def test_22_add_timer_choice_dialog(qapp):
    """AddTimerChoiceDialog sets choice to 'app' or 'website' upon clicking cards."""
    dlg = AddTimerChoiceDialog()
    try:
        dlg._select_choice("app")
        assert dlg.choice == "app"

        dlg2 = AddTimerChoiceDialog()
        dlg2._select_choice("website")
        assert dlg2.choice == "website"
    finally:
        dlg.deleteLater()
        QApplication.processEvents()
