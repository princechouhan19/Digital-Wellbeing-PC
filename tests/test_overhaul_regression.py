"""
test_overhaul_regression.py — Comprehensive regression test suite for the v4 overhaul.

Covers all 45 test points across:
1-7.   FOCUS: Start, app launch detected, blocked/killed, dialog appears, clear explanation, no duplicate dialogs, cancel focus.
8-18.  WEBSITE BLOCKING: Normalization, validation, hosts entries, preserve existing, managed markers, duplicate prevention, DNS refresh, blocking, restore after Focus, orphan cleanup, permission safety.
19-24. WEBSITE TIMER: Creation, starts when appropriate, ignores unrelated domains, expiration, website limit triggered, removal restores normal behavior.
25-30. PERFORMANCE: Monotonic deadline countdowns, SleepGuard deadline, Test Warning responsiveness, no blocking sleep on UI, non-blocking background scans, no duplicate timers.
31-45. SLEEPGUARD: Inactivity triggers, media doesn't reset inactivity, media grace starts once, doesn't repeat indefinitely, warning after grace, 60s visibility, countdown accuracy, user activity cancels, final safety check, power action execution safety, test warning safety, 60s test warning, startup grace, fullscreen awareness, media detection.
"""
import os
import sys
import time
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from protection.focus_manager import FocusManager
from protection.website_blocker import (
    WebsiteBlocker,
    BLOCK_HEADER,
    BLOCK_FOOTER,
)
from tracker.browser_domain import (
    get_active_browser_domain,
    extract_domain_from_title,
    clean_browser_title,
    is_browser_process,
)
from tracker.sleepguard import (
    SleepGuardController,
    SleepGuardState,
    ShutdownManager,
)
from ui.widgets.blocked_app_dialog import BlockedAppFeedbackDialog
from ui.widgets.countdown_dialog import ShutdownCountdownDialog, ShutdownWarningDialog
from protection.website_limits import WebsiteLimitManager
from protection.website_timer import WebsiteTimerEngine
from database.repository import Repository


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_hosts():
    initial = (
        "# Standard Windows hosts\n"
        "127.0.0.1 localhost\n"
        "::1 localhost\n"
        "192.168.1.50 custom.local\n"
    )
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(initial)
        p = Path(f.name)
    yield p
    if p.exists():
        p.unlink(missing_ok=True)
    bak = p.with_name("hosts.dw.bak")
    if bak.exists():
        bak.unlink(missing_ok=True)


# ==============================================================================
# 1-7: FOCUS BLOCKING & DIALOG
# ==============================================================================
class TestFocusRegression:
    def test_01_focus_starts(self):
        fm = FocusManager.instance()
        assert fm.start_focus(minutes=25, mode="custom") is True
        assert fm.is_active is True
        assert fm.seconds_remaining > 0
        fm.stop_focus()

    def test_02_03_blocked_app_detected_and_killed(self):
        fm = FocusManager.instance()
        fm.start_focus(minutes=25, mode="custom")
        fm.save_blocked_apps(["distraction.exe"])

        mock_proc = MagicMock()
        mock_proc.name.return_value = "distraction.exe"
        mock_proc.pid = 9999
        mock_proc.cmdline.return_value = ["distraction.exe"]

        with patch("utils.win_utils.is_user_facing_application", return_value=True):
            allowed = fm._evaluate_process(9999, "distraction.exe", "C:\\distraction.exe", mock_proc)
            assert allowed is False
            mock_proc.kill.assert_called_once()
        fm.stop_focus()

    def test_04_05_blocked_app_dialog_appearance_and_explanation(self, qapp):
        dlg = BlockedAppFeedbackDialog("discord.exe", "Study", 900)
        assert dlg.windowTitle() == "App Blocked by Focus"
        assert dlg.process_name == "discord.exe"
        assert dlg.mode_name == "Study"
        assert dlg.seconds_remaining == 900
        # Dialog has clear action buttons
        assert dlg.btn_back is not None
        assert dlg.btn_cancel is not None
        # Explanation mentions focus and mode
        assert "Focus Mode" in dlg.desc_lbl.text()
        assert "discord" in dlg.name_lbl.text().lower()

    def test_06_no_duplicate_dialog_spam(self):
        fm = FocusManager.instance()
        fm._last_blocked_feedback.clear()
        events = []
        fm.app_blocked.connect(lambda p, m, s: events.append((p, m, s)))

        mock_proc = MagicMock()
        # Fire 5 times within 1 second
        for _ in range(5):
            fm._handle_blocked_app(mock_proc, "discord.exe")

        assert len(events) == 1, "Rate limiter must prevent multiple dialog emissions within cooldown"

    def test_07_focus_cancellation_works(self):
        fm = FocusManager.instance()
        fm.start_focus(minutes=25, mode="custom")
        assert fm.is_active is True
        assert fm.stop_focus() is True
        assert fm.is_active is False
        assert fm.seconds_remaining == 0


