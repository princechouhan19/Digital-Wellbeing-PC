"""
windows_hello.py — Windows Hello authentication bridge for App Locker.

Wraps the WinRT UserConsentVerifier API in a QThread so async WinRT calls
never block the Qt main thread.  The caller connects to the `result_ready`
signal emitted on the Qt main thread after authentication completes.

Usage (Qt main thread):
    from protection.windows_hello import WindowsHelloAuth, HelloResult, HelloAvailability

    auth = WindowsHelloAuth()
    avail = auth.check_availability()          # synchronous, fast (~2 ms)

    def on_result(result: HelloResult) -> None:
        if result == HelloResult.VERIFIED:
            ...

    auth.result_ready.connect(on_result)
    auth.request_verification("Unlock Brave Browser")  # non-blocking
"""
from __future__ import annotations

import asyncio
from enum import IntEnum
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from core.logger import logger


# ── Public enums ─────────────────────────────────────────────────────────────

class HelloAvailability(IntEnum):
    AVAILABLE         = 0   # Windows Hello configured and ready
    UNAVAILABLE       = 1   # No biometric hardware or Hello not set up
    NOT_CONFIGURED    = 2   # Hardware present but user hasn't enrolled
    ERROR             = 99  # Unexpected error during availability check


class HelloResult(IntEnum):
    VERIFIED          = 0   # Authentication succeeded
    CANCELED          = 1   # User canceled
    FAILED            = 2   # Authentication failed (wrong biometric/PIN)
    UNAVAILABLE       = 3   # Device not present
    NOT_CONFIGURED    = 4   # Not configured for this user
    DEVICE_BUSY       = 5   # Device busy, try again
    ERROR             = 99  # Unexpected error


# ── Internal worker ───────────────────────────────────────────────────────────

class _HelloWorker(QThread):
    """Runs a single Windows Hello verification request asynchronously.

    Emits result_ready(HelloResult) on the Qt main thread when complete.
    """
    result_ready = Signal(int)  # HelloResult value

    def __init__(self, message: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._message = message

    def run(self) -> None:
        result = HelloResult.ERROR
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerifier,
                UserConsentVerificationResult,
            )

            async def _verify() -> HelloResult:
                verification = await UserConsentVerifier.request_verification_async(
                    self._message
                )
                mapping = {
                    UserConsentVerificationResult.VERIFIED:              HelloResult.VERIFIED,
                    UserConsentVerificationResult.CANCELED:              HelloResult.CANCELED,
                    UserConsentVerificationResult.DEVICE_NOT_PRESENT:    HelloResult.UNAVAILABLE,
                    UserConsentVerificationResult.NOT_CONFIGURED_FOR_USER: HelloResult.NOT_CONFIGURED,
                    UserConsentVerificationResult.DISABLED_BY_POLICY:    HelloResult.UNAVAILABLE,
                    UserConsentVerificationResult.DEVICE_BUSY:           HelloResult.DEVICE_BUSY,
                    UserConsentVerificationResult.RETRIES_EXHAUSTED:     HelloResult.FAILED,
                }
                return mapping.get(verification, HelloResult.ERROR)

            result = asyncio.run(_verify())

        except ModuleNotFoundError:
            logger.warning("winrt-Windows.Security.Credentials.UI not installed; Windows Hello unavailable.")
            result = HelloResult.UNAVAILABLE
        except Exception as exc:
            logger.error("WindowsHello verification error: %s", exc)
            result = HelloResult.ERROR

        self.result_ready.emit(int(result))


# ── Public API ────────────────────────────────────────────────────────────────

class WindowsHelloAuth(QObject):
    """Thread-safe Windows Hello authentication helper.

    All public methods are safe to call from the Qt main thread.
    The ``result_ready`` signal is emitted on the Qt main thread.
    """

    result_ready = Signal(int)  # HelloResult value; connect before calling request_verification()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._worker: Optional[_HelloWorker] = None

    # ------------------------------------------------------------------
    # Availability check (synchronous, returns quickly from cached state)
    # ------------------------------------------------------------------

    def check_availability(self) -> HelloAvailability:
        """Check whether Windows Hello is available on this machine.

        Runs the WinRT async call synchronously via asyncio.run().
        Typically completes in < 5 ms and is safe to call at startup.
        Returns HelloAvailability enum.
        """
        try:
            from winrt.windows.security.credentials.ui import (
                UserConsentVerifier,
                UserConsentVerifierAvailability,
            )

            async def _check() -> HelloAvailability:
                avail = await UserConsentVerifier.check_availability_async()
                if avail == UserConsentVerifierAvailability.AVAILABLE:
                    return HelloAvailability.AVAILABLE
                if avail == UserConsentVerifierAvailability.NOT_CONFIGURED_FOR_USER:
                    return HelloAvailability.NOT_CONFIGURED
                return HelloAvailability.UNAVAILABLE

            return asyncio.run(_check())

        except ModuleNotFoundError:
            logger.warning("winrt-Windows.Security.Credentials.UI not installed.")
            return HelloAvailability.UNAVAILABLE
        except Exception as exc:
            logger.error("WindowsHello availability check error: %s", exc)
            return HelloAvailability.ERROR

    # ------------------------------------------------------------------
    # Asynchronous verification (non-blocking)
    # ------------------------------------------------------------------

    def request_verification(self, message: str) -> None:
        """Show the Windows Hello prompt.  Non-blocking.

        Connect ``result_ready`` before calling this method.  The signal
        is emitted on the Qt main thread when the user completes or
        dismisses the Windows Hello dialog.

        Args:
            message: Text shown inside the Windows Hello dialog.
        """
        # Cancel any in-flight request first
        if self._worker and self._worker.isRunning():
            logger.warning("WindowsHello: previous request still running; ignoring new request.")
            return

        self._worker = _HelloWorker(message, parent=self)
        self._worker.result_ready.connect(self.result_ready)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def is_busy(self) -> bool:
        """Return True if a Windows Hello request is in progress."""
        return bool(self._worker and self._worker.isRunning())
