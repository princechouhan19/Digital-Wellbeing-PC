import os
import psutil
from core.logger import logger
from utils.win_utils import is_safe_lock_target

class ProcessController:
    @staticmethod
    def close_process(process_name: str) -> bool:
        """Terminate user processes matching process_name cleanly and without blocking the UI."""
        if not process_name:
            return False

        proc_lower = process_name.lower()
        if not proc_lower.endswith(".exe"):
            proc_lower += ".exe"

        logger.info(f"ProcessController: Terminating process {proc_lower}")
        my_pid = os.getpid()
        killed_any = False

        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    if pid <= 4 or pid == my_pid:
                        continue
                    name = (proc.info["name"] or "").lower()
                    if name == proc_lower:
                        try:
                            exe = proc.exe()
                        except Exception:
                            exe = ""
                        if not is_safe_lock_target(exe, name):
                            continue
                        proc.kill()
                        killed_any = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return killed_any
        except Exception as exc:
            logger.error(f"ProcessController failed to close {process_name}: {exc}")
            return False

    @staticmethod
    def close_browser_tab(hwnd: int = 0) -> bool:
        """Gracefully closes the active browser tab without terminating the browser process."""
        try:
            import win32gui
            import win32con
            import win32api
            if not hwnd:
                hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return False
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('W'), 0, 0, 0)
            win32api.keybd_event(ord('W'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            logger.info(f"ProcessController: Sent Ctrl+W to close active tab on hwnd {hwnd}")
            return True
        except Exception as exc:
            logger.error(f"ProcessController failed to close browser tab: {exc}")
            return False
