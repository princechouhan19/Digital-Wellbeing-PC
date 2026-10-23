"""
tests/test_browser_timer_flow.py — Comprehensive tests for the Browser Timer Choice Flow:
1. Normal application does not show browser choice.
2. Chrome shows browser choice.
3. Edge shows browser choice if recognized.
4. Brave shows browser choice if recognized.
5. Firefox shows browser choice if recognized.
6. "Entire Browser" opens existing application timer configuration.
7. "Specific Websites" opens existing website timer configuration.
8. Creating Entire Browser timer creates ONLY an application timer.
9. Creating Website timer creates ONLY a website timer.
10. Existing website timer behavior remains unchanged.
11. Existing application timer behavior remains unchanged.
12. App Locker remains independent.
13. Focus Mode remains independent.
14. Editing existing application timer does not show browser-choice flow.
15. Editing existing website timer remains website editing.
16. Dark theme rendering.
17. Light theme rendering.
18. Long browser names handling.
19. Canceling browser-choice dialog does not create a timer.
20. Back navigation / canceling configuration does not create duplicate timers.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QDialog

from database.repository import Repository
from protection.core import ProtectionManager
from protection.app_locker import AppLockerManager
from protection.focus_manager import FocusManager
from ui.pages.app_timer import (
    AppTimerPage,
    BrowserTimerChoiceDialog,
    AddTimerChoiceDialog,
    is_browser_app,
)
from ui.widgets.website_timer_widgets import WebsiteTimerConfigDialog
from ui.theme import ThemeManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def mock_repo(tmp_path):
    db_path = tmp_path / "browser_timer_flow_test.db"
    Repository.set_db_path_override(db_path)
    repo = Repository()
    yield repo
    Repository.set_db_path_override(None)


@pytest.fixture
def pm(mock_repo):
    return ProtectionManager(mock_repo)


# ============================================================================
# 1. NORMAL APPLICATION DOES NOT SHOW BROWSER CHOICE
# ============================================================================

def test_1_normal_application_does_not_show_browser_choice(qapp, pm):
    """Selecting normal applications (Discord, VS Code, Calculator, Spotify) bypasses browser choice."""
    normal_apps = [
        ("discord.exe", "Discord"),
        ("code.exe", "Visual Studio Code"),
        ("calc.exe", "Calculator"),
        ("spotify.exe", "Spotify"),
        ("notepad.exe", "Notepad"),
    ]
    for proc, disp in normal_apps:
        assert not is_browser_app(proc, disp), f"{proc} should not be recognized as a browser"

    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "discord.exe"
        mock_picker.selected_display_name = "Discord"

        mock_config = MagicMock()
        mock_config.exec.return_value = QDialog.DialogCode.Accepted
        mock_config.get_rule.return_value = {"limit_seconds": 3600}

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog") as mock_choice_cls, \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog", return_value=mock_config):
            page._on_add_app()
            # BrowserTimerChoiceDialog should NEVER be instantiated or executed
            mock_choice_cls.assert_not_called()
            # Standard application timer should be saved
            rule = pm.limits.get_limit_rule("discord.exe")
            assert rule is not None
            assert rule.get("limit_seconds") == 3600
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 2. CHROME SHOWS BROWSER CHOICE
# ============================================================================

def test_2_chrome_shows_browser_choice(qapp, pm):
    """Selecting Chrome (chrome.exe) shows the BrowserTimerChoiceDialog."""
    assert is_browser_app("chrome.exe", "Google Chrome")
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Rejected
        mock_choice.choice = None

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice) as mock_choice_cls:
            page._on_add_app()
            mock_choice_cls.assert_called_once()
            args, kwargs = mock_choice_cls.call_args
            assert kwargs.get("browser_name") == "Google Chrome"
            assert kwargs.get("process_name") == "chrome.exe"
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 3. EDGE SHOWS BROWSER CHOICE
# ============================================================================

def test_3_edge_shows_browser_choice(qapp, pm):
    """Selecting Edge (msedge.exe) shows the BrowserTimerChoiceDialog."""
    assert is_browser_app("msedge.exe", "Microsoft Edge")
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "msedge.exe"
        mock_picker.selected_display_name = "Microsoft Edge"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Rejected
        mock_choice.choice = None

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice) as mock_choice_cls:
            page._on_add_app()
            mock_choice_cls.assert_called_once()
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 4. BRAVE SHOWS BROWSER CHOICE
# ============================================================================

def test_4_brave_shows_browser_choice(qapp, pm):
    """Selecting Brave (brave.exe) shows the BrowserTimerChoiceDialog."""
    assert is_browser_app("brave.exe", "Brave Browser")
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "brave.exe"
        mock_picker.selected_display_name = "Brave Browser"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Rejected
        mock_choice.choice = None

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice) as mock_choice_cls:
            page._on_add_app()
            mock_choice_cls.assert_called_once()
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 5. FIREFOX SHOWS BROWSER CHOICE
# ============================================================================

def test_5_firefox_shows_browser_choice(qapp, pm):
    """Selecting Firefox (firefox.exe) shows the BrowserTimerChoiceDialog."""
    assert is_browser_app("firefox.exe", "Mozilla Firefox")
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "firefox.exe"
        mock_picker.selected_display_name = "Mozilla Firefox"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Rejected
        mock_choice.choice = None

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice) as mock_choice_cls:
            page._on_add_app()
            mock_choice_cls.assert_called_once()
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 6. "ENTIRE BROWSER" OPENS APPLICATION TIMER CONFIGURATION
# ============================================================================

def test_6_entire_browser_opens_application_timer_config(qapp, pm):
    """Selecting 'Entire Browser' in choice dialog opens standard TimerConfigDialog."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Accepted
        mock_choice.choice = "entire"

        mock_config = MagicMock()
        mock_config.exec.return_value = QDialog.DialogCode.Accepted
        mock_config.get_rule.return_value = {"limit_seconds": 7200}

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog", return_value=mock_config) as mock_cfg_cls, \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog") as mock_web_cls:
            page._on_add_app()
            mock_cfg_cls.assert_called_once()
            mock_web_cls.assert_not_called()
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 7. "SPECIFIC WEBSITES" OPENS WEBSITE TIMER CONFIGURATION
# ============================================================================

