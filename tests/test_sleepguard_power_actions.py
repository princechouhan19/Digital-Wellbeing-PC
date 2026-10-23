"""Non-destructive regression coverage for the SleepGuard expiry path."""

from __future__ import annotations

import logging
import os
import subprocess
from types import SimpleNamespace

import pytest

# This must be set before QApplication is created on CI hosts without a desktop.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from database.repository import Repository
from settings.manager import SettingsManager
from tracker import idle as idle_module
from tracker import sleepguard as sleepguard_module
from ui.widgets.countdown_dialog import ShutdownCountdownDialog
from utils import shutdown as shutdown_module
from utils.shutdown import ShutdownManager


class FakeSettings:
    def __init__(self, action: str = "shutdown") -> None:
        self.sleepguard_action = action
        self.idle_timeout_minutes = 1
        self.countdown_seconds = 10
        self.sleepguard_enabled = True
        self.shutdown_mode = "smart"
        self.media_idle_timeout_minutes = 15
        self.media_grace_minutes = 5


class FakeMediaEngine:
    def __init__(self, poll_interval: float, on_state_change) -> None:
        self.poll_interval = poll_interval
        self.on_state_change = on_state_change
        self.is_playing = False
        self.current = SimpleNamespace(is_playing=False, display_name="")

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class FakePowerExecutor:
    def __init__(self, result: bool = True, error: Exception | None = None) -> None:
        self.actions: list[str] = []
        self.result = result
        self.error = error
        self.cancelled = False

    def execute_action(self, action: str) -> bool:
        self.actions.append(action)
        if self.error:
            raise self.error
        return self.result

    def cancel_shutdown(self) -> None:
        self.cancelled = True


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller_factory(monkeypatch):
    def build(action: str = "shutdown", executor: FakePowerExecutor | None = None):
        settings = FakeSettings(action)
        monkeypatch.setattr(sleepguard_module, "SettingsManager", lambda: settings)
        monkeypatch.setattr(sleepguard_module, "MediaDetectionEngine", FakeMediaEngine)
        power_executor = executor or FakePowerExecutor()
        controller = sleepguard_module.SleepGuardController(power_executor=power_executor)
        return controller, settings, power_executor

    return build


def test_countdown_completes_on_the_tick_that_reaches_zero(qapp, monkeypatch):
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 60.0)
    dialog = ShutdownCountdownDialog(countdown_seconds=1, action="shutdown")
    accepted: list[str] = []
    cancelled: list[bool] = []
    dialog.shutdown_accepted.connect(accepted.append)
    dialog.shutdown_cancelled.connect(lambda: cancelled.append(True))

    dialog.start_countdown()
    dialog._on_tick()

    assert dialog._remaining_s == 0
    assert accepted == ["shutdown"]
    assert cancelled == []
    assert not dialog._timer.isActive()

    # A stray queued timer event must not execute the action twice.
    dialog._on_tick()
    assert accepted == ["shutdown"]
    dialog.deleteLater()


def test_countdown_expiry_routes_to_fake_power_executor(qapp, monkeypatch, controller_factory):
    controller, _, executor = controller_factory("shutdown")
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 120.0)
    monkeypatch.setattr(sleepguard_module, "get_idle_seconds", lambda: 120.0)
    dialog = ShutdownCountdownDialog(countdown_seconds=1, action="shutdown")
    dialog.shutdown_accepted.connect(controller.execute_power_action)

    dialog.start_countdown()
    dialog._on_tick()

    assert executor.actions == ["shutdown"]
    assert not dialog._timer.isActive()
    dialog.deleteLater()
    controller.deleteLater()


def test_activity_during_countdown_cancels_without_power_action(qapp, monkeypatch):
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 1.0)
    dialog = ShutdownCountdownDialog(countdown_seconds=10, action="shutdown")
    accepted: list[str] = []
    cancelled: list[bool] = []
    dialog.shutdown_accepted.connect(accepted.append)
    dialog.shutdown_cancelled.connect(lambda: cancelled.append(True))

    dialog.start_countdown()
    dialog._on_tick()
    # Ordinary tick does not vanish dialog
    assert not dialog._cancelled
    # When controller detects genuine user activity, it triggers force_cancel
    dialog.force_cancel()

    assert accepted == []
    assert cancelled == [True]
    assert dialog._cancelled
    assert not dialog._timer.isActive()
    dialog.deleteLater()


@pytest.mark.parametrize("action", ["lock", "sleep", "hibernate", "shutdown"])
def test_final_safety_check_passes_and_routes_each_action(
    monkeypatch,
    caplog,
    controller_factory,
    action,
):
    controller, _, executor = controller_factory(action)
    monkeypatch.setattr(sleepguard_module, "get_idle_seconds", lambda: 120.0)
    caplog.set_level(logging.INFO, logger="digital_wellbeing.sleepguard")

    assert controller.execute_power_action(action) is True
    assert executor.actions == [action]
    assert "Countdown completed" in caplog.text
    assert "Final activity/safety check result: PASSED" in caplog.text
    assert f"effective power action='{action}'" in caplog.text
    assert "Power action result" in caplog.text
    controller.deleteLater()


