"""
diagnostics.py — Fullscreen Application Tracking Diagnostic Tool for Digital Wellbeing v2.4.

Standalone diagnostic tool that continuously logs foreground window state at ~1-second
resolution. Designed to identify exactly where tracking gaps occur during fullscreen
game sessions (e.g. Valorant) without modifying production behavior.

Usage:
    python -m tracker.diagnostics [--duration SECONDS] [--output FILE]

Output columns:
    timestamp | HWND | window_title | PID | process_exe | process_path |
    detected_app | category | is_fullscreen | is_cloaked | is_overlay |
    session_would_split | reason
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure project root is on path
_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def run_diagnostics(duration_s: int = 1800, output_path: str = "tracking_diagnostics.csv") -> None:
    """Run the diagnostic logger for the specified duration.
    
    Args:
        duration_s: How long to run in seconds (default: 30 minutes).
        output_path: CSV file to write results to.
    """
    import win32gui
    import win32process
    import psutil

    from tracker.foreground import (
        ForegroundApp,
        _get_process_info,
        _get_real_window_pid,
        _get_root_owner_window,
        _is_generic_overlay,
        _is_window_cloaked,
        is_window_fullscreen,
    )
    from tracker.categorizer import categorize, display_name

    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  Digital Wellbeing — Fullscreen Tracking Diagnostics v2.4  ║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Duration:  {duration_s}s ({duration_s // 60}m {duration_s % 60}s)")
    print(f"║  Output:    {output_path}")
    print(f"║  Interval:  ~1 second")
    print(f"║  Press Ctrl+C to stop early")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print()

    # CSV columns
    fieldnames = [
        "timestamp",
        "hwnd",
        "root_hwnd",
        "window_title",
        "pid",
        "process_name",
        "process_path",
        "category",
        "display_name",
        "is_fullscreen",
        "is_cloaked",
        "is_overlay",
        "is_visible",
        "change_type",
        "prev_process",
        "prev_title",
        "change_reason",
        "elapsed_since_last_change_s",
    ]

    prev_process: Optional[str] = None
    prev_title: Optional[str] = None
    prev_pid: Optional[int] = None
    last_change_time: float = time.monotonic()
    poll_count = 0
    change_count = 0

    stopped = False
    def _handle_sigint(sig, frame):
        nonlocal stopped
        stopped = True
        print("\n[DIAG] Ctrl+C received. Stopping...")

    signal.signal(signal.SIGINT, _handle_sigint)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        start_time = time.monotonic()

        while not stopped and (time.monotonic() - start_time) < duration_s:
            poll_count += 1
            now = datetime.now()
            ts = now.isoformat(timespec="milliseconds")

            try:
                hwnd = win32gui.GetForegroundWindow()
            except Exception:
                hwnd = 0

            is_visible = False
            is_cloaked = False
            is_overlay = False
            is_fs = False
            root_hwnd = 0
            title = ""
            pid = 0
            name = ""
            path = ""
            cat = ""
            dname = ""

            if hwnd:
                try:
                    is_visible = bool(win32gui.IsWindowVisible(hwnd))
                except Exception:
                    pass

                is_cloaked = _is_window_cloaked(hwnd)
                is_overlay = _is_generic_overlay(hwnd)

                try:
                    root_hwnd = _get_root_owner_window(hwnd) or hwnd
                except Exception:
                    root_hwnd = hwnd

                try:
                    title = win32gui.GetWindowText(root_hwnd) or win32gui.GetWindowText(hwnd) or ""
                except Exception:
                    pass

                try:
                    pid = _get_real_window_pid(root_hwnd) or _get_real_window_pid(hwnd)
                except Exception:
                    pass

                if pid and pid > 4:
                    try:
                        name, path = _get_process_info(pid, root_hwnd)
                    except Exception:
                        pass

                    if name:
                        try:
                            cat = categorize(name, path).value
                        except Exception:
                            cat = "?"
                        try:
                            dname = display_name(name)
                        except Exception:
                            dname = name

                    is_fs = is_window_fullscreen(root_hwnd)

            # Detect changes
            change_type = "SAME"
            change_reason = ""
            if name != prev_process:
                change_type = "PROCESS_CHANGE"
                change_reason = f"Process changed: {prev_process} → {name}"
                change_count += 1
            elif title != prev_title and name:
                change_type = "TITLE_CHANGE"
                change_reason = f"Title changed (same process: {name})"
            elif not hwnd or not is_visible:
                if prev_process:
                    change_type = "LOST_FOCUS"
                    change_reason = f"Foreground lost (hwnd={hwnd}, visible={is_visible})"

            elapsed_since_change = time.monotonic() - last_change_time

            row = {
                "timestamp": ts,
                "hwnd": hwnd,
                "root_hwnd": root_hwnd,
                "window_title": title[:200] if title else "",
                "pid": pid,
                "process_name": name or "",
                "process_path": path or "",
                "category": cat,
                "display_name": dname,
                "is_fullscreen": is_fs,
                "is_cloaked": is_cloaked,
                "is_overlay": is_overlay,
                "is_visible": is_visible,
                "change_type": change_type,
                "prev_process": prev_process or "",
                "prev_title": (prev_title or "")[:200],
                "change_reason": change_reason,
                "elapsed_since_last_change_s": f"{elapsed_since_change:.1f}",
            }
            writer.writerow(row)

            # Console output for significant events
            if change_type != "SAME":
                elapsed_str = f"{elapsed_since_change:.1f}s"
                fs_tag = " [FULLSCREEN]" if is_fs else ""
                cloaked_tag = " [CLOAKED]" if is_cloaked else ""
                overlay_tag = " [OVERLAY]" if is_overlay else ""

                print(
                    f"[{ts}] {change_type}: {name or '(none)'}{fs_tag}{cloaked_tag}{overlay_tag} "
                    f"| PID:{pid} | Title: {title[:60]!r} | Prev held: {elapsed_str}"
                )
                last_change_time = time.monotonic()

            if change_type in ("PROCESS_CHANGE", "LOST_FOCUS"):
                prev_process = name if name else None
                prev_title = title if title else None
                prev_pid = pid if pid else None
            elif change_type == "TITLE_CHANGE":
                prev_title = title

            # Periodic status line every 60 seconds
            if poll_count % 60 == 0:
                elapsed_total = time.monotonic() - start_time
                remaining = duration_s - elapsed_total
                print(
                    f"  ... [{poll_count} polls | {change_count} changes | "
                    f"{elapsed_total:.0f}s elapsed | {remaining:.0f}s remaining | "
                    f"Current: {name or '(none)'} | FS: {is_fs}]"
                )

            time.sleep(1.0)

    elapsed_total = time.monotonic() - start_time
    print()
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  Diagnostics Complete                                      ║")
    print(f"╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Total polls:    {poll_count}")
    print(f"║  Total changes:  {change_count}")
    print(f"║  Total time:     {elapsed_total:.0f}s")
    print(f"║  Output file:    {output_path}")
    print(f"╚══════════════════════════════════════════════════════════════╝")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Digital Wellbeing — Fullscreen Tracking Diagnostics Tool"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=1800,
        help="Duration to run in seconds (default: 1800 = 30 minutes)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="tracking_diagnostics.csv",
        help="Output CSV file path (default: tracking_diagnostics.csv)",
    )
    args = parser.parse_args()
    run_diagnostics(duration_s=args.duration, output_path=args.output)


if __name__ == "__main__":
    main()