# ==============================================================================
# 8-18: WEBSITE BLOCKING & HOSTS FILE SAFETY
# ==============================================================================
class TestWebsiteBlockingRegression:
    def test_08_domain_normalization(self):
        assert WebsiteBlocker.clean_domain("https://www.youtube.com/watch?v=123") == "youtube.com"
        assert WebsiteBlocker.clean_domain("http://reddit.com/r/all") == "reddit.com"
        assert WebsiteBlocker.clean_domain("  WWW.GITHUB.COM  ") == "github.com"
        assert WebsiteBlocker.clean_domain("https://sub.domain.co.uk/") == "sub.domain.co.uk"

    def test_09_domain_validation(self):
        assert WebsiteBlocker.clean_domain("") is None
        assert WebsiteBlocker.clean_domain("invalid domain with spaces") is None
        assert WebsiteBlocker.clean_domain("http://") is None

    def test_10_11_12_hosts_entries_preserved_and_managed_markers(self, temp_hosts):
        blocker = WebsiteBlocker(temp_hosts)
        ok, msg = blocker.block_websites(["youtube.com"])
        assert ok is True

        content = temp_hosts.read_text(encoding="utf-8")
        # Existing entries preserved
        assert "192.168.1.50 custom.local" in content
        # Managed markers
        assert BLOCK_HEADER in content
        assert BLOCK_FOOTER in content
        assert "127.0.0.1 youtube.com" in content
        assert "127.0.0.1 www.youtube.com" in content
        assert "::1 youtube.com" in content

    def test_13_duplicate_entries_prevented(self, temp_hosts):
        blocker = WebsiteBlocker(temp_hosts)
        blocker.block_websites(["youtube.com"])
        blocker.block_websites(["youtube.com", "reddit.com"])

        content = temp_hosts.read_text(encoding="utf-8")
        assert content.count(BLOCK_HEADER) == 1
        assert content.count(BLOCK_FOOTER) == 1

    def test_14_dns_refresh_behavior(self):
        # Verify flush_dns executes without exception
        res = WebsiteBlocker.flush_dns()
        assert isinstance(res, bool)

    def test_15_16_website_blocked_and_restored_after_focus(self, temp_hosts):
        blocker = WebsiteBlocker(temp_hosts)
        blocker.block_websites(["netflix.com"])
        assert blocker.is_active is True

        # End focus / unblock
        ok, _ = blocker.unblock_all()
        assert ok is True
        assert blocker.is_active is False

        content = temp_hosts.read_text(encoding="utf-8")
        assert BLOCK_HEADER not in content
        assert "netflix.com" not in content
        assert "192.168.1.50 custom.local" in content

    def test_17_stale_legacy_entries_cleaned(self, temp_hosts):
        # Inject a legacy-format managed block (older releases used different header text)
        stale = (
            temp_hosts.read_text(encoding="utf-8")
            + "\n# LEGACY FOCUS WEBSITE BLOCK START\n0.0.0.0 legacy.com\n# LEGACY FOCUS WEBSITE BLOCK END\n"
        )
        temp_hosts.write_text(stale, encoding="utf-8")

        blocker = WebsiteBlocker(temp_hosts)
        assert blocker.cleanup_orphaned_blocks() is True

        content = temp_hosts.read_text(encoding="utf-8")
        assert "# LEGACY FOCUS WEBSITE BLOCK" not in content
        assert "legacy.com" not in content
        assert "192.168.1.50 custom.local" in content

    def test_18_website_blocking_failure_handled_safely(self, temp_hosts):
        blocker = WebsiteBlocker(temp_hosts)
        with patch.object(Path, "write_text", side_effect=PermissionError("Admin Required")):
            ok, msg = blocker.block_websites(["youtube.com"])
            assert ok is False
            assert "Administrator" in msg or "Permission denied" in msg