def test_final_safety_check_prevents_action_after_recent_activity(
    monkeypatch,
    caplog,
    controller_factory,
):
    controller, _, executor = controller_factory("shutdown")
    monkeypatch.setattr(sleepguard_module, "get_idle_seconds", lambda: 1.0)
    caplog.set_level(logging.INFO, logger="digital_wellbeing.sleepguard")

    assert controller.execute_power_action("shutdown") is False
    assert executor.actions == []
    assert "Final activity/safety check result: FAILED" in caplog.text
    controller.deleteLater()


def test_power_executor_exception_is_logged_and_reported_as_failure(
    monkeypatch,
    caplog,
    controller_factory,
):
    executor = FakePowerExecutor(error=RuntimeError("simulated executor failure"))
    controller, _, _ = controller_factory("shutdown", executor)
    monkeypatch.setattr(sleepguard_module, "get_idle_seconds", lambda: 120.0)
    caplog.set_level(logging.INFO, logger="digital_wellbeing.sleepguard")

    assert controller.execute_power_action("shutdown") is False
    assert executor.actions == ["shutdown"]
    assert "Power action execution raised an unexpected exception" in caplog.text
    assert "Power action result: action='shutdown', success=False" in caplog.text
    controller.deleteLater()


def test_shutdown_manager_maps_each_action_to_its_handler(monkeypatch):
    manager = ShutdownManager()
    handled: list[str] = []

    for action in ("lock", "sleep", "hibernate", "shutdown"):
        monkeypatch.setattr(
            manager,
            f"_execute_{action}",
            lambda action=action: handled.append(action) or True,
        )

    for action in ("lock", "sleep", "hibernate", "shutdown"):
        assert manager.execute_action(action) is True

    assert handled == ["lock", "sleep", "hibernate", "shutdown"]


def test_shutdown_command_failure_is_detected(monkeypatch, caplog):
    command: list[object] = []

    def failed_run(*args, **kwargs):
        command.extend([args, kwargs])
        return subprocess.CompletedProcess(args[0], 5, stdout="", stderr="simulated access denied")

    monkeypatch.setattr(shutdown_module.subprocess, "run", failed_run)
    caplog.set_level(logging.INFO, logger="digital_wellbeing.shutdown")

    assert ShutdownManager().execute_action("shutdown") is False
    assert command[0][0][0] == r"C:\Windows\System32\shutdown.exe"
    assert command[0][0][1:] == ["/s", "/f", "/t", "0"]
    assert command[1]["check"] is False
    assert "return_code=5" in caplog.text
    assert "simulated access denied" in caplog.text


def test_shutdown_command_exception_is_detected(monkeypatch, caplog):
    def failing_run(*args, **kwargs):
        raise OSError("simulated launch failure")

    monkeypatch.setattr(shutdown_module.subprocess, "run", failing_run)
    caplog.set_level(logging.INFO, logger="digital_wellbeing.shutdown")

    assert ShutdownManager().execute_action("shutdown") is False
    assert "Failed to invoke shutdown command" in caplog.text


def test_sleepguard_action_setting_persists(tmp_path):
    test_db = tmp_path / "sleepguard-settings.db"
    Repository.set_db_path_override(test_db)
    try:
        for action in ("lock", "sleep", "hibernate", "shutdown"):
            SettingsManager().sleepguard_action = action
            assert SettingsManager().sleepguard_action == action
    finally:
        Repository().close()
        Repository.set_db_path_override(None)


def test_startup_grace_period_skips_idle_evaluation(monkeypatch, controller_factory):
    controller, _, _ = controller_factory("shutdown")
    controller._running = True
    controller._paused = False
    idle_checks: list[bool] = []
    sleep_calls = 0
    clock_values = iter((0.0, 10.0))

    def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            controller._running = False

    monkeypatch.setattr(sleepguard_module.time, "time", lambda: next(clock_values))
    monkeypatch.setattr(sleepguard_module.time, "sleep", fake_sleep)
    monkeypatch.setattr(sleepguard_module, "get_idle_seconds", lambda: idle_checks.append(True) or 120.0)

    controller._poll_loop()

    assert sleep_calls == 2
    assert idle_checks == []
    controller.deleteLater()


def test_media_modes_preserve_existing_idle_behavior(monkeypatch):
    monkeypatch.setattr(idle_module, "get_idle_seconds", lambda: 100.0)

    assert not idle_module.is_idle(10.0, is_media_playing=True, mode="media")
    assert idle_module.is_idle(10.0, is_media_playing=True, mode="strict")
    assert not idle_module.is_idle(10.0, is_media_playing=True, mode="smart", media_timeout_s=200.0)
    assert idle_module.is_idle(10.0, is_media_playing=True, mode="smart", media_timeout_s=60.0)
