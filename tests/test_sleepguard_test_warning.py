"""
Tests for SleepGuard 'Test Warning' isolated preview behavior.

Verifies:
1. No UI lag / immediate instantiation on Qt main thread.
2. Full 60-second preview: remains open despite active user input (idle < 2.0s).
3. Smooth countdown decrementing.
4. Total safety: expiry and action buttons NEVER invoke power actions.
5. Cancel closes dialog cleanly without side-effects.
6. Real SleepGuard state, timers, grace period, and settings remain untouched.
7. Exactly one dialog displayed (no duplicates or native popups).
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from tracker import idle as idle_module
from tracker import sleepguard as sleepguard_module
from ui.widgets.countdown_dialog import ShutdownCountdownDialog
from ui.pages.sleepguard_page import SleepGuardPage


class FakeSettings:
    def __init__(self, action: str = "shutdown") -> None:
        self.sleepguard_action = action
        self.idle_timeout_minutes = 30
        self.countdown_seconds = 60
        self.sleepguard_enabled = True
        self.shutdown_mode = "smart"
        self.media_idle_timeout_minutes = 15
        self.media_grace_minutes = 5


class FakeMediaEngine:
    def __init__(self, poll_interval: float = 1.0, on_state_change=None) -> None:
        self.is_playing = False
        self.current = SimpleNamespace(is_playing=False, display_name="")

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


def test_dialog_test_mode_does_not_cancel_on_active_user(qapp, monkeypatch):
    """
    Test Warning preview dialog must never auto-cancel on active user or background tick.
    Real mode dialog cancels when controller calls force_cancel() on genuine activity.
    """
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 0.1)

    # Test mode: should remain open across multiple ticks
    test_dlg = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=True)
    test_dlg.start_countdown()
    for _ in range(5):
        test_dlg._on_tick()

    assert not test_dlg._cancelled, "Test dialog must not cancel on user activity"
    assert test_dlg._remaining_s == 55, "Countdown must decrement smoothly from 60 to 55"
    test_dlg._on_cancel()
    test_dlg.deleteLater()

    # Real mode: does not vanish on tick; cancels when controller triggers force_cancel
    real_dlg = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=False)
    real_dlg.start_countdown()
    real_dlg._on_tick()
    assert not real_dlg._cancelled, "Real SleepGuard dialog must not vanish on ordinary tick"
    real_dlg.force_cancel()
    assert real_dlg._cancelled, "Real SleepGuard dialog cancels when force_cancel is called"
    real_dlg.deleteLater()


def test_dialog_test_mode_completion_never_executes_power_action(qapp, monkeypatch):
    """When countdown reaches 0 in test mode, power action must NEVER execute."""
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 100.0)

    mock_power_action = MagicMock()
    test_completed_mock = MagicMock()

    dialog = ShutdownCountdownDialog(countdown_seconds=1, action="shutdown", is_test=True)
    dialog.shutdown_accepted.connect(mock_power_action)
    dialog.test_completed.connect(test_completed_mock)

    dialog.start_countdown()
    dialog._on_tick()  # reaches 0

    assert dialog._remaining_s == 0
    assert mock_power_action.call_count == 0, "Power action MUST NOT be called in test mode"
    assert test_completed_mock.call_count == 1, "test_completed signal should be emitted"
    assert dialog._completed
    dialog.deleteLater()


def test_dialog_test_mode_buttons_and_visuals(qapp):
    """Test preview dialog displays appropriate preview text and safe buttons."""
    dialog = ShutdownCountdownDialog(countdown_seconds=60, action="shutdown", is_test=True)

    assert "Test Warning Preview" in dialog.windowTitle()
    assert dialog._confirm_btn.text() == "Close Preview"
    assert dialog._cancel_btn.text() == "Cancel"
    assert dialog._remaining_s == 60

    # Clicking 'Close Preview' completes test safely
    mock_power = MagicMock()
    dialog.shutdown_accepted.connect(mock_power)
    dialog._confirm_btn.click()

    assert mock_power.call_count == 0, "Close Preview button must not invoke power action"
    assert dialog._completed
    dialog.deleteLater()


def test_sleepguard_page_test_warning_immediate_and_isolated(qapp, monkeypatch):
    """Clicking 'Test Warning' opens the preview immediately without affecting SleepGuard controller."""
    settings = FakeSettings(action="sleep")
    monkeypatch.setattr(sleepguard_module, "SettingsManager", lambda: settings)
    monkeypatch.setattr(sleepguard_module, "MediaDetectionEngine", FakeMediaEngine)

    controller = sleepguard_module.SleepGuardController()

    page = SleepGuardPage(sleepguard=controller)
    page.show()

    # Pre-test state
    assert not controller._idle_fired.is_set()
    assert controller.is_enabled
    initial_timeout = settings.idle_timeout_minutes

    # Trigger test warning
    page._on_test_warning()

    # Verify dialog was created
    dlg = page._test_dialog
    assert dlg is not None, "Test dialog should be stored on the page"
    assert dlg.isVisible(), "Test dialog should be visible"
    assert dlg._is_test, "Dialog must be flagged as is_test"
    assert dlg._remaining_s == 60, "Countdown must start at 60 seconds"
    assert dlg._action == "sleep", "Dialog must reflect configured action"

    # Verify real SleepGuard controller state was completely untouched
    assert not controller._idle_fired.is_set(), "Real SleepGuard _idle_fired must NOT be set"
    assert controller.is_enabled, "Real SleepGuard enabled state must NOT change"
    assert settings.idle_timeout_minutes == initial_timeout, "Settings must remain untouched"

    # Verify rapid re-click cleans up and does not create duplicate dialogs
    page._on_test_warning()
    top_dialogs = [
        w for w in QApplication.topLevelWidgets()
        if isinstance(w, ShutdownCountdownDialog) and w.isVisible()
    ]
    assert len(top_dialogs) == 1, "Exactly one test dialog must be visible at any time"

    # Cancel closes dialog cleanly
    page._test_dialog._cancel_btn.click()
    assert page._test_dialog is None or not page._test_dialog.isVisible()

    page.deleteLater()
    controller.deleteLater()
