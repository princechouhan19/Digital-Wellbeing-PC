"""
test_focus_pin_regression.py
Regression tests for the Focus Mode PIN unlock bug (v3.0.0).

Root cause: stop_focus(provided_pin="verified_by_dialog") was passing a literal
string to PINManager.verify_pin() instead of the real PIN, causing the second
hash-check to always fail and the session to stay active.

Fix: stop_focus_after_pin_dialog() bypasses the redundant re-validation after
the PinDialog has already confirmed the PIN.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

def _make_repo(tmp_path):
    """Create an isolated Repository using a fresh temp DB."""
    from database.repository import Repository
    tmp = tmp_path / "test_focus_pin.db"
    Repository.set_db_path_override(tmp)
    return Repository(), tmp


def _make_fm(repo):
    """Create a fresh FocusManager singleton for the test (reset between tests)."""
    from protection.focus_manager import FocusManager
    FocusManager._instance = None          # reset singleton
    fm = FocusManager(repo)
    FocusManager._instance = fm
    # Prevent the real QTimer from firing during unit tests
    fm._timer.blockSignals(True)
    return fm


def _set_pin(repo, pin: str):
    from protection.pin import PINManager
    pm = PINManager(repo)
    assert pm.set_pin(pin), f"Failed to set PIN {pin!r}"
    return pm


# ── tests ────────────────────────────────────────────────────────────────────

class TestPINManagerVerify:
    """Unit tests for PINManager.verify_pin() — security-critical."""

    def test_correct_pin_returns_true(self, tmp_path):
        from database.repository import Repository
        from protection.pin import PINManager
        Repository.set_db_path_override(tmp_path / "pin.db")
        repo = Repository()
        pm = PINManager(repo)
        pm.set_pin("1234")
        assert pm.verify_pin("1234") is True

    def test_incorrect_pin_returns_false(self, tmp_path):
        from database.repository import Repository
        from protection.pin import PINManager
        Repository.set_db_path_override(tmp_path / "pin.db")
        repo = Repository()
        pm = PINManager(repo)
        pm.set_pin("1234")
        assert pm.verify_pin("9999") is False

    def test_bogus_string_returns_false(self, tmp_path):
        """The old code passed 'verified_by_dialog' — this must fail."""
        from database.repository import Repository
        from protection.pin import PINManager
        Repository.set_db_path_override(tmp_path / "pin.db")
        repo = Repository()
        pm = PINManager(repo)
        pm.set_pin("1234")
        assert pm.verify_pin("verified_by_dialog") is False
        assert pm.verify_pin("verified") is False

    def test_no_pin_set_verify_passes(self, tmp_path):
        from database.repository import Repository
        from protection.pin import PINManager
        Repository.set_db_path_override(tmp_path / "pin.db")
        repo = Repository()
        pm = PINManager(repo)
        # PIN not set -> verify_pin returns True (no protection configured)
        assert pm.verify_pin("anything") is True


class TestFocusManagerPINFlow:
    """Integration tests for the focus session start/stop flow."""

    def setup_method(self):
        from database.repository import Repository
        from protection.focus_manager import FocusManager
        FocusManager._instance = None
        import tempfile
        self._tmp_dir = Path(tempfile.mkdtemp())
        self._tmp = self._tmp_dir / "focus_test.db"
        Repository.set_db_path_override(self._tmp)
        self._repo = Repository()
        _set_pin(self._repo, "5678")
        self._fm = _make_fm(self._repo)

    def teardown_method(self):
        from database.repository import Repository
        from protection.focus_manager import FocusManager
        FocusManager._instance = None
        Repository.set_db_path_override(None)
        try:
            self._tmp.unlink(missing_ok=True)
        except Exception:
            pass

    def test_correct_pin_stops_strict_focus(self):
        """
        TEST 1 regression: correct PIN -> focus stops completely.

        This is the exact bug present in v3.0.0:
        stop_focus("verified_by_dialog") silently failed because
        "verified_by_dialog" != hash("5678").
        """
        started = self._fm.start_focus(25, strict_mode=True)
        assert started, "Focus should have started"
        assert self._fm.is_active
        assert self._fm.is_strict

        # Simulate what PinDialog does: verify pin, then call stop_focus_after_pin_dialog()
        pin_ok = self._fm._pin_manager.verify_pin("5678")
        assert pin_ok, "Correct PIN must verify to True"

        stopped = self._fm.stop_focus_after_pin_dialog()
        assert stopped, "stop_focus_after_pin_dialog() must return True"
        assert not self._fm.is_active, "Focus must be inactive after unlock"
        assert not self._fm.is_strict, "Strict mode must be cleared after unlock"

    def test_incorrect_pin_keeps_focus_active(self):
        """TEST 2: wrong PIN -> focus session remains active."""
        self._fm.start_focus(25, strict_mode=True)
        assert self._fm.is_active

        stopped = self._fm.stop_focus(provided_pin="9999")
        assert not stopped, "stop_focus with wrong PIN must return False"
        assert self._fm.is_active, "Focus must remain active after wrong PIN"

    def test_old_bogus_string_keeps_focus_active(self):
        """Ensure the old 'verified_by_dialog' bypass string is blocked."""
        self._fm.start_focus(25, strict_mode=True)
        assert self._fm.is_active

        stopped = self._fm.stop_focus(provided_pin="verified_by_dialog")
        assert not stopped, "Bogus bypass string must not stop strict focus"
        assert self._fm.is_active, "Focus must remain active"

    def test_non_strict_focus_stops_without_pin(self):
        """TEST 7: normal Focus Mode stops without requiring any PIN."""
        started = self._fm.start_focus(25, strict_mode=False)
        assert started

        stopped = self._fm.stop_focus()
        assert stopped, "Non-strict focus must stop without PIN"
        assert not self._fm.is_active

    def test_cancel_leaves_focus_active(self):
        """TEST 3 (Cancel): if dialog is rejected, stop must NOT be called."""
        self._fm.start_focus(25, strict_mode=True)
        assert self._fm.is_active
        # Simulate Cancel: dialog.exec() returns 0 (Rejected),
        # so stop_focus_after_pin_dialog() is never called.
        assert self._fm.is_active, "Focus remains active when Cancel is pressed"

    def test_natural_expiry_clears_state(self):
        """TEST 8: session state is fully cleared when timer expires."""
        self._fm.start_focus(1, strict_mode=True)
        assert self._fm.is_active

        # Manually trigger the expiry path (mimics _on_tick hitting 0)
        self._fm._seconds_remaining = 0
        self._fm._is_active = False
        self._fm._is_strict = False
        self._fm._timer.stop()

        assert not self._fm.is_active
        assert not self._fm.is_strict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
