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
import json
import threading
from datetime import date, datetime
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
    session_recap_ready = Signal(object)
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
        self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        self._is_strict = False
        self._lockout = False
        self._watchdog_proc = None
        self._seconds_remaining = 0
        self._session_total_seconds = 0
        self._focus_session_id: Optional[int] = None
        self._focus_started_at: Optional[datetime] = None
        self._blocked_apps_counts: Dict[str, int] = {}
        self._blocked_sites_counts: Dict[str, int] = {}
        self._interruptions = 0
        self._block_count_last: Dict[str, float] = {}
        self._auto_started = False
        self._schedule_id = ""
        self._emergency_unlock_at: Optional[float] = None
        
        self._last_blocked_feedback: Dict[str, float] = {}
        self._suppressed_blocked_apps: Dict[str, float] = {}
        self._website_blocker = WebsiteBlocker()
        self._website_blocker.cleanup_orphaned_blocks()

        from protection.url_rules import UrlRuleEngine

        self._url_rule_engine = UrlRuleEngine(repo)
        self._url_rules_cache = None

        self._rules_revision: int = 1

        # The browser extension bridge asks this manager for a decision on each
        # navigation and fetches synced rule batches. Registration is cheap and
        # does not start the server.
        try:
            from protection.extension_bridge import ExtensionBridge

            bridge = ExtensionBridge.instance()
            bridge.set_decision_provider(self.check_url)
            bridge.set_rules_provider(self.get_extension_rules)
        except Exception:
            pass

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

        # A lockout session survives an unexpected app termination. Restore it
        # before any UI is built so the countdown and guards are immediately
        # active again.
        self._restore_active_session()

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
    def is_lockout(self) -> bool:
        return self._lockout

    @property
    def app_block_response(self) -> str:
        return self._app_block_response

    @property
    def seconds_remaining(self) -> int:
        return self._seconds_remaining

    @property
    def session_total_seconds(self) -> int:
        return self._session_total_seconds

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

    def blocked_websites(self) -> List[str]:
        """Return the current mode's blocked domains (legacy alias used by the
        foreground enforcement path)."""
        return self.current_mode_websites

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

    # ------------------------------------------------------------------
    # Granular URL rules + extension bridge
    # ------------------------------------------------------------------

    def url_rules(self) -> list:
        if self._url_rules_cache is None:
            self._url_rules_cache = self._url_rule_engine.load()
        return list(self._url_rules_cache)

    def add_url_rule(self, pattern: str, action: str, label: str = ""):
        rule = self._url_rule_engine.add(pattern, action, label)
        if rule is not None:
            self._url_rules_cache = None
            self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        return rule

    def remove_url_rule(self, rule_id: str) -> bool:
        removed = self._url_rule_engine.remove(rule_id)
        if removed:
            self._url_rules_cache = None
            self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        return removed

    def set_url_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        changed = self._url_rule_engine.set_enabled(rule_id, enabled)
        if changed:
            self._url_rules_cache = None
            self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        return changed

    def apply_url_preset(self, preset_name: str) -> int:
        added = self._url_rule_engine.apply_preset(preset_name)
        if added:
            self._url_rules_cache = None
            self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        return added

    def export_url_rules(self, path: str) -> int:
        return self._url_rule_engine.export_to_file(path)

    def import_url_rules(self, path: str) -> tuple[int, str]:
        added, error = self._url_rule_engine.import_from_file(path)
        if added:
            self._url_rules_cache = None
        return added, error

    def _site_is_blocked(self, domain: str) -> bool:
        if not domain:
            return False
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]
        for site in self.blocked_websites():
            site = self._normalize_domain(site)
            if site and (domain == site or domain.endswith("." + site)):
                return True
        return False

    def check_url(self, url: str) -> dict:
        """Return the Focus policy decision for a full browser URL.

        This is the decision function used by the loopback extension bridge and
        by foreground enforcement. Persistent parental/productivity guard rules
        are evaluated first; Focus sub-path rules apply only while a session is
        active.
        """
        from protection.url_rules import UrlRuleEngine, domain_of

        try:
            from protection.content_guard import ContentGuard

            guard_decision = ContentGuard.instance().evaluate(url)
            if guard_decision.blocked:
                return {
                    "action": "block",
                    "reason": guard_decision.reason,
                    "rule": guard_decision.rule,
                    "domain": domain_of(url),
                    "focus_active": self._is_active,
                    "mode": self._mode,
                    "guard": guard_decision.category or "parental",
                }
        except Exception as exc:
            logger.debug("[FOCUS] Content guard check failed: %s", exc)

        if not self._is_active:
            return {
                "action": "allow",
                "reason": "Focus session inactive",
                "rule": None,
                "domain": domain_of(url),
                "focus_active": False,
                "mode": self._mode,
            }

        domain = domain_of(url)
        default_action = "block" if self._site_is_blocked(domain) else "allow"
        decision = UrlRuleEngine.decide(
            url,
            default_action=default_action,
            rules=self.url_rules(),
        )
        if decision.action == "block":
            self._record_block("site", decision.matched_rule or decision.domain)
        return {
            "action": decision.action,
            "reason": decision.reason,
            "rule": decision.matched_rule,
            "domain": decision.domain,
            "focus_active": True,
            "mode": self._mode,
            "seconds_remaining": self._seconds_remaining,
        }

    def extension_bridge_info(self) -> dict:
        try:
            from protection.extension_bridge import ExtensionBridge

            return ExtensionBridge.instance().connection_info()
        except Exception:
            return {"running": False, "port": 0, "token": "", "last_error": ""}

    def enable_extension_pairing(self, duration_s: float = 300.0) -> str:
        try:
            from protection.extension_bridge import ExtensionBridge

            return ExtensionBridge.instance().enable_pairing(duration_s=duration_s)
        except Exception:
            return ""

    def get_extension_rules(self) -> dict:
        rules_list = []
        for r in self.url_rules():
            if r.enabled:
                rules_list.append(r.to_dict())

        blocked_domains = []
        if self._is_active:
            for site in self.blocked_websites():
                norm = self._normalize_domain(site)
                if norm:
                    blocked_domains.append(norm)

        return {
            "ok": True,
            "focus_active": self._is_active,
            "mode": self._mode,
            "seconds_remaining": self._seconds_remaining,
            "session_total_seconds": self._session_total_seconds,
            "rules": rules_list,
            "blocked_domains": blocked_domains,
            "revision": getattr(self, "_rules_revision", 1),
        }

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

    def start_focus(
        self,
        minutes: int = 25,
        strict_mode: bool = False,
        mode: Optional[str] = None,
        lockout: bool = False,
        auto_started: bool = False,
        schedule_id: str = "",
    ) -> bool:
        if self._is_active:
            return False

        if mode:
            self.set_mode(mode)

        if strict_mode and not lockout and not self._pin_manager.is_enabled():
            logger.warning("[FOCUS] Cannot start strict mode: PIN is not configured.")
            return False
        if lockout and not self._pin_manager.is_enabled():
            logger.warning("[FOCUS] Cannot start lockout: a PIN is required for the safe emergency exit.")
            return False

        self._is_active = True
        self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        self._is_strict = strict_mode or lockout
        self._lockout = bool(lockout)
        self._deadline = time.monotonic() + minutes * 60
        self._seconds_remaining = minutes * 60
        self._session_total_seconds = minutes * 60
        self._focus_started_at = datetime.now()
        self._blocked_apps_counts = {}
        self._blocked_sites_counts = {}
        self._interruptions = 0
        self._block_count_last = {}
        self._auto_started = bool(auto_started)
        self._schedule_id = schedule_id or ""
        self._emergency_unlock_at = None
        try:
            self._focus_session_id = self._repo.insert_focus_session(
                mode=self._mode,
                planned_s=minutes * 60,
                started_at=self._focus_started_at,
                strict=self._is_strict,
                lockout=self._lockout,
                auto_started=self._auto_started,
                schedule_id=self._schedule_id,
            )
        except Exception as exc:
            logger.warning("[FOCUS] Could not create session record: %s", exc)
            self._focus_session_id = None
        # Only lockout needs crash/relaunch persistence; a normal session ends
        # cleanly and should not surprise the user on the next launch.
        if self._lockout:
            self._save_active_session(minutes)

        logger.info(
            f"[FOCUS] Session started. mode={self._mode}, minutes={minutes}, strict={strict_mode}, "
            f"lockout={lockout}, apps={self.current_mode_apps or '(empty)'}, "
            f"websites={self.current_mode_websites or '(none)'}"
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
        if self._lockout:
            self._spawn_lockout_watchdog()
        self.focus_state_changed.emit(True)
        return True

    def _save_active_session(self, minutes: int) -> None:
        try:
            payload = {
                "mode": self._mode,
                "minutes": minutes,
                "strict": self._is_strict,
                "lockout": self._lockout,
                "started_epoch": self._focus_started_at.timestamp() if self._focus_started_at else time.time(),
                "deadline_epoch": time.time() + minutes * 60,
                "focus_session_id": self._focus_session_id,
                "auto_started": self._auto_started,
                "schedule_id": self._schedule_id,
            }
            self._repo.set_setting("focus_active_session", json.dumps(payload))
        except Exception as exc:
            logger.warning("[FOCUS] Could not persist active session: %s", exc)

    def _clear_active_session(self) -> None:
        try:
            self._repo.set_setting("focus_active_session", "")
        except Exception:
            pass

    def _spawn_lockout_watchdog(self) -> None:
        try:
            from protection.focus_watchdog import spawn_watchdog

            self._watchdog_proc = spawn_watchdog(time.time() + max(1, self._seconds_remaining))
            if self._watchdog_proc is not None:
                logger.info("[FOCUS] Lockout watchdog started (pid=%s).", self._watchdog_proc.pid)
        except Exception as exc:
            logger.debug("[FOCUS] Watchdog unavailable: %s", exc)

    def _stop_lockout_watchdog(self) -> None:
        proc = self._watchdog_proc
        self._watchdog_proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass

    def _restore_active_session(self) -> None:
        try:
            raw = self._repo.get_setting("focus_active_session") or ""
            if not raw:
                return
            data = json.loads(raw)
        except Exception:
            self._clear_active_session()
            return

        try:
            deadline_epoch = float(data.get("deadline_epoch", 0))
        except (TypeError, ValueError):
            deadline_epoch = 0.0

        remaining = deadline_epoch - time.time()
        if remaining <= 1:
            self._clear_active_session()
            try:
                self._website_blocker.unblock_all()
            except Exception:
                pass
            return

        mode = str(data.get("mode", "custom"))
        if mode in self._mode_apps:
            self._mode = mode
        self._is_active = True
        self._is_strict = bool(data.get("strict", False))
        self._lockout = bool(data.get("lockout", False))
        self._deadline = time.monotonic() + remaining
        self._seconds_remaining = int(remaining)
        try:
            self._session_total_seconds = max(1, int(float(data.get("minutes", 25)) * 60))
        except (TypeError, ValueError):
            self._session_total_seconds = max(int(remaining), 1)
        try:
            started_epoch = float(data.get("started_epoch", time.time() - (self._session_total_seconds - remaining)))
            self._focus_started_at = datetime.fromtimestamp(started_epoch)
        except (TypeError, ValueError, OSError):
            self._focus_started_at = datetime.now()
        self._focus_session_id = data.get("focus_session_id")
        if self._focus_session_id is None or not self._repo.get_focus_session(int(self._focus_session_id)):
            try:
                self._focus_session_id = self._repo.insert_focus_session(
                    mode=self._mode,
                    planned_s=self._session_total_seconds,
                    started_at=self._focus_started_at,
                    strict=self._is_strict,
                    lockout=self._lockout,
                    auto_started=self._auto_started,
                    schedule_id=self._schedule_id,
                )
            except Exception:
                self._focus_session_id = None
        self._blocked_apps_counts = {}
        self._blocked_sites_counts = {}
        self._interruptions = 0
        self._block_count_last = {}
        self._auto_started = bool(data.get("auto_started", False))
        self._schedule_id = str(data.get("schedule_id", ""))
        self._timer.start()
        logger.info(
            "[FOCUS] Restored active session: mode=%s, remaining=%ds, lockout=%s",
            self._mode,
            self._seconds_remaining,
            self._lockout,
        )
        if self.current_mode_websites:
            try:
                self._website_blocker.block_websites(self.current_mode_websites)
            except Exception:
                pass
        if self._lockout:
            self._spawn_lockout_watchdog()

    def stop_focus(self, provided_pin: str = "") -> bool:
        if not self._is_active:
            return True

        if self._lockout and self._seconds_remaining > 0:
            if self._emergency_unlock_at is not None and time.monotonic() >= self._emergency_unlock_at:
                return self._do_stop(reason="emergency_exit")
            logger.warning("[FOCUS] Stop denied: lockout session in progress.")
            return False

        if self._is_strict and not self._lockout:
            if not self._pin_manager.verify_pin(provided_pin):
                logger.warning("[FOCUS] Stop denied: Invalid PIN.")
                return False

        return self._do_stop(reason="manual")

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
        if self._lockout and self._seconds_remaining > 0:
            if self._emergency_unlock_at is not None and time.monotonic() >= self._emergency_unlock_at:
                return self._do_stop(reason="emergency_exit")
            return False
        return self._do_stop(reason="manual")

    # ------------------------------------------------------------------
    # Safe emergency exit (hold + PIN + cooldown)
    # ------------------------------------------------------------------

    @property
    def is_emergency_pending(self) -> bool:
        return self._emergency_unlock_at is not None

    @property
    def emergency_unlock_remaining(self) -> int:
        if self._emergency_unlock_at is None:
            return 0
        return max(0, int(round(self._emergency_unlock_at - time.monotonic())))

    def request_emergency_exit(self, cooldown_minutes: int = 15) -> bool:
        """Begin the deliberate lockout exit countdown.

        The caller must already have completed the 10-second hold and PIN
        verification. The lockout remains active for the cooldown window.
        """
        if not self._is_active or not self._lockout:
            return False
        self._emergency_unlock_at = time.monotonic() + max(1, int(cooldown_minutes)) * 60
        logger.warning(
            "[FOCUS] Emergency exit requested; lockout holds for %d more minutes.",
            cooldown_minutes,
        )
        return True

    def _do_stop(self, reason: str = "manual", completed: bool = False) -> bool:
        """Internal teardown — persist the recap and reset state."""
        session_id = self._focus_session_id
        started_at = self._focus_started_at
        planned_s = self._session_total_seconds
        mode = self._mode
        blocked_apps = dict(self._blocked_apps_counts)
        blocked_sites = dict(self._blocked_sites_counts)
        interruptions = self._interruptions
        ended_at = datetime.now()
        if completed:
            actual_s = float(planned_s)
        elif started_at:
            actual_s = max(0.0, (ended_at - started_at).total_seconds())
        else:
            actual_s = float(max(0, planned_s - self._seconds_remaining))

        timeline = {
            "mode": mode,
            "reason": reason,
            "planned_s": planned_s,
            "actual_s": actual_s,
            "started_at": started_at.isoformat() if started_at else "",
            "ended_at": ended_at.isoformat(),
            "completed": bool(completed),
            "lockout": self._lockout,
            "strict": self._is_strict,
            "blocked_apps_map": blocked_apps,
            "blocked_sites_map": blocked_sites,
            "interruptions": interruptions,
        }

        recap = dict(timeline)
        if started_at:
            try:
                from analytics.engine import AnalyticsEngine

                metrics = AnalyticsEngine().get_focus_recap_metrics(
                    start=started_at,
                    end=ended_at,
                    blocked_apps=sum(blocked_apps.values()),
                    blocked_sites=sum(blocked_sites.values()),
                    interruptions=interruptions,
                )
                metrics.pop("start", None)
                metrics.pop("end", None)
                recap.update(metrics)
            except Exception as exc:
                logger.debug("[FOCUS] Recap analytics unavailable: %s", exc)

        if session_id:
            try:
                self._repo.finish_focus_session(
                    session_id=session_id,
                    actual_s=actual_s,
                    ended_at=ended_at,
                    was_completed=completed,
                    blocked_apps=sum(blocked_apps.values()),
                    blocked_sites=sum(blocked_sites.values()),
                    interruptions=interruptions,
                    blocked_apps_json=json.dumps(blocked_apps, separators=(",", ":")),
                    blocked_sites_json=json.dumps(blocked_sites, separators=(",", ":")),
                    recap_json=json.dumps(self._json_safe(recap), separators=(",", ":")),
                )
            except Exception as exc:
                logger.warning("[FOCUS] Could not persist recap: %s", exc)

        self._is_active = False
        self._rules_revision = getattr(self, "_rules_revision", 0) + 1
        self._is_strict = False
        self._lockout = False
        self._seconds_remaining = 0
        self._session_total_seconds = 0
        self._focus_session_id = None
        self._focus_started_at = None
        self._blocked_apps_counts = {}
        self._blocked_sites_counts = {}
        self._interruptions = 0
        self._block_count_last = {}
        self._emergency_unlock_at = None
        self._timer.stop()
        self._clear_active_session()
        self._stop_lockout_watchdog()
        self._website_blocker.unblock_all()
        self.focus_state_changed.emit(False)
        logger.info("[FOCUS] Session stopped (%s).", reason)
        try:
            self.session_recap_ready.emit(recap)
        except Exception:
            pass
        return True

    @staticmethod
    def _json_safe(value):
        if isinstance(value, dict):
            return {str(k): FocusManager._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [FocusManager._json_safe(v) for v in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

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

            if (
                self._lockout
                and self._emergency_unlock_at is not None
                and time.monotonic() >= self._emergency_unlock_at
            ):
                self._do_stop(reason="emergency_exit")
                return

            self.tick.emit(self._seconds_remaining)
            self._run_enforcement_scan()
        else:
            # Session completed naturally
            self._do_stop(reason="completed", completed=True)
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

                # Check browser tab website block (domain + granular URL rules)
                from tracker.browser_domain import is_browser_process, get_active_browser_domain
                if is_browser_process(p_name):
                    try:
                        title = win32gui.GetWindowText(hwnd) or ""
                    except Exception:
                        title = ""
                    domain = get_active_browser_domain(p_name, title, hwnd=hwnd)
                    if domain:
                        full_url = ""
                        try:
                            from protection.extension_bridge import ExtensionBridge
                            from protection.url_rules import domain_of

                            candidate = ExtensionBridge.instance().latest_url(p_name, max_age_s=12.0)
                            if candidate and domain_of(candidate) == domain:
                                full_url = candidate
                        except Exception:
                            full_url = ""
                        decision = self.check_url(full_url or f"https://{domain}/")
                        if decision.get("action") == "block":
                            from protection.process import ProcessController
                            ProcessController.close_browser_tab(hwnd)
                            now = time.time()
                            key = decision.get("rule") or domain
                            self._record_block("site", str(key))
                            last_time = self._last_blocked_feedback.get(key, 0.0)
                            if now - last_time >= 4.0:
                                self._last_blocked_feedback[key] = now
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

    def _record_block(self, kind: str, target: str) -> None:
        if not self._is_active or not target:
            return
        key = f"{kind}:{target.lower()}"
        now = time.time()
        if now - self._block_count_last.get(key, 0.0) < 5.0:
            return
        self._block_count_last[key] = now
        self._interruptions += 1
        if kind == "app":
            self._blocked_apps_counts[target.lower()] = self._blocked_apps_counts.get(target.lower(), 0) + 1
        else:
            self._blocked_sites_counts[target.lower()] = self._blocked_sites_counts.get(target.lower(), 0) + 1

    def _handle_blocked_app(self, proc, p_name: str) -> None:
        try:
            if self._app_block_response == "close":
                logger.info(f"[FOCUS] Terminating restricted app {p_name}.")
                proc.kill()
            else:
                logger.debug(f"[FOCUS] Restricted app in foreground: {p_name}")

            self._record_block("app", p_name)
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
