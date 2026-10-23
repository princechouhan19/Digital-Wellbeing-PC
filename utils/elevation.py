"""
elevation.py — UAC elevation utilities for privileged host operations.

Provides a minimal, auditable bridge for the two privileged operations the
app supports: writing the Windows hosts file (Focus Mode website blocking
and the SafeBrowse content filter) and flushing the DNS cache.

Design guarantees:
  - Least privilege: the elevated helper process runs a single, explicit
    action (--elevated-helper --action <name>) and exits immediately.
  - No interactive surface in the helper: it never touches the GUI or the
    tracking engine.
  - Result handshake: the helper writes a JSON status file into AppData so
    the parent (non-elevated) process can report success/failure to the UI.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

from core.logger import logger

STATUS_FILE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "DigitalWellbeing"
STATUS_FILE = STATUS_FILE_DIR / "elevated_action_status.json"

# Actions the helper is allowed to execute (allow-list; anything else is refused)
ALLOWED_ACTIONS = {
    "focus-apply",
    "focus-remove",
    "content-apply",
    "content-remove",
}


def status_path() -> Path:
    STATUS_FILE_DIR.mkdir(parents=True, exist_ok=True)
    return STATUS_FILE


def write_status(action: str, success: bool, message: str, detail: str = "") -> None:
    """Write the handshake status file (called by the elevated helper)."""
    try:
        status_path().write_text(
            json.dumps({
                "action": action,
                "success": bool(success),
                "message": message,
                "detail": detail,
                "ts": time.time(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.debug(f"[ELEVATION] Could not write status file: {exc}")


def read_status(max_age_s: float = 120.0) -> Optional[dict]:
    """Read the most recent helper status (called by the parent process)."""
    try:
        if not STATUS_FILE.exists():
            return None
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        if time.time() - float(data.get("ts", 0)) > max_age_s:
            return None
        return data
    except Exception:
        return None


def _current_executable() -> str:
    """Absolute path of the running interpreter / frozen executable."""
    return sys.executable


def run_elevated(action: str, domains: str = "", timeout_s: float = 90.0) -> Tuple[bool, str]:
    """
    Relaunch this executable as an elevated helper performing `action`.

    Uses PowerShell Start-Process -Verb RunAs -Wait -PassThru so we obtain
    the helper's exit code. Triggers a single UAC consent prompt.

    Returns (success, message).
    """
    if action not in ALLOWED_ACTIONS:
        return False, f"Unknown elevated action: {action}"

    exe = _current_executable()
    # Quote every argument defensively
    inner_args = f'--elevated-helper --action "{action}"'
    if domains:
        inner_args += f' --domains "{domains}"'

    ps_cmd = (
        "$p = Start-Process -FilePath $exe -ArgumentList $args "
        "-Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    )

    # Remove any stale status so we only read THIS run's result
    try:
        if STATUS_FILE.exists():
            STATUS_FILE.unlink()
    except Exception:
        pass

    try:
        cmd = [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "$exe = @'\n" + exe + "\n'@;",
            "$args = @'" + inner_args + "'@ -split ' ';",
            ps_cmd,
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
        )
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        return False, "Elevation prompt timed out"
    except Exception as exc:
        logger.warning(f"[ELEVATION] Failed to launch elevated helper: {exc}")
        return False, "Could not launch the elevated helper"

    if exit_code != 0:
        detail = (proc.stderr or proc.stdout or "").strip()[:300]
        return False, f"Privileged action failed (code {exit_code}). {detail}".strip()

    # Prefer the helper's own richer status message when available
    status = read_status(max_age_s=15.0)
    if status and status.get("action") == action:
        if status.get("success"):
            return True, str(status.get("message", "Done"))
        detail = str(status.get("detail", ""))
        return False, str(status.get("message", "Privileged action failed")) + (f" {detail}" if detail else "")

    return True, "Done"


def is_elevated_helper_call(argv: Optional[list] = None) -> bool:
    argv = sys.argv if argv is None else argv
    return "--elevated-helper" in argv
