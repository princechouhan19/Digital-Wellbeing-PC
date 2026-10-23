"""
focus_manager.py — Focus Mode enforcement engine for Digital Wellbeing.

Enforcement model:
  - Deep Focus / Presets (Study, Work, Movie): ALLOWLIST mode.
    Only recognized user-facing apps that are NOT on the allowlist are blocked.
    System/Background apps are always allowed.
  - Custom: BLOCKLIST mode.
  - No hosts/DNS/proxy modifications.
"""
from __future__ import annotations

import time
import ctypes
import ctypes.wintypes
import threading
from typing import Dict, List, Optional

import win32gui
import win32process
import psutil

from PySide6.QtCore import QObject, Signal, QTimer
from core.logger import logger
from database.repository import Repository
from protection.pin import PINManager
from protection.website_blocker import WebsiteBlocker

DEFAULT_MODE_WEBSITES = {
    "study": ["instagram.com", "reddit.com", "youtube.com", "twitter.com", "tiktok.com"],
    "work": ["instagram.com", "reddit.com", "facebook.com", "twitter.com", "tiktok.com"],
    "movie": ["reddit.com", "twitter.com"],
    "deep": ["instagram.com", "reddit.com", "youtube.com", "twitter.com", "facebook.com", "tiktok.com"],
    "custom": ["instagram.com", "reddit.com"],
}


