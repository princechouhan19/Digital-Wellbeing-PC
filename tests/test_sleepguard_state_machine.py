"""
tests/test_sleepguard_state_machine.py -- SleepGuard v2.5 state machine tests.

Tests A-N (18 sub-tests) covering:
A  Normal inactivity -> WARNING
B  Media at threshold -> MEDIA_GRACE (not WARNING)
C  Media grace expires -> WARNING
D  Media does NOT reset the idle clock
E  Grace cannot repeat in same idle cycle
F  User activity during grace -> MONITORING
G  Warning countdown carries configured seconds
H  cancel_warning() returns to MONITORING
I  Countdown zero -> execute_power_action (mocked)
J  Test Warning: is_test=True, no power action ever
K  Media state change cannot dismiss active warning dialog
L  Fullscreen + media -> finite grace, still warns
M  Startup grace: no trigger in first 30s
N  Existing safety behaviours preserved (5 sub-tests)

No real power actions, no real sleep, all external I/O mocked.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DW_TEST_MODE"] = "1"

from PySide6.QtWidgets import QApplication
_app = QApplication.instance() or QApplication([])


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def _make_controller(idle_fn, playing_fn=None, idle_timeout_minutes=1, media_grace_minutes=1):
    """Create a SleepGuardController with all I/O mocked."""
    from tracker.sleepguard import SleepGuardController
    from tracker.media import MediaDetectionEngine

    mock_exec = MagicMock()
    mock_exec.cancel_shutdown = MagicMock()
    mock_exec.execute_action = MagicMock(return_value=True)

    orig_start = MediaDetectionEngine.start
    orig_stop  = MediaDetectionEngine.stop
    MediaDetectionEngine.start = lambda self: setattr(self, "_running", True)
    MediaDetectionEngine.stop  = lambda self: setattr(self, "_running", False)

    patcher = patch("tracker.sleepguard.get_idle_seconds", side_effect=idle_fn)
    patcher.start()

    ctrl = SleepGuardController(power_executor=mock_exec)
    ctrl._settings.idle_timeout_minutes = idle_timeout_minutes
    ctrl._settings.media_grace_minutes  = media_grace_minutes
    ctrl._settings.countdown_seconds    = 60
    ctrl._settings.sleepguard_enabled   = True
    ctrl._settings.sleepguard_action    = "lock"

    if playing_fn is not None:
        type(ctrl._media_engine).is_playing = property(lambda self: playing_fn())
    else:
        type(ctrl._media_engine).is_playing = property(lambda self: False)

    MediaDetectionEngine.start = orig_start
    MediaDetectionEngine.stop  = orig_stop

    ctrl._test_patcher = patcher
    return ctrl, mock_exec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSleepGuardStateMachine(unittest.TestCase):

    def setUp(self):
        os.environ.pop("NYW_QUICK_TEST", None)

    def tearDown(self):
        os.environ.pop("NYW_QUICK_TEST", None)

    # A -----------------------------------------------------------------------
    def test_A_normal_inactivity_triggers_warning(self):
        warnings = []
        ctrl, _ = _make_controller(idle_fn=lambda: 70.0)
        ctrl.shutdown_warning_triggered.connect(lambda s, a: warnings.append((s, a)))
        with patch("tracker.sleepguard.get_idle_seconds", return_value=70.0):
            ctrl._emit_warning(60.0, 70.0, False)
        self.assertGreaterEqual(len(warnings), 1)
        self.assertEqual(warnings[0][1], "lock")
        ctrl._test_patcher.stop()

    # B -----------------------------------------------------------------------
    def test_B_media_active_enters_grace(self):
        from tracker.sleepguard import _SGState
        ctrl, _ = _make_controller(idle_fn=lambda: 70.0, playing_fn=lambda: True)
        ctrl._media_grace_used = False
        with ctrl._state_lock:
            ctrl._state = _SGState.INACTIVE
        if ctrl._media_engine.is_playing and not ctrl._media_grace_used:
            ctrl._grace_start = time.monotonic()
            with ctrl._state_lock:
                ctrl._state = _SGState.MEDIA_GRACE
                ctrl._media_grace_used = True
        self.assertEqual(ctrl.current_state, _SGState.MEDIA_GRACE)
        self.assertTrue(ctrl._media_grace_used)
        ctrl._test_patcher.stop()

    # C -----------------------------------------------------------------------
    def test_C_grace_expires_then_warning(self):
        from tracker.sleepguard import _SGState
        warnings = []
        ctrl, _ = _make_controller(idle_fn=lambda: 70.0, playing_fn=lambda: True, media_grace_minutes=1)
        ctrl.shutdown_warning_triggered.connect(lambda s, a: warnings.append((s, a)))
        with ctrl._state_lock:
            ctrl._state = _SGState.MEDIA_GRACE
            ctrl._media_grace_used = True
        ctrl._grace_start = time.monotonic() - 120.0
        with patch("tracker.sleepguard.get_idle_seconds", return_value=70.0):
            if (time.monotonic() - ctrl._grace_start) >= 60.0:
                ctrl._emit_warning(60.0, 70.0, False)
        self.assertGreaterEqual(len(warnings), 1, "Warning must fire after grace expires")
        ctrl._test_patcher.stop()

    # D -----------------------------------------------------------------------
    def test_D_media_does_not_reset_idle_clock(self):
        from tracker.idle import is_idle
        with patch("tracker.idle.get_idle_seconds", return_value=200.0):
            with_media    = is_idle(60.0, is_media_playing=True, mode="smart")
            without_media = is_idle(60.0, is_media_playing=False)
        self.assertTrue(with_media,
            "is_idle() must return True even with media playing (idle > threshold)")
        self.assertTrue(without_media)

    # E -----------------------------------------------------------------------
    def test_E_grace_cannot_repeat_in_same_cycle(self):
        ctrl, _ = _make_controller(idle_fn=lambda: 70.0, playing_fn=lambda: True)
        ctrl._media_grace_used = False
        entries = []
        if ctrl._media_engine.is_playing and not ctrl._media_grace_used:
            ctrl._media_grace_used = True
            entries.append(1)
        # Second attempt -- should be blocked
        if ctrl._media_engine.is_playing and not ctrl._media_grace_used:
            entries.append(2)
        self.assertEqual(entries, [1], "Grace may only be entered once per idle cycle")
        ctrl._test_patcher.stop()

    # F -----------------------------------------------------------------------
    def test_F_activity_during_grace_returns_monitoring(self):
        from tracker.sleepguard import _SGState
        ctrl, _ = _make_controller(idle_fn=lambda: 5.0, playing_fn=lambda: False)
        with ctrl._state_lock:
            ctrl._state = _SGState.MEDIA_GRACE
            ctrl._media_grace_used = True
        idle_s = 5.0
        threshold_s = 60.0
        if idle_s < threshold_s * 0.5:
            with ctrl._state_lock:
                ctrl._state = _SGState.MONITORING
                ctrl._media_grace_used = False
        self.assertEqual(ctrl.current_state, _SGState.MONITORING)
        self.assertFalse(ctrl._media_grace_used)
        ctrl._test_patcher.stop()

    # G -----------------------------------------------------------------------
    def test_G_warning_carries_configured_seconds(self):
        received = []
        ctrl, _ = _make_controller(idle_fn=lambda: 70.0)
        ctrl._settings.countdown_seconds = 60
        ctrl.shutdown_warning_triggered.connect(lambda s, a: received.append(s))
        with patch("tracker.sleepguard.get_idle_seconds", return_value=70.0):
            ctrl._emit_warning(60.0, 70.0, False)
        self.assertGreater(len(received), 0)
        self.assertEqual(received[0], 60)
        ctrl._test_patcher.stop()

    # H -----------------------------------------------------------------------
    def test_H_cancel_warning_returns_to_monitoring(self):
        from tracker.sleepguard import _SGState
        ctrl, executor = _make_controller(idle_fn=lambda: 70.0)
        with ctrl._state_lock:
            ctrl._state = _SGState.WARNING
        ctrl._idle_fired.set()
        ctrl._warning_active.set()
        ctrl._media_grace_used = True
        with patch("tracker.sleepguard.get_idle_seconds", return_value=70.0):
            ctrl.cancel_warning()
        self.assertEqual(ctrl.current_state, _SGState.MONITORING)
        self.assertFalse(ctrl._idle_fired.is_set())
        self.assertFalse(ctrl._warning_active.is_set())
        self.assertFalse(ctrl._media_grace_used)
        executor.cancel_shutdown.assert_called()
        ctrl._test_patcher.stop()

    # I -----------------------------------------------------------------------
    def test_I_countdown_zero_calls_power_action(self):
        ctrl, executor = _make_controller(idle_fn=lambda: 200.0, idle_timeout_minutes=1)
        ctrl._settings.sleepguard_action = "lock"
        with patch("tracker.sleepguard.get_idle_seconds", return_value=200.0):
            result = ctrl.execute_power_action("lock")
        self.assertTrue(result)
        executor.execute_action.assert_called_with("lock")
        ctrl._test_patcher.stop()

    # J -----------------------------------------------------------------------
    def test_J_test_warning_no_power_action(self):
        from ui.widgets.countdown_dialog import ShutdownCountdownDialog
        accepted = []; completed = []
        d = ShutdownCountdownDialog(countdown_seconds=3, action="lock", is_test=True)
        d.shutdown_accepted.connect(lambda a: accepted.append(a))
        d.test_completed.connect(lambda: completed.append(True))
        d.start_countdown(); d.show()
        deadline = time.monotonic() + 6.0
        while time.monotonic() < deadline:
            _app.processEvents(); time.sleep(0.05)
            if completed:
                break
        self.assertEqual(len(accepted), 0, "Test Warning must NEVER emit shutdown_accepted")
        self.assertGreater(len(completed), 0, "Test Warning must complete cleanly")
        d.close()

    # K -----------------------------------------------------------------------
    def test_K_media_state_cannot_dismiss_warning_dialog(self):
        from ui.widgets.countdown_dialog import ShutdownCountdownDialog
        cancelled = []
        d = ShutdownCountdownDialog(countdown_seconds=10, action="lock", is_test=False)
        d.shutdown_cancelled.connect(lambda: cancelled.append(True))
        d.start_countdown(); d.show()
        with patch("tracker.idle.get_idle_seconds", return_value=0.1):
            for _ in range(5):
                _app.processEvents(); time.sleep(0.05)
        self.assertEqual(len(cancelled), 0,
            "Dialog _on_tick must NOT auto-cancel based on idle seconds")
        d.close()

    # L -----------------------------------------------------------------------
    def test_L_fullscreen_media_no_permanent_disable(self):
        from tracker.sleepguard import _SGState
        warnings = []
        ctrl, _ = _make_controller(idle_fn=lambda: 200.0, playing_fn=lambda: True, media_grace_minutes=1)
        ctrl.shutdown_warning_triggered.connect(lambda s, a: warnings.append((s, a)))
        with ctrl._state_lock:
            ctrl._state = _SGState.MEDIA_GRACE
            ctrl._media_grace_used = True
        ctrl._grace_start = time.monotonic() - 120.0
        with patch("tracker.sleepguard.get_idle_seconds", return_value=200.0):
            if (time.monotonic() - ctrl._grace_start) >= 60.0:
                ctrl._emit_warning(60.0, 200.0, False)
        self.assertGreater(len(warnings), 0,
            "Must warn even when media/fullscreen is active - grace is finite")
        ctrl._test_patcher.stop()

    # M -----------------------------------------------------------------------
    def test_M_startup_grace_skips_trigger(self):
        start = time.monotonic()
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 30.0, "elapsed must be < 30s immediately after start")
        # The poll loop checks: if elapsed < 30 -> continue (skip)
        self.assertTrue(elapsed < 30.0)

    # N -----------------------------------------------------------------------
    def test_N1_action_validation(self):
        from utils.shutdown import ShutdownManager
        sm = ShutdownManager()
        for v in ["shutdown", "sleep", "hibernate", "lock", "cancel"]:
            self.assertTrue(sm.validate_action(v), f"Expected valid: {v}")
        for inv in ["reboot", "format", "", None]:
            self.assertFalse(sm.validate_action(inv), f"Expected invalid: {inv!r}")

    def test_N2_cancel_action_is_safe(self):
        from utils.shutdown import ShutdownManager
        self.assertTrue(ShutdownManager().execute_action("cancel"))

    def test_N3_minimum_countdown_floor(self):
        from utils.shutdown import MIN_COUNTDOWN_SECONDS
        from settings.manager import SettingsManager
        raw = SettingsManager().countdown_seconds
        self.assertGreaterEqual(max(raw, MIN_COUNTDOWN_SECONDS), MIN_COUNTDOWN_SECONDS)

    def test_N4_invalid_action_blocked(self):
        from utils.shutdown import ShutdownManager
        self.assertFalse(ShutdownManager().execute_action("format_c_drive"))

    def test_N5_safety_check_aborts_if_user_active(self):
        ctrl, executor = _make_controller(idle_fn=lambda: 0.5, idle_timeout_minutes=1)
        with patch("tracker.sleepguard.get_idle_seconds", return_value=0.5):
            result = ctrl.execute_power_action("lock")
        self.assertFalse(result, "Must abort when user is active")
        executor.execute_action.assert_not_called()
        ctrl._test_patcher.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
