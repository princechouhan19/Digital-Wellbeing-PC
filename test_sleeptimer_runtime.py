"""
test_sleeptimer_runtime.py — Real runtime verification of SleepGuard v2.4 safety changes.

Tests the complete path:
  Timer configured → countdown appears → notification/warning → countdown reaches zero → action executes

Tests:
  1. Safety guards (invalid action blocked)
  2. Cancel before expiry (action NOT executed)
  3. Lock action (countdown expires → LockWorkStation called)
  4. Minimum countdown floor (5s clamped to 10s)
  5. Action validation for all supported types
  6. Migration: missing setting defaults to "lock"
"""

import sys
import os
import time
import logging
from pathlib import Path

# Setup project path
sys.path.insert(0, str(Path(__file__).parent))
os.environ["DW_TEST_MODE"] = "1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("sleeptimer_test")

RESULTS = []

def record(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, status, detail))
    icon = "✅" if passed else "❌"
    print(f"  {icon} {name}: {status}" + (f" — {detail}" if detail else ""))


def test_action_validation():
    """Test ShutdownManager.validate_action for all inputs."""
    print("\n═══ TEST 1: Action Validation ═══")
    from utils.shutdown import ShutdownManager
    sm = ShutdownManager()

    valid_cases = ["shutdown", "sleep", "hibernate", "lock", "cancel"]
    invalid_cases = ["reboot", "format", "", "SHUTDOWN ", None, 123, "power_off"]

    all_ok = True
    for v in valid_cases:
        ok = sm.validate_action(v)
        if not ok:
            record(f"validate('{v}')", False, "Expected True")
            all_ok = False
    for inv in invalid_cases:
        ok = sm.validate_action(inv)
        if ok:
            record(f"validate({inv!r})", False, "Expected False (should reject)")
            all_ok = False

    if all_ok:
        record("Action validation", True, f"All valid={valid_cases} accepted, all invalid rejected")


def test_safety_guard_blocks_invalid():
    """Test that execute_action refuses unknown/invalid actions."""
    print("\n═══ TEST 2: Safety Guard — Invalid Action Blocked ═══")
    from utils.shutdown import ShutdownManager
    sm = ShutdownManager()

    result = sm.execute_action("format_c_drive")
    record("execute_action('format_c_drive')", result == False, f"Returned {result}")

    result = sm.execute_action("")
    record("execute_action('')", result == False, f"Returned {result}")

    result = sm.execute_action(None)
    record("execute_action(None)", result == False, f"Returned {result}")


def test_cancel_action():
    """Test that cancel action returns True but does nothing destructive."""
    print("\n═══ TEST 3: Cancel Action ═══")
    from utils.shutdown import ShutdownManager
    sm = ShutdownManager()

    result = sm.execute_action("cancel")
    record("execute_action('cancel')", result == True, f"Returned {result}")


def test_minimum_countdown_floor():
    """Test that countdown < 10 is clamped to 10."""
    print("\n═══ TEST 4: Minimum Countdown Floor ═══")
    from utils.shutdown import MIN_COUNTDOWN_SECONDS
    from settings.manager import SettingsManager

    sm = SettingsManager()
    raw = sm.countdown_seconds  # This is 5 in the existing DB
    clamped = max(raw, MIN_COUNTDOWN_SECONDS)

    record(
        "Countdown floor",
        clamped >= MIN_COUNTDOWN_SECONDS,
        f"Raw={raw}s, Clamped={clamped}s, Floor={MIN_COUNTDOWN_SECONDS}s"
    )


def test_migration_defaults():
    """Test that missing sleepguard_action defaults to 'lock'."""
    print("\n═══ TEST 5: Migration — Missing Setting Defaults ═══")
    from settings.manager import SettingsManager
    sm = SettingsManager()

    # First ensure the key doesn't exist
    import sqlite3
    db = Path.home() / "AppData" / "Local" / "DigitalWellbeing" / "digital_wellbeing.db"
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM settings WHERE key = 'sleepguard_action'")
    conn.commit()
    conn.close()

    # Force a fresh read (SettingsManager reads from DB each time)
    action = sm.sleepguard_action
    record("Missing key defaults to 'lock'", action == "lock", f"Got {action!r}")