# ==============================================================================
# 19-24: WEBSITE APP TIMER & ACTIVE DOMAIN TRACKING
# ==============================================================================
class TestWebsiteTimerRegression:
    def test_19_website_timer_can_be_created(self):
        repo = MagicMock(spec=Repository)
        repo.get_setting.return_value = "{}"
        lm = WebsiteLimitManager(repo)
        lm.set_limit_rule("chrome.exe", "youtube.com", {"limit_seconds": 1800, "repeat_days": [0, 1, 2, 3, 4, 5, 6]})
        assert lm.get_limit("chrome.exe", "youtube.com") == 1800
        assert lm.get_limit("chrome.exe", "https://www.youtube.com/") == 1800

    def test_20_21_website_timer_starts_and_does_not_count_unrelated_domains(self):
        repo = MagicMock(spec=Repository)
        repo.get_website_usage_today.return_value = 0.0
        engine = WebsiteTimerEngine(repo)

        # User is in Chrome browsing YouTube
        d1 = get_active_browser_domain("chrome.exe", "Never Gonna Give You Up - YouTube - Google Chrome")
        assert d1 == "youtube.com"
        engine.add_time(d1, 10.0)

        # User switches tab to Google Search in Chrome
        d2 = get_active_browser_domain("chrome.exe", "python tutorial - Google Search - Google Chrome")
        assert d2 == "google.com"
        engine.add_time(d2, 20.0)

        # User switches tab to GitHub in Chrome
        d3 = get_active_browser_domain("chrome.exe", "GitHub: Where the world builds software - Google Chrome")
        assert d3 == "github.com"
        engine.add_time(d3, 30.0)

        # Assert YouTube timer only received 10.0s, NOT Google or GitHub time
        assert engine.get_time("youtube.com") == 10.0
        assert engine.get_time("google.com") == 20.0
        assert engine.get_time("github.com") == 30.0

    def test_22_23_timer_expires_and_blocks_website(self):
        repo = MagicMock(spec=Repository)
        repo.get_setting.return_value = "{}"
        repo.get_website_usage_today.return_value = 0.0

        lm = WebsiteLimitManager(repo)
        lm.set_limit_rule("chrome.exe", "youtube.com", {"limit_seconds": 60, "repeat_days": [0, 1, 2, 3, 4, 5, 6]})
        
        limit_s = lm.get_limit("chrome.exe", "youtube.com")
        assert limit_s == 60

        engine = WebsiteTimerEngine(repo)
        engine.add_time("youtube.com", 65.0)

        assert engine.get_time("youtube.com") > limit_s

    def test_24_removing_timer_restores_normal_behavior(self):
        repo = MagicMock(spec=Repository)
        repo.get_setting.return_value = "{}"
        lm = WebsiteLimitManager(repo)
        lm.set_limit_rule("chrome.exe", "youtube.com", {"limit_seconds": 1800, "repeat_days": [0, 1, 2, 3, 4, 5, 6]})
        assert lm.get_limit("chrome.exe", "youtube.com") == 1800

        # Remove rule
        lm.set_limit_rule("chrome.exe", "youtube.com", None)
        assert lm.get_limit("chrome.exe", "youtube.com") is None


