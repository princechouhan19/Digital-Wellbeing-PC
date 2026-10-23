"""
focus_watchdog.py — Best-effort relaunch guard for Strict Lockout sessions.

This is intentionally *not* a kernel-level tamper-proof service. It cannot
survive Safe Mode, an administrator killing both processes, or a reboot with
autostart disabled. It does make casual "just kill it in Task Manager" attempts
recover the lockout session by relaunching the app, which then restores the
persisted deadline.

The watchdog is a normal unprivileged child process. It exits as soon as the
deadline passes or the parent ends the session normally (the parent terminates
it). No files, registry keys, services, or scheduled tasks are created.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def _app_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return [sys.executable, str(main_py)]


def spawn_watchdog(deadline_epoch: float, parent_pid: Optional[int] = None) -> Optional[subprocess.Popen]:
    """Start a detached watchdog process; returns None in test/unsupported mode."""
    if os.environ.get("DW_TEST_MODE") == "1":
        return None
    if sys.platform != "win32":
        return None
    parent_pid = parent_pid or os.getpid()
    if getattr(sys, "frozen", False):
        args = [sys.executable, "--focus-watchdog", "--parent-pid", str(parent_pid), "--deadline", f"{deadline_epoch:.3f}"]
    else:
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        args = [
            sys.executable,
            str(main_py),
            "--focus-watchdog",
            "--parent-pid",
            str(parent_pid),
            "--deadline",
            f"{deadline_epoch:.3f}",
        ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return subprocess.Popen(
            args,
            creationflags=creationflags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None


def run_watchdog(parent_pid: int, deadline_epoch: float, poll_s: float = 5.0) -> int:
    """Wait for the parent to disappear before the deadline, then relaunch once."""
    try:
        import psutil
    except Exception:
        psutil = None  # type: ignore[assignment]

    while time.time() < deadline_epoch:
        alive = False
        if psutil is not None:
            try:
                alive = psutil.pid_exists(parent_pid)
            except Exception:
                alive = False
        else:
            try:
                os.kill(parent_pid, 0)
                alive = True
            except OSError:
                alive = False

        if not alive:
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                subprocess.Popen(
                    _app_command(),
                    creationflags=creationflags,
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
            return 0
        time.sleep(max(1.0, poll_s))
    return 0
