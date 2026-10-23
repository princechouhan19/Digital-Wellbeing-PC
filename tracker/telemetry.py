"""
telemetry.py — Strictly opt-in anonymous usage heartbeat.

Privacy contract (aligned with the "Local-First & Zero Telemetry" promise):
  - Disabled by default. No network request is ever made unless the user
    explicitly enables "Share anonymous usage statistics" in Settings.
  - The payload contains ONLY an anonymous install id and the app version.
    No personal data, no window titles, no process names, no usage metrics.
  - The endpoint is configurable via the DW_TELEMETRY_ENDPOINT environment
    variable (self-hosted instances supported); it is empty by default, in
    which case the heartbeat is a no-op even when opted in.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request

from core.logger import logger
from core.constants import APP_VERSION
from settings.manager import SettingsManager

_TIMEOUT_S = 5.0


class TelemetryManager:
    _instance = None

    @classmethod
    def instance(cls) -> "TelemetryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.settings = SettingsManager()
        self._endpoint = os.environ.get("DW_TELEMETRY_ENDPOINT", "").strip()
        self._thread: threading.Thread | None = None

    def start_heartbeat(self):
        """Spawns a daemon thread to send the opt-in telemetry heartbeat."""
        # Privacy gate 1: user opt-in (default OFF)
        if not self.settings.get_bool("share_anonymous_stats", False):
            logger.debug("Telemetry disabled (not opted in). Skipping heartbeat.")
            return
        # Privacy gate 2: an endpoint must be configured
        if not self._endpoint:
            logger.debug("Telemetry endpoint not configured. Skipping heartbeat.")
            return
        if self._thread and self._thread.is_alive():
            return

        self._thread = threading.Thread(target=self._send_heartbeat, daemon=True, name="DW-Telemetry")
        self._thread.start()

    def _send_heartbeat(self):
        install_id = self.settings.install_id
        if not install_id:
            return

        payload = {
            "installId": install_id,
            "version": APP_VERSION,
        }

        try:
            req = urllib.request.Request(
                self._endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S):
                logger.info("Anonymous telemetry heartbeat sent successfully.")
        except Exception as e:
            # Swallow all exceptions to ensure offline capability
            logger.debug(f"Telemetry heartbeat failed (offline or server unreachable): {e}")