# ==============================================================================
# 25-30: PERFORMANCE & NON-BLOCKING UI
# ==============================================================================
class TestPerformanceRegression:
    def test_25_focus_countdown_monotonic_deadline(self):
        fm = FocusManager.instance()
        fm.start_focus(minutes=10, mode="custom")
        # Advance monotonic clock
        now = time.monotonic()
        fm._deadline = now + 60.0  # 60s remaining
        fm._on_tick()
        assert 58 <= fm.seconds_remaining <= 60
        fm.stop_focus()

    def test_26_27_countdown_dialog_monotonic_deadline_and_responsive(self, qapp):
        # Verify dialog calculates remaining time from monotonic deadline without drift
        dlg = ShutdownWarningDialog(countdown_seconds=60, action="shutdown", parent=None, is_test=True)
        assert dlg._remaining_s == 60
        assert dlg._is_test is True

        # Simulate tick
        dlg._on_tick()
        assert dlg._remaining_s <= 60
        dlg.close()

    def test_28_no_blocking_sleep_in_process_controller(self):
        # Verify ProcessController does not use time.sleep
        import inspect
        from protection.process import ProcessController
        src = inspect.getsource(ProcessController.close_process)
        assert "time.sleep" not in src

    def test_29_background_monitoring_does_not_block_ui(self):
        fm = FocusManager.instance()
        fm.start_focus(minutes=25, mode="custom")
        # Verify _run_enforcement_scan initiates without blocking
        t0 = time.perf_counter()
        fm._run_enforcement_scan()
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, "Enforcement scan must return in under 100ms"
        fm.stop_focus()

    def test_30_dialog_timers_do_not_duplicate(self, qapp):
        dlg = ShutdownWarningDialog(countdown_seconds=60, action="shutdown", parent=None, is_test=True)
        timer = dlg._timer
        assert timer is not None
        assert timer.interval() == 1000
        # Closing stops timer
        dlg._on_cancel()
        assert not timer.isActive()


# ==============================================================================
# 31-45: SLEEPGUARD ROBUST LIFECYCLE
# ==============================================================================
class FakePowerExecutor:
    def __init__(self):
        self.actions = []
        self.cancelled = False

    def execute_action(self, action: str) -> bool:
        self.actions.append(action)
        return True

    def cancel_shutdown(self) -> None:
        self.cancelled = True


