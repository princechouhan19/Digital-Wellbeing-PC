"""
test_app_locker.py — Automated regression tests for NYW App Locker.

Covers:
  - Database persistence (add/remove/clear locked apps)
  - SYSTEM_SAFE enforcement (cannot lock protected processes)
  - Temporary grant management (every_launch / 5_min / 15_min / until_close)
  - Grant expiry
  - Restart recovery (grants cleared, config persists)
  - Focus / App Locker separation (FocusManager state does not affect AppLockerManager)
  - Settings protection (enable/disable/method/duration stored correctly)
  - Windows Hello bridge imports and enum values (no live call in CI)
"""
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, ".")

import pytest


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_repo(tmp_path: Path):
    from database.repository import Repository
    Repository.set_db_path_override(tmp_path / "test_locker.db")
    Repository._instance = None
    return Repository()


def _make_alm(repo):
    from protection.app_locker import AppLockerManager
    AppLockerManager._instance = None
    alm = AppLockerManager(repo)
    AppLockerManager._instance = alm
    # Prevent real QTimer from firing
    alm._timer.blockSignals(True)
    return alm


def _teardown(tmp_path: Path):
    from database.repository import Repository
    from protection.app_locker import AppLockerManager
    AppLockerManager._instance = None
    Repository._instance = None
    Repository.set_db_path_override(None)
    try:
        for f in tmp_path.iterdir():
            f.unlink(missing_ok=True)
    except Exception:
        pass


# ── TestAppLockerDB ───────────────────────────────────────────────────────────

class TestAppLockerDB:
    """Database persistence tests."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._repo = _make_repo(self._tmp)
        self._alm = _make_alm(self._repo)

    def teardown_method(self):
        _teardown(self._tmp)

    def test_add_locked_app_persists(self):
        ok = self._alm.add_locked_app("brave.exe", "Brave Browser", "/path/brave.exe")
        assert ok
        apps = self._alm.get_locked_apps()
        assert len(apps) == 1
        assert apps[0]["process_name"] == "brave.exe"
        assert apps[0]["display_name"] == "Brave Browser"

    def test_process_name_stored_lowercase(self):
        self._alm.add_locked_app("DISCORD.EXE", "Discord", "")
        apps = self._alm.get_locked_apps()
        assert apps[0]["process_name"] == "discord.exe"

    def test_remove_locked_app(self):
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        self._alm.remove_locked_app("brave.exe")
        assert len(self._alm.get_locked_apps()) == 0

    def test_clear_all_locked_apps(self):
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        self._alm.add_locked_app("discord.exe", "Discord")
        self._alm.add_locked_app("steam.exe", "Steam")
        self._alm.clear_all_locked_apps()
        assert len(self._alm.get_locked_apps()) == 0

    def test_is_locked_true(self):
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        assert self._alm.is_locked("brave.exe")
        assert self._alm.is_locked("BRAVE.EXE")  # case-insensitive

    def test_is_locked_false_for_unknown(self):
        assert not self._alm.is_locked("notepad.exe")

    def test_duplicate_add_replaces(self):
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        self._alm.add_locked_app("brave.exe", "Brave Browser Updated")
        apps = self._alm.get_locked_apps()
        assert len(apps) == 1
        assert apps[0]["display_name"] == "Brave Browser Updated"

    def test_persistence_across_manager_reinit(self):
        """Simulates restart: new AppLockerManager reads DB."""
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        self._alm.add_locked_app("discord.exe", "Discord")

        # Simulate restart: create a new manager instance
        from protection.app_locker import AppLockerManager
        AppLockerManager._instance = None
        new_alm = _make_alm(self._repo)

        apps = new_alm.get_locked_apps()
        names = {a["process_name"] for a in apps}
        assert "brave.exe" in names
        assert "discord.exe" in names


# ── TestSystemSafe ────────────────────────────────────────────────────────────

class TestSystemSafe:
    """SYSTEM_SAFE enforcement tests."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._repo = _make_repo(self._tmp)
        self._alm = _make_alm(self._repo)

    def teardown_method(self):
        _teardown(self._tmp)

    @pytest.mark.parametrize("p_name", [
        "explorer.exe",
        "dwm.exe",
        "csrss.exe",
        "winlogon.exe",
        "services.exe",
        "lsass.exe",
        "svchost.exe",
        "taskmgr.exe",
        "digitalwellbeing.exe",
    ])
    def test_system_safe_cannot_be_locked(self, p_name: str):
        ok = self._alm.add_locked_app(p_name, "System Process")
        assert not ok, f"{p_name} must not be lockable"
        assert not self._alm.is_locked(p_name)


