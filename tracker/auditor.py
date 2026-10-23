"""
auditor.py — Verbose Debug Tracking Auditor for Digital Wellbeing.

Provides structured audit logs for foreground window polling, process lookup,
session creation/ending, and ignore reasons for diagnostic verification.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from tracker.foreground import ForegroundApp

logger = logging.getLogger("tracker.auditor")


class TrackingAuditor:
    @staticmethod
    def log_poll_event(
        fg: Optional[ForegroundApp],
        action: str,
        reason: str = "",
        session_id: Optional[int] = None,
    ) -> None:
        ts = datetime.now().isoformat()
        if fg is None:
            logger.debug(
                "[TRACKING AUDIT] %s | Action: %s | App: None | Reason: %s",
                ts, action, reason or "No foreground window detected"
            )
            return

        logger.debug(
            "[TRACKING AUDIT] %s | Action: %s | App: %s | Exe: %s | PID: %d | Title: %r | SessionID: %s | Reason: %s",
            ts,
            action,
            fg.process_name,
            fg.exe_path or "Unknown",
            fg.pid,
            fg.window_title,
            str(session_id) if session_id else "N/A",
            reason or "N/A",
        )