def test_7_specific_websites_opens_website_timer_config(qapp, pm):
    """Selecting 'Specific Websites' in choice dialog opens WebsiteTimerConfigDialog with browser context."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Accepted
        mock_choice.choice = "websites"

        mock_web_cfg = MagicMock()
        mock_web_cfg.exec.return_value = QDialog.DialogCode.Accepted
        mock_web_cfg.get_data.return_value = ("youtube.com", {"limit_seconds": 3600})

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog", return_value=mock_web_cfg) as mock_web_cls, \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog") as mock_app_cls:
            page._on_add_app()
            mock_web_cls.assert_called_once()
            mock_app_cls.assert_not_called()
            kwargs = mock_web_cls.call_args[1]
            assert kwargs.get("browser_name") == "Google Chrome"
            assert kwargs.get("browser_process") == "chrome.exe"
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 8. CREATING ENTIRE BROWSER TIMER CREATES ONLY APPLICATION TIMER
# ============================================================================

def test_8_creating_entire_browser_creates_only_application_timer(qapp, pm):
    """Choosing Entire Browser sets rule in pm.limits and NOT in pm.website_limits."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Accepted
        mock_choice.choice = "entire"

        mock_config = MagicMock()
        mock_config.exec.return_value = QDialog.DialogCode.Accepted
        mock_config.get_rule.return_value = {"limit_seconds": 7200}

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog", return_value=mock_config):
            page._on_add_app()

        # Check App Limits
        app_rule = pm.limits.get_limit_rule("chrome.exe")
        assert app_rule is not None
        assert app_rule.get("limit_seconds") == 7200

        # Check Website Limits has no rules for chrome
        web_limits = pm.website_limits.get_all_limits("chrome.exe")
        assert len(web_limits) == 0
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 9. CREATING WEBSITE TIMER CREATES ONLY WEBSITE TIMER
# ============================================================================

