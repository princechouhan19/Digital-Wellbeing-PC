"""
sleepguard.py -- SleepGuard Controller for Digital Wellbeing Platform v2.5.

Integrates Win32 idle monitoring, WinRT GSMTC media playback detection,
and automated PC power action logic with PySide6 signals.

v2.5 changes:
- Explicit 4-state machine: MONITORING -> INACTIVE -> MEDIA_GRACE -> WARNING
- Media playback no longer pauses/resets inactivity indefinitely
- Media grace is a single finite period per idle cycle (default 5 min)
- Warning dialog is no longer auto-dismissed by mouse movement;
  the controller monitors activity and cancels via signal instead
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from typing import Optional

from PySide6.QtCore import QObject, Signal

from settings.manager import SettingsManager
from tracker.idle import get_idle_seconds, get_last_input_tick
from tracker.media import MediaDetectionEngine, MediaInfo
from utils.shutdown import ShutdownManager, MIN_COUNTDOWN_SECONDS, VALID_ACTIONS

# Use the application's configured logger hierarchy so final safety decisions
# are written to the rotating DigitalWellbeing log in frozen builds too.
logger = logging.getLogger("digital_wellbeing.sleepguard")


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class _SGState(enum.Enum):
    """Explicit states for the SleepGuard inactivity state machine."""
    MONITORING         = "monitoring"          # Normal: waiting for inactivity threshold
    INACTIVE           = "inactive"            # Threshold reached: deciding on media grace
    MEDIA_GRACE        = "media_grace"         # One-shot grace period while media plays
    WARNING            = "warning"             # Dialog shown: counting down to power action
    FINAL_SAFETY_CHECK = "final_safety_check"  # Safety check before power action


SleepGuardState = _SGState


class SleepGuardController(QObject):

    # Signal carries (countdown_seconds, action_type)
    shutdown_warning_triggered = Signal(int, str)
    media_state_changed = Signal(object)        # MediaInfo
    sleepguard_status_changed = Signal(bool)    # active status
    programmatic_shutdown_cancelled = Signal()  # emitted when cancel is performed

    def __init__(
        self,
        parent=None,
        power_executor: Optional[ShutdownManager] = None,
    ) -> None:
        super().__init__(parent)
        self._settings = SettingsManager()
        # Production keeps the existing ShutdownManager. Tests inject a mock.
        self._shutdown_mgr = power_executor or ShutdownManager()

        self._media_engine = MediaDetectionEngine(
            poll_interval=2.0,
            on_state_change=self._on_media_state_change,
        )

        self._running = False
        self._paused = False

        # -- state machine --------------------------------------------------
        self._state = _SGState.MONITORING
        self._state_lock = threading.Lock()

        # Set while the warning dialog is visible.
        self._warning_active = threading.Event()

        # Monotonic timestamp when MEDIA_GRACE began.
        self._grace_start: float = 0.0

        # Guard: only one MEDIA_GRACE per idle cycle.
        # Reset only when returning to MONITORING via user activity.
        self._media_grace_used: bool = False

        # -- legacy compat --------------------------------------------------
        self._idle_fired = threading.Event()
        self._force_trigger = threading.Event()
        self._cancel_block_until = 0.0
        self._cancel_lock = threading.Lock()
        self._poll_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._paused = not self._settings.sleepguard_enabled
        self._idle_fired.clear()
        self._force_trigger.clear()
        self._warning_active.clear()
        self._waiting_for_first_activity = True

        with self._state_lock:
            self._state = _SGState.MONITORING
            self._media_grace_used = False

        self._media_engine.start()

        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            name="SleepGuardController-poll",
            daemon=True,
        )
        self._poll_thread.start()
        logger.info(
            "[SLEEPGUARD] Controller started (enabled=%s, action=%s, countdown=%ds).",
            not self._paused,
            self._settings.sleepguard_action,
            self._settings.countdown_seconds,
        )
        self.sleepguard_status_changed.emit(not self._paused)

    def stop(self) -> None:
        self._running = False
        self._media_engine.stop()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5.0)
            self._poll_thread = None
        logger.info("[SLEEPGUARD] Controller stopped.")

    def set_enabled(self, enabled: bool) -> None:
        self._settings.sleepguard_enabled = enabled
        self._paused = not enabled
        if enabled:
            self._idle_fired.clear()
            self._warning_active.clear()
            with self._state_lock:
                self._state = _SGState.MONITORING
                self._media_grace_used = False
        logger.info("[SLEEPGUARD] State set to enabled=%s", enabled)
        self.sleepguard_status_changed.emit(enabled)

    @property
    def is_enabled(self) -> bool:
        return self._settings.sleepguard_enabled

    @property
    def current_media(self) -> MediaInfo:
        return self._media_engine.current

    @property
    def current_state(self) -> _SGState:
        with self._state_lock:
            return self._state

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def cancel_warning(self) -> None:
        """Cancel any active warning and return to MONITORING."""
        self._idle_fired.clear()
        self._warning_active.clear()
        with self._state_lock:
            self._state = _SGState.MONITORING
            self._media_grace_used = False

        cooldown = 30.0
        with self._cancel_lock:
            self._cancel_block_until = time.time() + cooldown

        self._shutdown_mgr.cancel_shutdown()
        try:
            self.programmatic_shutdown_cancelled.emit()
        except Exception:
            pass
        logger.info("[SLEEPGUARD] Warning cancelled. Applied cooldown=%ss", cooldown)
        logger.info(
            "SLEEPGUARD_TRIGGER ACTION=CANCEL IDLE_SECONDS=0 MEDIA_STATE=%s "
            "QUICK_TEST=N/A COUNTDOWN=N/A USER_INTERRUPTION=TRUE "
            "POWER_RESULT=N/A ERROR_CODE=0 FINAL_RESULT=CANCELLED",
            self._media_engine.is_playing,
        )

    def force_trigger_idle(self) -> None:
        """Force an immediate idle trigger (developer/test use)."""
        self._force_trigger.set()

    # ------------------------------------------------------------------
    # Power action
    # ------------------------------------------------------------------

    def execute_power_action(self, action: str = "") -> bool:
        """Execute the configured (or specified) power action with safety checks.

        This is the single authoritative entry point for all SleepGuard power
        actions. If action is empty, reads from settings.
        """
        from datetime import datetime

        configured_action = self._settings.sleepguard_action
        if not action:
            action = configured_action
        action = action.lower().strip()
        ts = datetime.now().isoformat()

        logger.info(
            "[SLEEPGUARD] Countdown completed. Final safety check at %s. action='%s'.",
            ts, action,
        )

        # Safety guard: validate action, fallback to lock
        if not ShutdownManager.validate_action(action):
            logger.warning(
                "[SLEEPGUARD] SAFETY GUARD: Invalid action '%s'. Defaulting to 'lock'.",
                action,
            )
            action = "lock"

        logger.info(
            "[SLEEPGUARD] Configured='%s'; effective='%s'.",
            configured_action, action,
        )

        # Cancel is not a destructive action — skip the idle safety check.
        if action == "cancel":
            logger.info("[SLEEPGUARD] Cancel action: no idle check required.")
            try:
                result = bool(self._shutdown_mgr.execute_action("cancel"))
            except Exception:
                result = True
            logger.info("SLEEPGUARD_TRIGGER ACTION=cancel IDLE_SECONDS=N/A MEDIA_STATE=%s "
                        "QUICK_TEST=N/A COUNTDOWN=0 USER_INTERRUPTION=FALSE POWER_RESULT=%s "
                        "ERROR_CODE=0 FINAL_RESULT=%s",
                        self._media_engine.is_playing,
                        "SUCCESS" if result else "FAILED",
                        "EXECUTED" if result else "FAILED")
            with self._state_lock:
                self._state = _SGState.MONITORING
                self._media_grace_used = False
            self._warning_active.clear()
            return result

        with self._state_lock:
            self._state = _SGState.FINAL_SAFETY_CHECK

        # Safety guard: if media is playing and grace was never granted, enter grace instead of immediate action
        if self._media_engine.is_playing and not self._media_grace_used:
            logger.info("[SLEEPGUARD] Media active and grace not yet exhausted. Aborting power action to grant grace.")
            with self._state_lock:
                self._state = _SGState.MEDIA_GRACE
                self._media_grace_used = True
                self._grace_start = time.monotonic()
            self._warning_active.clear()
            return False

        # Safety guard: check base idle threshold only (no media inflation).
        import os
        idle_s = get_idle_seconds()
        timeout_s = self._settings.idle_timeout_minutes * 60
        qt_env = os.getenv("DW_QUICK_TEST")
        is_quick_test = bool(qt_env and qt_env.isdigit())
        if is_quick_test:
            timeout_s = int(qt_env)
        required_idle_s = timeout_s * 0.5

        logger.info(
            "[SLEEPGUARD] Safety check: idle=%.1fs, required>=%.1fs, quick_test=%s.",
            idle_s, required_idle_s, is_quick_test,
        )

        if idle_s < required_idle_s:
            logger.error(
                "[SLEEPGUARD] Final activity/safety check result: FAILED. User active during countdown. "
                "idle=%.1f, required=%d. Aborting.", idle_s, timeout_s,
            )
            logger.info(
                "SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s "
                "QUICK_TEST=%s COUNTDOWN=0 USER_INTERRUPTION=TRUE POWER_RESULT=N/A "
                "ERROR_CODE=0 FINAL_RESULT=CANCELLED",
                action, idle_s, self._media_engine.is_playing,
                "TRUE" if is_quick_test else "FALSE",
            )
            with self._state_lock:
                self._state = _SGState.MONITORING
                self._media_grace_used = False
            self._warning_active.clear()
            return False

        logger.info("[SLEEPGUARD] Final activity/safety check result: PASSED. effective power action='%s'", action)
        logger.warning(
            "[SLEEPGUARD] Executing action='%s', timestamp=%s.", action, ts,
        )

        try:
            result = bool(self._shutdown_mgr.execute_action(action))
        except Exception as p_exc:
            logger.exception(
                "[SLEEPGUARD] Power action execution raised an unexpected exception. action='%s': %s", action, p_exc,
            )
            result = False

        logger.info(
            "[SLEEPGUARD] Power action result: action='%s', success=%s.", action, result,
        )
        logger.info(
            "SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s "
            "QUICK_TEST=%s COUNTDOWN=0 USER_INTERRUPTION=FALSE POWER_RESULT=%s "
            "ERROR_CODE=0 FINAL_RESULT=%s",
            action, idle_s, self._media_engine.is_playing,
            "TRUE" if is_quick_test else "FALSE",
            "SUCCESS" if result else "FAILED",
            "EXECUTED" if result else "FAILED",
        )

        with self._state_lock:
            self._state = _SGState.MONITORING
            self._media_grace_used = False
        self._warning_active.clear()
        return result

    def execute_shutdown(self) -> bool:
        """Legacy method -- routes through execute_power_action."""
        return self.execute_power_action()

    # ------------------------------------------------------------------
    # Internal callbacks
    # ------------------------------------------------------------------

    def _on_media_state_change(self, info: MediaInfo) -> None:
        logger.info(
            "[SLEEPGUARD] Media update: playing=%s, app=%s",
            info.is_playing, info.display_name,
        )
        self.media_state_changed.emit(info)

    # ------------------------------------------------------------------
    # Poll loop -- explicit 4-state machine
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        try:
            from tracker.foreground import _ensure_interactive_desktop
            _ensure_interactive_desktop()
        except Exception:
            pass
        start_time = time.monotonic()

        while self._running:
            time.sleep(1.0)
            if not self._running:
                break
            if self._paused:
                continue

            # While WARNING dialog is visible, only check for activity to cancel.
            if self._warning_active.is_set():
                self._check_warning_activity()
                continue

            # Quick-test env override (developer only)
            import os
            qt_env = os.getenv("DW_QUICK_TEST")
            is_quick_test = bool(qt_env and qt_env.isdigit())
            threshold_s = int(qt_env) if is_quick_test else (self._settings.idle_timeout_minutes * 60)
            grace_s = self._settings.media_grace_minutes * 60

            # Startup grace (30 s after controller start, or 5s for quick test)
            elapsed_start = time.monotonic() - start_time
            startup_grace_limit = 5.0 if is_quick_test else 30.0
            if elapsed_start < startup_grace_limit:
                continue

            # Wait for first user input after startup (or auto-arm after startup grace)
            idle_s = get_idle_seconds()
            if getattr(self, "_waiting_for_first_activity", False):
                if idle_s < 5.0 or elapsed_start >= startup_grace_limit:
                    self._waiting_for_first_activity = False
                    logger.info("[SLEEPGUARD] User activity verified or grace elapsed. SleepGuard armed.")
                else:
                    continue

            # Respect cancel cooldown
            with self._cancel_lock:
                if time.time() < self._cancel_block_until:
                    continue

            with self._state_lock:
                state = self._state

            # ==============================================================
            # STATE: MONITORING
            # ==============================================================
            if state == _SGState.MONITORING:
                idle_triggered = idle_s >= threshold_s or self._force_trigger.is_set()
                if self._force_trigger.is_set():
                    self._force_trigger.clear()

                if idle_triggered:
                    logger.info(
                        "[SLEEPGUARD] Threshold reached (idle=%.0fs, threshold=%ds). -> INACTIVE.",
                        idle_s, threshold_s,
                    )
                    with self._state_lock:
                        self._state = _SGState.INACTIVE

            # ==============================================================
            # STATE: INACTIVE
            # ==============================================================
            elif state == _SGState.INACTIVE:
                # User regained activity -> back to MONITORING
                if idle_s < threshold_s * 0.5:
                    logger.info(
                        "[SLEEPGUARD] Activity in INACTIVE (idle=%.1fs). -> MONITORING.", idle_s,
                    )
                    with self._state_lock:
                        self._state = _SGState.MONITORING
                        self._media_grace_used = False
                    continue

                media_playing = self._media_engine.is_playing
                if media_playing and not self._media_grace_used:
                    # Grant the one-shot media grace period
                    logger.info(
                        "[SLEEPGUARD] Media active at threshold -- granting one-shot grace of %ds.",
                        grace_s,
                    )
                    self._grace_start = time.monotonic()
                    with self._state_lock:
                        self._state = _SGState.MEDIA_GRACE
                        self._media_grace_used = True
                else:
                    # No media, or grace already exhausted this cycle
                    if self._media_grace_used and media_playing:
                        logger.info(
                            "[SLEEPGUARD] Media playing but grace already used. -> WARNING."
                        )
                    self._emit_warning(threshold_s, idle_s, is_quick_test)

            # ==============================================================
            # STATE: MEDIA_GRACE
            # ==============================================================
            elif state == _SGState.MEDIA_GRACE:
                elapsed_grace = time.monotonic() - self._grace_start

                # User regained activity -> back to MONITORING
                if idle_s < threshold_s * 0.5:
                    logger.info(
                        "[SLEEPGUARD] Activity in MEDIA_GRACE (idle=%.1fs). -> MONITORING.", idle_s,
                    )
                    with self._state_lock:
                        self._state = _SGState.MONITORING
                        self._media_grace_used = False
                    continue

                logger.debug(
                    "[SLEEPGUARD] MEDIA_GRACE: %.0fs / %.0fs elapsed, media=%s",
                    elapsed_grace, grace_s, self._media_engine.is_playing,
                )

                # If media stopped while user is idle, or grace expired -> warn immediately
                if not self._media_engine.is_playing:
                    logger.info(
                        "[SLEEPGUARD] Media stopped before grace expired (%.0fs elapsed). -> WARNING.",
                        elapsed_grace,
                    )
                    self._emit_warning(threshold_s, idle_s, is_quick_test)
                elif elapsed_grace >= grace_s:
                    logger.info(
                        "[SLEEPGUARD] Media grace expired (%.0fs). -> WARNING.", grace_s,
                    )
                    self._emit_warning(threshold_s, idle_s, is_quick_test)

    def _check_warning_activity(self) -> None:
        """Monitor user activity while WARNING is active; cancel if genuine activity occurs."""
        now_mono = time.monotonic()
        # Give a 2-second grace period after dialog display so pop-up events/window activation
        # do not trigger instant cancellation.
        if now_mono - getattr(self, "_warning_start_monotonic", 0.0) < 2.0:
            return

        current_tick = get_last_input_tick()
        start_tick = getattr(self, "_warning_start_input_tick", current_tick)
        tick_delta = (current_tick - start_tick) & 0xFFFFFFFF

        # Input tick advances only on genuine keyboard / mouse input events
        if 0 < tick_delta < 0x7FFFFFFF:
            logger.info(
                "[SLEEPGUARD] Genuine user activity during WARNING (input tick advanced by %d ms). Cancelling.",
                tick_delta,
            )
            self.cancel_warning()

    def _emit_warning(
        self, threshold_s: float, idle_s: float, is_quick_test: bool
    ) -> None:
        """Transition to WARNING state and signal the UI to show the dialog."""
        action = self._settings.sleepguard_action
        raw_countdown = self._settings.countdown_seconds
        countdown = max(raw_countdown, MIN_COUNTDOWN_SECONDS)
        if countdown != raw_countdown:
            logger.warning(
                "[SLEEPGUARD] Countdown %ds below floor %ds. Clamped.",
                raw_countdown, MIN_COUNTDOWN_SECONDS,
            )

        with self._state_lock:
            self._state = _SGState.WARNING
        self._warning_start_monotonic = time.monotonic()
        self._warning_start_input_tick = get_last_input_tick()
        self._idle_fired.set()
        self._warning_active.set()

        logger.warning(
            "[SLEEPGUARD] WARNING triggered: idle=%.0fs, threshold=%ds, "
            "action='%s', countdown=%ds.",
            idle_s, threshold_s, action, countdown,
        )
        logger.info(
            "SLEEPGUARD_TRIGGER ACTION=%s IDLE_SECONDS=%.1f MEDIA_STATE=%s "
            "QUICK_TEST=%s COUNTDOWN=%d USER_INTERRUPTION=FALSE "
            "POWER_RESULT=PENDING ERROR_CODE=0 FINAL_RESULT=PENDING",
            action, idle_s, self._media_engine.is_playing,
            "TRUE" if is_quick_test else "FALSE", countdown,
        )
        # Emit Qt signal -- main thread will show the dialog non-blocking
        self.shutdown_warning_triggered.emit(countdown, action)