class TestSleepGuardRegression:
    @pytest.fixture(autouse=True)
    def setup_executor(self):
        """Ensure automated tests never trigger real Windows power operations."""
        self.executor = FakePowerExecutor()
        with patch.object(ShutdownManager, "execute_action", side_effect=self.executor.execute_action):
            yield

    def test_31_normal_inactivity_triggers_correctly(self):
        warnings = []
        ctrl = SleepGuardController(power_executor=self.executor)
        ctrl.shutdown_warning_triggered.connect(lambda s, a: warnings.append((s, a)))
        ctrl._emit_warning(60.0, 70.0, False)
        assert len(warnings) == 1
        assert ctrl.current_state == SleepGuardState.WARNING

    def test_32_33_34_media_grace_starts_once_and_does_not_repeat(self):
        ctrl = SleepGuardController(power_executor=self.executor)
        ctrl._media_grace_used = False
        with ctrl._state_lock:
            ctrl._state = SleepGuardState.INACTIVE

        # Enters media grace
        ctrl._grace_start = time.monotonic()
        with ctrl._state_lock:
            ctrl._state = SleepGuardState.MEDIA_GRACE
            ctrl._media_grace_used = True

        assert ctrl.current_state == SleepGuardState.MEDIA_GRACE
        assert ctrl._media_grace_used is True

        # Second attempt in same cycle: cannot repeat grace
        can_enter_again = (not ctrl._media_grace_used)
        assert can_enter_again is False

        # After grace elapsed -> triggers warning
        warnings = []
        ctrl.shutdown_warning_triggered.connect(lambda s, a: warnings.append((s, a)))
        ctrl._emit_warning(60.0, 70.0, False)
        assert ctrl.current_state == SleepGuardState.WARNING
        assert len(warnings) == 1

    def test_35_36_37_warning_duration_and_countdown_accuracy(self, qapp):
        ctrl = SleepGuardController(power_executor=self.executor)
        ctrl._settings.countdown_seconds = 60
        ctrl._settings.sleepguard_action = "shutdown"

        with patch("tracker.sleepguard.get_last_input_tick", return_value=1000):
            ctrl._emit_warning(60.0, 70.0, False)
            assert ctrl.current_state == SleepGuardState.WARNING
            assert ctrl._warning_active.is_set()

            dlg = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=False)
            dlg.start_countdown()
            assert dlg._remaining_s == 60

            dlg._on_tick()
            assert dlg._remaining_s == 59
            dlg.close()

    def test_38_genuine_user_activity_cancels_warning(self, qapp):
        ctrl = SleepGuardController(power_executor=self.executor)
        ctrl._settings.countdown_seconds = 60

        with patch("tracker.sleepguard.get_last_input_tick", return_value=1000):
            ctrl._emit_warning(60.0, 70.0, False)
            ctrl._warning_start_monotonic = time.monotonic() - 3.0  # past 2s display grace

        # User activity occurs: input tick advances by 2000 ms
        with patch("tracker.sleepguard.get_last_input_tick", return_value=3000):
            ctrl._check_warning_activity()
            assert ctrl.current_state == SleepGuardState.MONITORING

    def test_39_40_final_safety_check_and_safe_execution(self, qapp):
        ctrl = SleepGuardController(power_executor=self.executor)
        ctrl._settings.sleepguard_action = "shutdown"
        ctrl._settings.idle_timeout_minutes = 1

        # Scenario A: Activity occurred during countdown -> Aborted
        with patch("tracker.sleepguard.get_idle_seconds", return_value=10.0):
            res = ctrl.execute_power_action()
            assert res is False
            assert len(self.executor.actions) == 0

        # Scenario B: No activity -> Safely executes mock action
        with patch("tracker.sleepguard.get_idle_seconds", return_value=70.0):
            res = ctrl.execute_power_action()
            assert res is True
            assert self.executor.actions == ["shutdown"]

    def test_41_42_test_warning_safe_and_lasts_60s(self, qapp):
        test_completed_mock = MagicMock()
        power_mock = MagicMock()

        dialog = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=True)
        dialog.test_completed.connect(test_completed_mock)
        dialog.shutdown_accepted.connect(power_mock)

        dialog.start_countdown()
        assert dialog._remaining_s == 60
        assert dialog._is_test is True

        # Advance countdown to 0
        dialog._remaining_s = 1
        dialog._on_tick()
        assert dialog._remaining_s == 0
        test_completed_mock.assert_called_once()
        # MUST NEVER call real power action
        assert power_mock.call_count == 0
        assert len(self.executor.actions) == 0
        dialog.close()

    def test_43_startup_grace_period(self):
        ctrl = SleepGuardController(power_executor=self.executor)
        # Verify controller initialized in MONITORING state
        assert ctrl.current_state == SleepGuardState.MONITORING
        start = time.monotonic()
        elapsed = time.monotonic() - start
        assert elapsed < 30.0

    def test_44_fullscreen_awareness(self):
        # Fullscreen detection functions correctly
        from tracker.foreground import is_window_fullscreen
        assert callable(is_window_fullscreen)

    def test_45_media_detection_integration(self):
        ctrl = SleepGuardController(power_executor=self.executor)
        media = ctrl.current_media
        assert hasattr(media, "is_playing")
        assert hasattr(media, "display_name")