def test_9_creating_website_timer_creates_only_website_timer(qapp, pm):
    """Choosing Specific Websites sets rule in pm.website_limits and NOT in pm.limits."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Accepted
        mock_choice.choice = "websites"

        mock_web_cfg = MagicMock()
        mock_web_cfg.exec.return_value = QDialog.DialogCode.Accepted
        mock_web_cfg.get_data.return_value = ("youtube.com", {"limit_seconds": 3600})

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog", return_value=mock_web_cfg):
            page._on_add_app()

        # Check Website Limits has youtube.com under chrome.exe
        rule = pm.website_limits.get_limit_rule("chrome.exe", "youtube.com")
        assert rule is not None
        assert rule.get("limit_seconds") == 3600

        # Check Application Limits has NO chrome.exe limit
        assert pm.limits.get_limit_rule("chrome.exe") is None
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 10. EXISTING WEBSITE TIMER BEHAVIOR REMAINS UNCHANGED
# ============================================================================

def test_10_existing_website_timer_behavior_remains_unchanged(qapp, pm):
    """Adding a website timer via generic '+ Add Timer -> Website Timer' flow still works with wildcard '*'."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_web_cfg = MagicMock()
        mock_web_cfg.exec.return_value = QDialog.DialogCode.Accepted
        mock_web_cfg.get_data.return_value = ("reddit.com", {"limit_seconds": 1800})

        with patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog", return_value=mock_web_cfg):
            page._on_add_website()

        rule = pm.website_limits.get_limit_rule("*", "reddit.com")
        assert rule is not None
        assert rule.get("limit_seconds") == 1800
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 11. EXISTING APPLICATION TIMER BEHAVIOR REMAINS UNCHANGED
# ============================================================================

def test_11_existing_application_timer_behavior_remains_unchanged(qapp, pm):
    """Direct application limit management via pm.limits remains 100% backward compatible."""
    pm.limits.set_limit_rule("slack.exe", {"limit_seconds": 2400})
    rule = pm.limits.get_limit_rule("slack.exe")
    assert rule is not None
    assert rule["limit_seconds"] == 2400
    assert pm.limits.get_limit("slack.exe") == 2400


# ============================================================================
# 12. APP LOCKER REMAINS INDEPENDENT
# ============================================================================

def test_12_app_locker_remains_independent(qapp, pm, mock_repo):
    """Creating browser application or website timers has zero side effects on App Locker."""
    locker = AppLockerManager(mock_repo)
    initial_locked = set(locker.get_locked_apps())

    # Create browser app timer
    pm.limits.set_limit_rule("chrome.exe", {"limit_seconds": 3600})
    # Create website timer
    pm.website_limits.set_limit_rule("chrome.exe", "youtube.com", {"limit_seconds": 1800})

    assert set(locker.get_locked_apps()) == initial_locked
    assert not locker.is_locked("chrome.exe")


# ============================================================================
# 13. FOCUS MODE REMAINS INDEPENDENT
# ============================================================================

def test_13_focus_mode_remains_independent(qapp, pm, mock_repo):
    """Creating browser application or website timers has zero side effects on Focus Mode."""
    focus = FocusManager(mock_repo)
    assert not focus.is_active

    pm.limits.set_limit_rule("msedge.exe", {"limit_seconds": 3600})
    pm.website_limits.set_limit_rule("msedge.exe", "github.com", {"limit_seconds": 1800})

    assert not focus.is_active


# ============================================================================
# 14. EDITING EXISTING APPLICATION TIMER DOES NOT SHOW BROWSER CHOICE
# ============================================================================

def test_14_editing_existing_application_timer_does_not_show_browser_choice(qapp, pm):
    """Editing an existing browser application timer opens TimerConfigDialog directly without asking."""
    pm.limits.set_limit_rule("chrome.exe", {"limit_seconds": 3600})
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_config = MagicMock()
        mock_config.exec.return_value = QDialog.DialogCode.Accepted
        mock_config.get_rule.return_value = {"limit_seconds": 5400}

        with patch("ui.pages.app_timer.BrowserTimerChoiceDialog") as mock_choice_cls, \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog", return_value=mock_config) as mock_cfg_cls:
            page._on_configure_item("app", "chrome.exe")
            mock_choice_cls.assert_not_called()
            mock_cfg_cls.assert_called_once()
            assert pm.limits.get_limit_rule("chrome.exe")["limit_seconds"] == 5400
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 15. EDITING EXISTING WEBSITE TIMER REMAINS WEBSITE EDITING
# ============================================================================

def test_15_editing_existing_website_timer_remains_website_editing(qapp, pm):
    """Editing an existing website timer opens WebsiteTimerConfigDialog directly without asking."""
    pm.website_limits.set_limit_rule("*", "netflix.com", {"limit_seconds": 3600})
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_web_cfg = MagicMock()
        mock_web_cfg.exec.return_value = QDialog.DialogCode.Accepted
        mock_web_cfg.get_data.return_value = ("netflix.com", {"limit_seconds": 7200})

        with patch("ui.pages.app_timer.BrowserTimerChoiceDialog") as mock_choice_cls, \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog", return_value=mock_web_cfg) as mock_web_cls:
            page._on_configure_item("website", "netflix.com")
            mock_choice_cls.assert_not_called()
            mock_web_cls.assert_called_once()
            assert pm.website_limits.get_limit_rule("*", "netflix.com")["limit_seconds"] == 7200
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 16. DARK THEME RENDERING
# ============================================================================