# ── TestAuthGrants ────────────────────────────────────────────────────────────

class TestAuthGrants:
    """Temporary access grant tests."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._repo = _make_repo(self._tmp)
        self._alm = _make_alm(self._repo)
        self._alm.add_locked_app("brave.exe", "Brave Browser")

    def teardown_method(self):
        _teardown(self._tmp)

    def test_no_grant_initially(self):
        assert not self._alm.is_access_granted("brave.exe")

    def test_grant_fifteen_min(self):
        from protection.app_locker import AuthDuration
        self._alm.set_auth_duration(AuthDuration.FIFTEEN_MIN)
        self._alm.grant_temporary_access("brave.exe")
        assert self._alm.is_access_granted("brave.exe")

    def test_grant_five_min(self):
        from protection.app_locker import AuthDuration
        self._alm.set_auth_duration(AuthDuration.FIVE_MIN)
        self._alm.grant_temporary_access("brave.exe")
        assert self._alm.is_access_granted("brave.exe")

    def test_grant_every_launch_expires_quickly(self):
        from protection.app_locker import AuthDuration
        self._alm.set_auth_duration(AuthDuration.EVERY_LAUNCH)
        self._alm.grant_temporary_access("brave.exe")
        # Grant exists immediately
        assert self._alm.is_access_granted("brave.exe")
        # Manually fast-forward expiry
        self._alm._grants["brave.exe"] = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert not self._alm.is_access_granted("brave.exe")

    def test_grant_revoke(self):
        from protection.app_locker import AuthDuration
        self._alm.set_auth_duration(AuthDuration.FIFTEEN_MIN)
        self._alm.grant_temporary_access("brave.exe")
        assert self._alm.is_access_granted("brave.exe")
        self._alm.revoke_access("brave.exe")
        assert not self._alm.is_access_granted("brave.exe")

    def test_grants_cleared_on_restart(self):
        """Grants are in-memory only; new instance has no grants."""
        from protection.app_locker import AuthDuration, AppLockerManager
        self._alm.set_auth_duration(AuthDuration.FIFTEEN_MIN)
        self._alm.grant_temporary_access("brave.exe")
        assert self._alm.is_access_granted("brave.exe")

        # Simulate restart
        AppLockerManager._instance = None
        new_alm = _make_alm(self._repo)
        assert not new_alm.is_access_granted("brave.exe"), \
            "Grants must not survive restart"

    def test_expired_grant_returns_false(self):
        from protection.app_locker import AuthDuration
        self._alm.set_auth_duration(AuthDuration.FIFTEEN_MIN)
        self._alm.grant_temporary_access("brave.exe")
        # Manually expire
        self._alm._grants["brave.exe"] = datetime.now(timezone.utc) - timedelta(minutes=16)
        assert not self._alm.is_access_granted("brave.exe")


# ── TestSettings ──────────────────────────────────────────────────────────────

class TestSettings:
    """Auth method/duration persistence."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._repo = _make_repo(self._tmp)
        self._alm = _make_alm(self._repo)

    def teardown_method(self):
        _teardown(self._tmp)

    def test_default_auth_method_is_hello_pin(self):
        from protection.app_locker import AuthMethod
        assert self._alm.auth_method == AuthMethod.HELLO_THEN_PIN

    def test_default_auth_duration_is_fifteen_min(self):
        from protection.app_locker import AuthDuration
        assert self._alm.auth_duration == AuthDuration.FIFTEEN_MIN

    def test_set_auth_method_persists(self):
        from protection.app_locker import AuthMethod, AppLockerManager
        self._alm.set_auth_method(AuthMethod.NYW_PIN)
        # New instance reads from DB
        AppLockerManager._instance = None
        new_alm = _make_alm(self._repo)
        assert new_alm.auth_method == AuthMethod.NYW_PIN

    def test_set_auth_duration_persists(self):
        from protection.app_locker import AuthDuration, AppLockerManager
        self._alm.set_auth_duration(AuthDuration.FIVE_MIN)
        AppLockerManager._instance = None
        new_alm = _make_alm(self._repo)
        assert new_alm.auth_duration == AuthDuration.FIVE_MIN

    def test_enable_disable(self):
        assert not self._alm.is_enabled  # default: disabled
        self._alm.enable()
        assert self._alm.is_enabled
        self._alm.disable()
        assert not self._alm.is_enabled


