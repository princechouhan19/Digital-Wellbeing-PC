"""
tests/test_v361_stability.py — Focused regression tests for v3.6.1 stability:
1. Browser-specific website limit is strictly scoped to the target browser.
2. Browser-specific website limit does NOT leak to other browsers.
3. Global wildcard website limits are enforced across all browsers.
4. get_browser_for_domain accurately identifies owning browser or wildcard.
5. Editing website timers in AppTimerPage preserves the original browser context.
6. ProtectionManager resets warnings_sent at midnight rollover.
7. ProtectionManager prunes expired overrides at midnight rollover.
8. Website override resets warning sent history so expiration toast fires.
9. TimerEngine resets to 0.0 and advances date on read when midnight crosses.
10. WebsiteTimerEngine resets to 0.0 and advances date on read when midnight crosses.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtWidgets import QApplication

from database.repository import Repository
from protection.core import ProtectionManager
from protection.website_limits import WebsiteLimitManager
from protection.timer import TimerEngine
from protection.website_timer import WebsiteTimerEngine
from ui.pages.app_timer import AppTimerPage


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


@pytest.fixture
def test_repo(tmp_path):
    db_path = tmp_path / "test_v361_stability.db"
    Repository.set_db_path_override(db_path)
    repo = Repository()
    yield repo
    Repository.set_db_path_override(None)


@pytest.fixture
def pm(test_repo):
    return ProtectionManager(test_repo)


# ==============================================================================
# 1. Browser-Specific Website Limits Scoping
# ==============================================================================

class TestBrowserSpecificLimits:
    def test_browser_specific_limit_does_not_leak_to_other_browsers(self, test_repo):
        wlm = WebsiteLimitManager(test_repo)
        rule = {
            "limit_seconds": 1800,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock",
        }
        wlm.set_limit_rule("chrome.exe", "youtube.com", rule)

        # 1. Target browser has rule
        assert wlm.get_limit_rule("chrome.exe", "youtube.com") is not None
        assert wlm.get_limit("chrome.exe", "youtube.com") == 1800

        # 2. Other browsers MUST NOT have rule
        assert wlm.get_limit_rule("firefox.exe", "youtube.com") is None
        assert wlm.get_limit("firefox.exe", "youtube.com") is None

        assert wlm.get_limit_rule("msedge.exe", "youtube.com") is None
        assert wlm.get_limit("msedge.exe", "youtube.com") is None

        assert wlm.get_limit_rule("brave.exe", "youtube.com") is None
        assert wlm.get_limit("brave.exe", "youtube.com") is None

    def test_global_wildcard_limit_applies_to_all_browsers(self, test_repo):
        wlm = WebsiteLimitManager(test_repo)
        rule = {
            "limit_seconds": 3600,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock",
        }
        wlm.set_limit_rule("*", "reddit.com", rule)

        assert wlm.get_limit_rule("chrome.exe", "reddit.com") is not None
        assert wlm.get_limit_rule("firefox.exe", "reddit.com") is not None
        assert wlm.get_limit_rule("msedge.exe", "reddit.com") is not None
        assert wlm.get_limit_rule("brave.exe", "reddit.com") is not None
        assert wlm.get_limit_rule("*", "reddit.com") is not None

    def test_get_browser_for_domain_finds_correct_owning_browser(self, test_repo):
        wlm = WebsiteLimitManager(test_repo)
        rule = {"limit_seconds": 1200, "repeat_days": [0, 1, 2, 3, 4, 5, 6]}
        wlm.set_limit_rule("chrome.exe", "twitter.com", rule)
        wlm.set_limit_rule("*", "wikipedia.org", rule)

        assert wlm.get_browser_for_domain("twitter.com") == "chrome.exe"
        assert wlm.get_browser_for_domain("www.twitter.com") == "chrome.exe"
        assert wlm.get_browser_for_domain("wikipedia.org") == "*"
        assert wlm.get_browser_for_domain("unknown-domain.io") is None


# ==============================================================================
# 2. UI Editing Preserves Browser Context
# ==============================================================================

class TestUIEditingPreservesBrowserContext:
    def test_edit_website_timer_retains_browser_context(self, qapp, test_repo, pm):
        wlm = pm.website_limits
        initial_rule = {
            "limit_seconds": 1800,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock",
        }
        wlm.set_limit_rule("chrome.exe", "twitch.tv", initial_rule)

        page = AppTimerPage(protection_manager=pm)

        # Mock WebsiteTimerConfigDialog to return updated limit
        updated_rule = {
            "limit_seconds": 2400,
            "repeat_days": [0, 1, 2, 3, 4, 5, 6],
            "notifications": [15, 10, 5, 1],
            "on_expire": "lock",
        }

        with patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog.exec", return_value=1), \
             patch("ui.widgets.website_timer_widgets.WebsiteTimerConfigDialog.get_data", return_value=("twitch.tv", updated_rule)):
            page._on_configure_item("website", "twitch.tv")

        # Verify chrome.exe still owns twitch.tv and got updated limit
        assert wlm.get_browser_for_domain("twitch.tv") == "chrome.exe"
        assert wlm.get_limit("chrome.exe", "twitch.tv") == 2400
        # Verify it was NOT converted to a global wildcard
        assert wlm.get_all_limits("*").get("twitch.tv") is None

        page.deleteLater()


# ==============================================================================
# 3. Midnight Rollover and Warning State Reset
# ==============================================================================

class TestMidnightRolloverAndWarnings:
    def test_midnight_rollover_clears_warnings_and_prunes_overrides(self, test_repo, pm):
        today = date.today()
        yesterday = today - timedelta(days=1)
        pm._current_date = yesterday

        # Populate warnings and overrides from yesterday
        pm._warnings_sent["discord.exe"] = {15, 10, 5, 1, 0}
        pm._warnings_sent["youtube.com"] = {5, 1, 0}
        pm._overrides["discord.exe"] = datetime.now() - timedelta(hours=2)  # expired override
        pm._overrides["active.exe"] = datetime.now() + timedelta(hours=2)   # still active override

        # Tick with today's date should trigger midnight rollover
        pm.tick("discord.exe", 1.0)

        assert pm._current_date == today
        assert len(pm._warnings_sent) == 0
        assert len(pm._website_warnings_sent) == 0
        assert "discord.exe" not in pm._overrides
        assert "active.exe" in pm._overrides

    def test_website_override_resets_warning_state(self, test_repo, pm):
        pm._warnings_sent["youtube.com"] = {5, 1, 0}

        # Grant 15 minute extension
        pm.add_website_override("youtube.com", 15)

        # Warning state must be cleared for youtube.com
        assert "youtube.com" not in pm._warnings_sent
        assert pm.has_active_website_override("youtube.com") is True


# ==============================================================================
# 4. Timer Engines Synchronous Date Rollover
# ==============================================================================

class TestTimerEnginesDateRollover:
    def test_timer_engine_advances_date_and_clears_cache_on_read(self, test_repo):
        engine = TimerEngine(test_repo)
        engine.add_time("app.exe", 500.0)
        assert engine.get_time("app.exe") == 500.0

        # Simulate rollover to tomorrow
        tomorrow = date.today() + timedelta(days=1)
        engine._current_date = date.today() - timedelta(days=1)

        # get_time on new day must return 0.0 and advance _current_date
        assert engine.get_time("app.exe") == 0.0
        assert engine._current_date == date.today()
        assert len(engine.get_all_times()) == 0

    def test_website_timer_engine_advances_date_and_clears_cache_on_read(self, test_repo):
        engine = WebsiteTimerEngine(test_repo)
        engine.add_time("reddit.com", 300.0)
        assert engine.get_time("reddit.com") == 300.0

        # Simulate rollover to tomorrow
        engine._current_date = date.today() - timedelta(days=1)

        # get_time on new day must advance _current_date
        val = engine.get_time("reddit.com")
        assert engine._current_date == date.today()
        assert val == 0.0