def test_16_dark_theme_rendering(qapp):
    """BrowserTimerChoiceDialog renders correctly with dark theme styling."""
    ThemeManager.instance().set_theme("dark")
    dialog = BrowserTimerChoiceDialog(browser_name="Google Chrome", process_name="chrome.exe")
    dialog.show()
    try:
        assert dialog.card_entire is not None
        assert dialog.card_websites is not None
        assert "Google Chrome" in dialog.card_entire.findChild(QLabel, "choiceCardDesc").text()
        assert "Google Chrome" in dialog.card_websites.findChild(QLabel, "choiceCardDesc").text()
    finally:
        dialog.hide()
        dialog.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 17. LIGHT THEME RENDERING
# ============================================================================

def test_17_light_theme_rendering(qapp):
    """BrowserTimerChoiceDialog renders correctly with light theme styling."""
    ThemeManager.instance().set_theme("light")
    dialog = BrowserTimerChoiceDialog(browser_name="Brave Browser", process_name="brave.exe")
    dialog.show()
    try:
        assert dialog.card_entire is not None
        assert dialog.card_websites is not None
        assert "Brave Browser" in dialog.card_entire.findChild(QLabel, "choiceCardDesc").text()
    finally:
        dialog.hide()
        dialog.deleteLater()
        ThemeManager.instance().set_theme("dark")
        QApplication.processEvents()


# ============================================================================
# 18. LONG BROWSER NAMES HANDLING
# ============================================================================

def test_18_long_browser_names_handling(qapp):
    """BrowserTimerChoiceDialog cleanly handles unusually long browser display names without crash or error."""
    long_browser = "Google Chrome Enterprise Dedicated Work Profile (Global Corporation Management)"
    dialog = BrowserTimerChoiceDialog(browser_name=long_browser, process_name="chrome.exe")
    dialog.show()
    try:
        desc_entire = dialog.card_entire.findChild(QLabel, "choiceCardDesc").text()
        assert long_browser in desc_entire
        assert dialog.card_entire.findChild(QLabel, "choiceCardDesc").wordWrap()
    finally:
        dialog.hide()
        dialog.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 19. CANCELING BROWSER-CHOICE DIALOG DOES NOT CREATE A TIMER
# ============================================================================

def test_19_canceling_browser_choice_dialog_creates_no_timer(qapp, pm):
    """Rejecting/canceling the browser choice dialog results in zero timers being created."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "chrome.exe"
        mock_picker.selected_display_name = "Google Chrome"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Rejected
        mock_choice.choice = None

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.app_timer_widgets.TimerConfigDialog") as mock_cfg, \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog") as mock_web:
            page._on_add_app()
            mock_cfg.assert_not_called()
            mock_web.assert_not_called()
            assert pm.limits.get_limit_rule("chrome.exe") is None
            assert len(pm.website_limits.get_all_limits("chrome.exe")) == 0
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()


# ============================================================================
# 20. BACK NAVIGATION / CANCELING CONFIG DOES NOT CREATE DUPLICATE TIMERS
# ============================================================================

def test_20_back_navigation_canceling_config_creates_no_timers(qapp, pm):
    """Choosing 'Specific Websites' but canceling in WebsiteTimerConfigDialog creates no timers."""
    page = AppTimerPage(protection_manager=pm)
    page.show()
    try:
        mock_picker = MagicMock()
        mock_picker.exec.return_value = QDialog.DialogCode.Accepted
        mock_picker.selected_process_name = "brave.exe"
        mock_picker.selected_display_name = "Brave"

        mock_choice = MagicMock()
        mock_choice.exec.return_value = QDialog.DialogCode.Accepted
        mock_choice.choice = "websites"

        mock_web_cfg = MagicMock()
        mock_web_cfg.exec.return_value = QDialog.DialogCode.Rejected  # User pressed Cancel

        with patch("ui.widgets.process_picker.ProcessPickerDialog", return_value=mock_picker), \
             patch("ui.pages.app_timer.BrowserTimerChoiceDialog", return_value=mock_choice), \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog", return_value=mock_web_cfg):
            page._on_add_app()
            assert len(pm.website_limits.get_all_limits("brave.exe")) == 0
            assert pm.limits.get_limit_rule("brave.exe") is None
    finally:
        page.hide()
        page.deleteLater()
        QApplication.processEvents()