class FocusManager(QObject):
    focus_state_changed = Signal(bool)   # is_active
    tick = Signal(int)                   # seconds remaining
    focus_completed = Signal()
    mode_changed = Signal(str)
    app_blocked = Signal(str, str, int)  # process_name, mode_name, seconds_remaining

    _instance: Optional["FocusManager"] = None

    @classmethod
    def instance(cls, repo: Optional[Repository] = None) -> "FocusManager":
        if cls._instance is None:
            if repo is None:
                repo = Repository()
            cls._instance = FocusManager(repo)
        return cls._instance

    def __init__(self, repo: Repository, parent=None):
        super().__init__(parent)
        self._repo = repo
        self._pin_manager = PINManager(repo)
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0
        
        self._last_blocked_feedback: Dict[str, float] = {}
        self._suppressed_blocked_apps: Dict[str, float] = {}
        self._website_blocker = WebsiteBlocker()
        self._website_blocker.cleanup_orphaned_blocks()

        self._mode: str = self._repo.get_setting("focus_current_mode") or "custom"
        self._mode_apps: Dict[str, List[str]] = {
            "custom": [],
            "study": [],
            "work": [],
            "movie": [],
            "deep": []
        }
        self._mode_websites: Dict[str, List[str]] = {
            "custom": [],
            "study": [],
            "work": [],
            "movie": [],
            "deep": []
        }

        self._app_block_response: str = "close"

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        for m in self._mode_apps:
            # Fallback to legacy key for 'custom' if it exists
            key = f"focus_mode_{m}_apps"
            if m == "custom":
                stored = self._repo.get_setting(key) or self._repo.get_setting("focus_blocked_apps")
            else:
                stored = self._repo.get_setting(key)
                
            if stored:
                self._mode_apps[m] = [a.strip().lower() for a in stored.split(",") if a.strip()]

        for m in self._mode_websites:
            key = f"focus_mode_{m}_websites"
            stored = self._repo.get_setting(key)
            if stored is not None:
                self._mode_websites[m] = [w.strip().lower() for w in stored.split(",") if w.strip()]
            else:
                self._mode_websites[m] = list(DEFAULT_MODE_WEBSITES.get(m, []))

        stored_response = self._repo.get_setting("focus_app_block_response")
        if stored_response:
            self._app_block_response = stored_response

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def is_strict(self) -> bool:
        return self._is_strict

    @property
    def app_block_response(self) -> str:
        return self._app_block_response

    @property
    def seconds_remaining(self) -> int:
        return self._seconds_remaining

    @property
    def remaining_seconds(self) -> int:
        return self._seconds_remaining

    @property
    def current_mode(self) -> str:
        return self._mode

    @property
    def current_mode_apps(self) -> List[str]:
        return list(self._mode_apps.get(self._mode, []))
        
    @property
    def blocked_apps(self) -> List[str]:
        # Legacy compat for ui. Still used by some UI elements that expect a list
        return self.current_mode_apps

    @property
    def current_mode_websites(self) -> List[str]:
        return list(self._mode_websites.get(self._mode, []))

    def get_mode_websites(self, mode: str) -> List[str]:
        return list(self._mode_websites.get(mode, []))

    def save_mode_websites(self, mode: str, websites: List[str]) -> None:
        if mode in self._mode_websites:
            clean_sites = []
            for w in websites:
                c = self._website_blocker.clean_domain(w)
                if c and c not in clean_sites:
                    clean_sites.append(c)
            self._mode_websites[mode] = clean_sites
            self._repo.set_setting(f"focus_mode_{mode}_websites", ",".join(clean_sites))
            logger.info(f"[FOCUS] Saved {len(clean_sites)} websites for mode {mode}.")

    def add_mode_website(self, mode: str, website: str) -> bool:
        c = self._website_blocker.clean_domain(website)
        if not c:
            return False
        current = self.get_mode_websites(mode)
        if c not in current:
            current.append(c)
            self.save_mode_websites(mode, current)
            return True
        return False

    def remove_mode_website(self, mode: str, website: str) -> bool:
        c = self._website_blocker.clean_domain(website) or website.strip().lower()
        current = self.get_mode_websites(mode)
        if c in current:
            current.remove(c)
            self.save_mode_websites(mode, current)
            return True
        return False

    def set_mode(self, mode: str) -> None:
        if mode in self._mode_apps and not self._is_active:
            self._mode = mode
            self._repo.set_setting("focus_current_mode", mode)
            self.mode_changed.emit(mode)

    def save_mode_apps(self, mode: str, apps: List[str]) -> None:
        if mode in self._mode_apps:
            self._mode_apps[mode] = [a.strip().lower() for a in apps if a.strip()]
            self._repo.set_setting(f"focus_mode_{mode}_apps", ",".join(self._mode_apps[mode]))

    def save_blocked_apps(self, apps: List[str]) -> None:
        # Legacy compat
        self.save_mode_apps(self._mode, apps)

    def save_app_block_response(self, response: str) -> None:
        self._app_block_response = response
        self._repo.set_setting("focus_app_block_response", response)

    def _normalize_domain(self, raw_domain: str) -> str:
        """Normalize raw input into clean apex or subdomain string."""
        if not raw_domain:
            return ""
        c = self._website_blocker.clean_domain(raw_domain)
        if c:
            return c
        text = raw_domain.strip().lower()
        import re
        text = re.sub(r"^https?://", "", text)
        text = text.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        if text.startswith("www."):
            text = text[4:]
        return text.strip(". ")

    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def start_focus(self, minutes: int = 25, strict_mode: bool = False, mode: Optional[str] = None) -> bool:
        if self._is_active:
            return False

        if mode:
            self.set_mode(mode)

        if strict_mode and not self._pin_manager.is_enabled():
            logger.warning("[FOCUS] Cannot start strict mode: PIN is not configured.")
            return False

        self._is_active = True
        self._is_strict = strict_mode
        self._deadline = time.monotonic() + minutes * 60
        self._seconds_remaining = minutes * 60

        logger.info(
            f"[FOCUS] Session started. mode={self._mode}, minutes={minutes}, strict={strict_mode}, "
            f"apps={self.current_mode_apps or '(empty)'}, websites={self.current_mode_websites or '(none)'}"
        )

        # Activate website blocking if configured
        if self.current_mode_websites:
            success, msg = self._website_blocker.block_websites(self.current_mode_websites)
            if not success and ("dministrator" in msg or "ermission" in msg):
                # Direct hosts write failed (non-elevated process) — retry once
                # through the single-action UAC elevated helper.
                try:
                    from utils.elevation import run_elevated
                    ok, elev_msg = run_elevated(
                        "focus-apply", ",".join(self.current_mode_websites)
                    )
                    success, msg = ok, elev_msg
                except Exception as elev_exc:
                    logger.warning(f"[FOCUS] Elevation fallback failed: {elev_exc}")
            logger.info(f"[FOCUS] Website blocking activated: {msg}")

        # Run an immediate enforcement scan before the first timer tick
        self._run_enforcement_scan()

        self._timer.start()
        self.focus_state_changed.emit(True)
        return True

    def stop_focus(self, provided_pin: str = "") -> bool:
        if not self._is_active:
            return True

        if self._is_strict:
            if not self._pin_manager.verify_pin(provided_pin):
                logger.warning("[FOCUS] Stop denied: Invalid PIN.")
                return False

        return self._do_stop()

    def cancel_focus(self) -> bool:
        """Alias for stop_focus for backward compatibility and API clarity."""
        return self.stop_focus()

    def stop_focus_after_pin_dialog(self) -> bool:
        """
        Stop unconditionally after PinDialog has already verified the PIN.
        MUST only be called from code that received QDialog.Accepted from PinDialog.
        """
        if not self._is_active:
            return True
        return self._do_stop()

    def _do_stop(self) -> bool:
        """Internal teardown — reset state."""
        self._is_active = False
        self._is_strict = False
        self._seconds_remaining = 0
        self._timer.stop()
        self._website_blocker.unblock_all()
        self.focus_state_changed.emit(False)
        logger.info("[FOCUS] Session stopped.")
        return True

    # ------------------------------------------------------------------
    # Timer tick
    # ------------------------------------------------------------------

    def _on_tick(self) -> None:
        if not self._is_active:
            return

        if self._seconds_remaining > 0:
            # Derive remaining seconds from monotonic deadline, falling back to decrement for manual test ticks
            if hasattr(self, "_deadline") and self._deadline is not None:
                calc_rem = int(round(self._deadline - time.monotonic()))
                if 0 <= calc_rem < self._seconds_remaining:
                    self._seconds_remaining = calc_rem
                else:
                    self._seconds_remaining = max(0, self._seconds_remaining - 1)
            else:
                self._seconds_remaining = max(0, self._seconds_remaining - 1)

            self.tick.emit(self._seconds_remaining)
            self._run_enforcement_scan()
        else:
            # Session completed naturally
            self._do_stop()
            self.focus_completed.emit()
            logger.info("[FOCUS] Session completed naturally.")

    # ------------------------------------------------------------------
    # Enforcement scan — fast foreground check on tick, async deep scan
    # ------------------------------------------------------------------

    def _run_enforcement_scan(self) -> None:
        """
        Scan active user-facing applications against the Focus mode policy.
        """
        try:
            if not self._is_active:
                return

            # 1. Immediate foreground check on this tick (<0.1ms)
            self._check_foreground_app_block()

            # 2. Broader window and process scan in background thread to eliminate UI lag
            if not getattr(self, "_scan_running", False):
                self._scan_running = True
                threading.Thread(target=self._async_enforcement_scan, daemon=True).start()
        except Exception as exc:
            logger.debug(f"[FOCUS] Enforcement scan error: {exc}")

    def _async_enforcement_scan(self) -> None:
        try:
            if self._is_active:
                self._check_app_blocks()
        finally:
            self._scan_running = False

    def _check_foreground_app_block(self) -> None:
        """Immediate check on currently focused window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            from tracker.foreground import _get_real_window_pid
            fg_pid = _get_real_window_pid(hwnd)
            if fg_pid and fg_pid > 4:
                p = psutil.Process(fg_pid)
                p_name = p.name()
                try:
                    exe_path = p.exe()
                except Exception:
                    exe_path = ""

                # Check browser tab website block
                from tracker.browser_domain import is_browser_process, get_active_browser_domain
                if is_browser_process(p_name):
                    try:
                        title = win32gui.GetWindowText(hwnd) or ""
                    except Exception:
                        title = ""
                    domain = get_active_browser_domain(p_name, title, hwnd=hwnd)
                    if domain:
                        blocked_sites = self.blocked_websites()
                        if any(self._normalize_domain(site) == domain or domain.endswith("." + self._normalize_domain(site)) for site in blocked_sites):
                            from protection.process import ProcessController
                            ProcessController.close_browser_tab(hwnd)
                            now = time.time()
                            last_time = self._last_blocked_feedback.get(domain, 0.0)
                            if now - last_time >= 4.0:
                                self._last_blocked_feedback[domain] = now
                                self.app_blocked.emit(domain, self._mode, self._seconds_remaining)
                            return

                self._evaluate_process(fg_pid, p_name, exe_path, p, visible_pids={fg_pid}, is_foreground=True)
        except Exception:
            pass

    def suppress_blocked_app(self, process_name: str, duration: float = 12.0) -> None:
        """
        Suppresses repeated blocked-app dialog notifications for a process after
        the user acknowledges and clicks 'Back to Focus'.
        """
        clean_name = process_name.strip().lower()
        expiry = time.time() + duration
        self._suppressed_blocked_apps[clean_name] = expiry
        self._last_blocked_feedback[clean_name] = expiry
        logger.info(f"[FOCUS] Suppressed blocked-app popups for '{clean_name}' for {duration:.1f}s.")

    def _check_app_blocks(self) -> None:
        """
        Enforces Focus mode rules against active user-facing applications.
        Inspects:
          1. Foreground window process (immediate active window response)
          2. Processes with visible, interactive desktop windows
        Background infrastructure, helpers, services, and system components are never terminated.
        """
        try:
            from utils.win_utils import get_visible_window_pids

            visible_window_pids = get_visible_window_pids()
            active_pids: set[int] = set(visible_window_pids)

            # 1. Foreground window process
            fg_pid: Optional[int] = None
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    from tracker.foreground import _get_real_window_pid
                    fg_pid = _get_real_window_pid(hwnd)
                    if fg_pid and fg_pid > 4:
                        active_pids.add(fg_pid)
                        visible_window_pids.add(fg_pid)
            except Exception:
                pass

            # 2. Evaluate each candidate process through the safety gates
            for target_pid in active_pids:
                try:
                    p = psutil.Process(target_pid)
                    p_name = p.name()
                    try:
                        exe_path = p.exe()
                    except Exception:
                        exe_path = ""
                    self._evaluate_process(
                        target_pid,
                        p_name,
                        exe_path,
                        p,
                        visible_pids=visible_window_pids,
                        is_foreground=(target_pid == fg_pid),
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as exc:
            logger.debug(f"[FOCUS] Enforcement error: {exc}")

    def _evaluate_process(
        self,
        pid: int,
        p_name: str,
        exe_path: str,
        proc: psutil.Process,
        visible_pids: Optional[set] = None,
        is_foreground: bool = False,
    ) -> bool:
        """
        Applies the enforcement decision tree:
          1. Protected/system/OEM/capture process -> ALLOW (True)
          2. Non-interactive background / helper process -> ALLOW (True)
          3. Process tree resolution: child of allowed root application -> ALLOW (True)
          4. User-facing interactive application not in allowlist -> BLOCK (False)
        Returns True if allowed, False if blocked/restricted.
        """
        from protection.app_locker import SYSTEM_SAFE
        from utils.win_utils import (
            is_safe_lock_target,
            is_user_facing_application,
            get_session_id,
            resolve_root_application,
        )

        p_lower = p_name.lower()

        # Step 1: Protected / system process & the app itself -> ALWAYS ALLOW
        # The app (self) and its parent process tree (runner, terminal, IDE) must NEVER be terminated
        try:
            import os
            cur_pid = os.getpid()
            if pid == cur_pid:
                return True
            cur_proc = psutil.Process(cur_pid)
            if pid in (parent.pid for parent in cur_proc.parents()):
                return True
        except Exception:
            pass

        if p_lower in SYSTEM_SAFE or not is_safe_lock_target(exe_path, p_lower):
            return True

        # System services / Session 0 processes -> ALWAYS ALLOW
        if pid is not None and get_session_id(pid) == 0:
            return True

        # Step 2: Interactive Desktop Window requirement
        # When visible window PIDs are provided, headless processes without an interactive window
        # (and not foreground) are background helpers/daemons, NOT user-facing block targets!
        if visible_pids is not None:
            if pid is not None and pid not in visible_pids and not is_foreground:
                return True

        # Step 3: Non-user-facing / background / helper / infrastructure process -> ALWAYS ALLOW
        # Gated by multi-signal classification (rejects services, updaters, crash handlers, daemons, LSPs)
        if not is_user_facing_application(pid, exe_path, p_lower, visible_pids=visible_pids):
            return True

        # Multi-process safety gate: do NOT terminate child workers/renderers directly
        try:
            cmdline = proc.cmdline()
            if any(arg.startswith("--type=") for arg in cmdline):
                return True  # Internal worker/helper child, ignore directly
        except Exception:
            pass

        # Step 4: Multi-process Application Tree Resolution
        # Climb ancestor tree to identify the root user application (e.g. Code.exe, Discord.exe)
        root_proc, root_name = resolve_root_application(proc)
        root_lower = root_name.lower() if root_name else p_lower

        mode = self._mode
        mode_apps = self._mode_apps.get(mode, [])

        # Allowlist Modes (Study, Work, Movie, Deep Focus)
        if mode in ("study", "work", "movie", "deep"):
            # Fail-open guard: an unconfigured allowlist must not block everything.
            # Without apps to keep, "allow-only" semantics would terminate every
            # user-facing application the moment a session starts.
            if not mode_apps:
                logger.warning(
                    "[FOCUS] Allowlist mode %r has no apps configured — "
                    "failing open (blocking nothing this scan).",
                    mode,
                )
                return True
            # Check if either the process itself OR its root application is in the allowlist
            is_allowed = any(a in p_lower for a in mode_apps) or (
                root_lower and any(a in root_lower for a in mode_apps)
            )
            if is_allowed:
                return True

            # Target root/user-facing application for restriction and feedback
            block_target = root_proc if (root_proc and root_lower != p_lower and hasattr(root_proc, "kill")) else proc
            block_name = root_lower if (root_lower and root_lower != p_lower) else p_lower
            self._handle_blocked_app(block_target, block_name)
            return False

        # Blocklist Mode (Custom)
        else:
            # Blocks only if explicitly on the user's blocklist (by name or root application)
            is_blocked = any(a in p_lower for a in mode_apps) or (
                root_lower and any(a in root_lower for a in mode_apps)
            )
            if is_blocked:
                block_target = root_proc if (root_proc and root_lower != p_lower and hasattr(root_proc, "kill")) else proc
                block_name = root_lower if (root_lower and root_lower != p_lower) else p_lower
                self._handle_blocked_app(block_target, block_name)
                return False
            return True

    # ------------------------------------------------------------------
    # App blocking handler
    # ------------------------------------------------------------------

    def _handle_blocked_app(self, proc, p_name: str) -> None:
        try:
            if self._app_block_response == "close":
                logger.info(f"[FOCUS] Terminating restricted app {p_name}.")
                proc.kill()
            else:
                logger.debug(f"[FOCUS] Restricted app in foreground: {p_name}")

            now = time.time()
            # Suppression check (e.g. user acknowledged and clicked "Back to Focus")
            suppressed_until = self._suppressed_blocked_apps.get(p_name, 0.0)
            if now < suppressed_until:
                return

            # Rate-limited user feedback to avoid notification spam (6s debounce)
            last_time = self._last_blocked_feedback.get(p_name, 0.0)
            if now - last_time >= 6.0:
                self._last_blocked_feedback[p_name] = now
                self.app_blocked.emit(p_name, self._mode, self._seconds_remaining)
        except Exception as exc:
            logger.warning(f"[FOCUS] Failed to handle restricted app {p_name}: {exc}")