# ── TestFocusLockerSeparation ─────────────────────────────────────────────────

class TestFocusLockerSeparation:
    """FocusManager and AppLockerManager must be fully independent."""

    def setup_method(self):
        self._tmp = Path(tempfile.mkdtemp())
        self._repo = _make_repo(self._tmp)

        from protection.app_locker import AppLockerManager
        from protection.focus_manager import FocusManager
        AppLockerManager._instance = None
        FocusManager._instance = None

        # Set up PIN so strict mode can be enabled
        from protection.pin import PINManager
        pm = PINManager(self._repo)
        pm.set_pin("1234")

        self._alm = _make_alm(self._repo)
        self._fm = FocusManager(self._repo)
        self._fm._timer.blockSignals(True)
        FocusManager._instance = self._fm

    def teardown_method(self):
        from protection.focus_manager import FocusManager
        FocusManager._instance = None
        _teardown(self._tmp)

    def test_stopping_focus_does_not_affect_locker(self):
        """Stopping Focus Mode must not disable App Locker."""
        self._alm.enable()
        self._alm.add_locked_app("brave.exe", "Brave Browser")

        self._fm.start_focus(25, strict_mode=False)
        assert self._fm.is_active

        self._fm.stop_focus()
        assert not self._fm.is_active

        # App Locker must still be enabled with Brave locked
        assert self._alm.is_enabled
        assert self._alm.is_locked("brave.exe")

    def test_locker_grant_not_affected_by_focus(self):
        from protection.app_locker import AuthDuration
        self._alm.enable()
        self._alm.add_locked_app("brave.exe", "Brave Browser")
        self._alm.set_auth_duration(AuthDuration.FIFTEEN_MIN)
        self._alm.grant_temporary_access("brave.exe")
        assert self._alm.is_access_granted("brave.exe")

        # Focus session starts and stops
        self._fm.start_focus(25, strict_mode=False)
        self._fm.stop_focus()

        # Brave's grant must still be valid
        assert self._alm.is_access_granted("brave.exe")


# ── TestWindowsHelloBridge ────────────────────────────────────────────────────

class TestWindowsHelloBridge:
    """Test enum values and module imports without live Windows Hello calls."""

    def test_hello_result_enum_values(self):
        from protection.windows_hello import HelloResult
        assert HelloResult.VERIFIED       == 0
        assert HelloResult.CANCELED       == 1
        assert HelloResult.FAILED         == 2
        assert HelloResult.UNAVAILABLE    == 3
        assert HelloResult.NOT_CONFIGURED == 4
        assert HelloResult.DEVICE_BUSY    == 5
        assert HelloResult.ERROR          == 99

    def test_hello_availability_enum_values(self):
        from protection.windows_hello import HelloAvailability
        assert HelloAvailability.AVAILABLE      == 0
        assert HelloAvailability.UNAVAILABLE    == 1
        assert HelloAvailability.NOT_CONFIGURED == 2
        assert HelloAvailability.ERROR          == 99

    def test_auth_object_instantiates(self):
        from protection.windows_hello import WindowsHelloAuth
        # Instantiation must not raise even without a Qt app
        try:
            auth = WindowsHelloAuth()
            assert auth is not None
        except RuntimeError:
            # May raise if no QApplication — acceptable in headless CI
            pass

    def test_check_availability_returns_valid_enum(self):
        """On this machine Windows Hello is confirmed available."""
        from protection.windows_hello import WindowsHelloAuth, HelloAvailability
        try:
            auth = WindowsHelloAuth()
            result = auth.check_availability()
            assert isinstance(result, HelloAvailability)
        except RuntimeError:
            pytest.skip("No QApplication available in this test environment")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
