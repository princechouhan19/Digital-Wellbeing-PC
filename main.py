from __future__ import annotations

import sys
import traceback

def _show_fatal_error(msg: str) -> None:
    try:
        import ctypes
        MB_OK = 0x0
        MB_ICONERROR = 0x10
        ctypes.windll.user32.MessageBoxW(0, msg, "Digital Wellbeing — Startup Error", MB_OK | MB_ICONERROR)
    except Exception:
        pass

try:
    import argparse
    import time
    from pathlib import Path
except Exception as e:
    _show_fatal_error(f"A critical error occurred while initializing the application.\n\nError details: {e}")
    sys.exit(1)


def _early_log(msg: str) -> None:
    try:
        p = Path.home() / "AppData" / "Local" / "DigitalWellbeing"
        p.mkdir(parents=True, exist_ok=True)
        with open(p / "startup_diagnostic.txt", "a", encoding="utf-8") as f:
            import datetime
            f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass

_early_log("--- NEW STARTUP ---")
_early_log(f"Executable: {sys.executable}")
_early_log(f"Python version: {sys.version}")

def _setup_path() -> None:
    root = Path(__file__).parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def run_headless_service() -> None:
    from core.logger import logger
    logger.info("Starting Digital Wellbeing Headless Tracking Service")
    
    from tracker.manager import TrackingManager
    tracker = TrackingManager()
    
    try:
        tracker.start()
        # Keep the main thread alive while tracker runs in its daemon thread
        while tracker.is_running:
            time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Headless service interrupted. Stopping tracker.")
    except Exception as exc:
        logger.critical("Headless service fatal error: %s", exc, exc_info=True)
    finally:
        tracker.stop()


def main() -> None:
    _setup_path()
    
    # Set AppUserModelID for proper Windows Taskbar grouping
    import platform
    if platform.system() == "Windows":
        try:
            import ctypes
            from core.constants import APP_AUMID
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_AUMID)
        except Exception as e:
            from core.logger import logger
            logger.warning(f"Could not set AppUserModelID: {e}")

    parser = argparse.ArgumentParser(description="Digital Wellbeing Tracker")
    parser.add_argument(
        "--service",
        action="store_true",
        help="Run the tracking engine as a headless background service.",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Launch the GUI application minimized to the system tray.",
    )
    parser.add_argument(
        "--elevated-helper",
        action="store_true",
        help="Run as privileged helper. Requires UAC elevation.",
    )
    parser.add_argument(
        "--action",
        type=str,
        help="Elevated helper action (apply or remove).",
    )
    parser.add_argument(
        "--domains",
        type=str,
        default="",
        help="Comma separated domains for elevated helper.",
    )
    parser.add_argument(
        "--focus-watchdog",
        action="store_true",
        help="Internal: relaunch the app if a lockout session process disappears.",
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=0,
        help="Internal: parent process id for the lockout watchdog.",
    )
    parser.add_argument(
        "--deadline",
        type=float,
        default=0.0,
        help="Internal: epoch deadline for the lockout watchdog.",
    )
    args = parser.parse_args()

    if args.focus_watchdog:
        from protection.focus_watchdog import run_watchdog

        sys.exit(run_watchdog(args.parent_pid, args.deadline))

    from core.logger import logger
    
    if args.service:
        run_headless_service()
        sys.exit(0)
        
    if args.elevated_helper:
        from protection.elevated_helper import run_elevated_action
        success = run_elevated_action(args.action or "", args.domains)
        sys.exit(0 if success else 1)

    logger.info("[LIFECYCLE] Starting Digital Wellbeing GUI Application (main.py entry)")
    FOCUS_ENFORCEMENT_BUILD_MARKER = "FOCUS-V3-1-4-CLOSE-TAB"
    logger.info(f"[DIAGNOSTICS] {FOCUS_ENFORCEMENT_BUILD_MARKER}")
    
    try:
        from ui.app import DigitalWellbeingApp
        from utils.debug_lifecycle import log_lifecycle_state
        
        log_lifecycle_state("main.py: before DigitalWellbeingApp instantiation")
        app = DigitalWellbeingApp(start_minimized=args.background)
        
        import datetime
        import sys
        import os
        import os
        
        logger.info(f"[DEBUG BUILD] Build timestamp: {datetime.datetime.now().isoformat()}")
        logger.info(f"EXECUTABLE PATH: {sys.executable}")
        logger.info(f"FILE PATH: {__file__}")
        logger.info(f"CWD: {os.getcwd()}")
        
        logger.info("[LIFECYCLE] Entering QApplication.exec()")
        log_lifecycle_state("main.py: before QApplication.exec()")
        
        exit_code = app.run()
        
        logger.info("[LIFECYCLE] QApplication.exec() RETURNED with exit code %d", exit_code)
        log_lifecycle_state("main.py: after QApplication.exec() returned")
    except Exception as exc:
        clean_err_msg = f"A fatal error occurred during execution: {exc}\nPlease check the application logs."
        logger.critical("Fatal error: %s", exc, exc_info=True)
        _early_log(f"main() Fatal error caught: {type(exc).__name__} - {exc}")
        _early_log(traceback.format_exc())
        _show_fatal_error(clean_err_msg)
        exit_code = 1

    import os
    logger.info("[LIFECYCLE] Exiting process via os._exit(%d)", exit_code)
    os._exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except Exception as global_exc:
        clean_err_msg = f"A critical startup error occurred: {global_exc}\nPlease check the application logs."
        full_err_msg = f"FATAL STARTUP EXCEPTION: {type(global_exc).__name__}: {global_exc}\n\n{traceback.format_exc()}"
        _early_log(full_err_msg)
        _show_fatal_error(clean_err_msg)
        import os
        os._exit(1)