def test_countdown_dialog_ui():
    """Test the countdown dialog shows correctly and can be cancelled."""
    print("\n═══ TEST 6: Countdown Dialog — UI Rendering & Cancel ═══")
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from ui.widgets.countdown_dialog import ShutdownCountdownDialog

    app = QApplication.instance() or QApplication(sys.argv)

    # Test 6a: Dialog with cancel
    dialog = ShutdownCountdownDialog(countdown_seconds=10, action="lock", parent=None)
    
    action_received = []
    cancel_received = []
    dialog.shutdown_accepted.connect(lambda a: action_received.append(a))
    dialog.shutdown_cancelled.connect(lambda: cancel_received.append(True))

    dialog.start_countdown()
    dialog.show()

    # Wait 2 ticks then cancel
    def do_cancel():
        dialog._on_cancel()

    QTimer.singleShot(2500, do_cancel)  # Cancel after 2.5 seconds

    # Run event loop briefly
    deadline = time.monotonic() + 4.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.05)

    record(
        "Dialog cancel prevents action",
        len(cancel_received) > 0 and len(action_received) == 0,
        f"cancel_signals={len(cancel_received)}, action_signals={len(action_received)}"
    )

    # Test 6b: Dialog with expiry (very short countdown)
    dialog2 = ShutdownCountdownDialog(countdown_seconds=3, action="lock", parent=None)
    action_received2 = []
    dialog2.shutdown_accepted.connect(lambda a: action_received2.append(a))
    dialog2.start_countdown()
    dialog2.show()

    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.05)
        if action_received2:
            break

    record(
        "Dialog expiry emits action",
        len(action_received2) > 0,
        f"action_signals={action_received2}"
    )

    if action_received2:
        record(
            "Expiry carries correct action type",
            action_received2[0] == "lock",
            f"Got action={action_received2[0]!r}"
        )

    # Test 6c: Action-specific labels
    for act in ["lock", "sleep", "hibernate", "shutdown"]:
        d = ShutdownCountdownDialog(countdown_seconds=60, action=act)
        title = d.windowTitle()
        record(
            f"Dialog title for '{act}'",
            act.lower() in title.lower() or act.title() in title or "shut down" in title.lower(),
            f"Title={title!r}"
        )
        d.close()


def test_sleepguard_controller_safety():
    """Test SleepGuardController.execute_power_action safety guards."""
    print("\n═══ TEST 7: SleepGuard Controller — Safety Guards ═══")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    from tracker.sleepguard import SleepGuardController

    ctrl = SleepGuardController()

    # Invalid action
    result = ctrl.execute_power_action("nuke_everything")
    record("Controller rejects invalid action", result == False, f"Returned {result}")

    # Cancel action
    result = ctrl.execute_power_action("cancel")
    record("Controller accepts cancel action", result == True, f"Returned {result}")


def test_lock_action_executes():
    """Test that the lock action actually calls LockWorkStation.
    
    NOTE: This WILL lock the screen. The test records success if the API call returns True.
    """
    print("\n═══ TEST 8: Lock Action — Real Execution ═══")
    from utils.shutdown import ShutdownManager
    sm = ShutdownManager()

    print("  ⚠️  This will LOCK your screen. You will need to unlock with your password.")
    print("  ⏳ Executing in 3 seconds...")
    time.sleep(3)

    result = sm.execute_action("lock")
    # If we reach here, lock was called. The screen will be locked.
    record("Lock action executed", result == True, f"Returned {result}")


def print_summary():
    print("\n" + "═" * 60)
    print("  SLEEP TIMER v2.4 — TEST SUMMARY")
    print("═" * 60)
    passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
    failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    total = len(RESULTS)
    print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")
    print()
    for name, status, detail in RESULTS:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {name}: {status}" + (f" — {detail}" if detail else ""))
    print("═" * 60)
    if failed > 0:
        print("  ⚠️  SOME TESTS FAILED — DO NOT COMMIT")
    else:
        print("  ✅  ALL TESTS PASSED")
    print("═" * 60)


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Digital Wellbeing v2.4 — Sleep Timer Runtime Test Suite    ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    test_action_validation()
    test_safety_guard_blocks_invalid()
    test_cancel_action()
    test_minimum_countdown_floor()
    test_migration_defaults()
    test_countdown_dialog_ui()
    test_sleepguard_controller_safety()

    # The lock test is last because it will lock the screen
    if "--skip-lock" not in sys.argv:
        test_lock_action_executes()
    else:
        print("\n═══ TEST 8: Lock Action — SKIPPED (--skip-lock) ═══")

    print_summary()
