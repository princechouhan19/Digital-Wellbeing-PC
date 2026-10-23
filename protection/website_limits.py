from __future__ import annotations
import json
import threading
from typing import Dict, Optional
from database.repository import Repository
from core.logger import logger

class WebsiteLimitManager:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        # Format: { browser_process: { domain: rule_dict } }
        self._limits: Dict[str, Dict[str, dict]] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            data = self._repo.get_setting("website_limits") or "{}"
            try:
                self._limits = json.loads(data)
            except json.JSONDecodeError:
                logger.error("Failed to parse website_limits from DB")
                self._limits = {}

    def _save(self) -> None:
        try:
            data = json.dumps(self._limits)
            self._repo.set_setting("website_limits", data)
        except Exception as e:
            logger.error(f"Failed to save website_limits: {e}")

    @staticmethod
    def normalize_domain(domain: str) -> str:
        d = (domain or "").strip().lower()
        if d.startswith("http://"):
            d = d[7:]
        elif d.startswith("https://"):
            d = d[8:]
        d = d.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        if d.startswith("www."):
            d = d[4:]
        return d.strip(". ")

    def set_limit_rule(self, browser_process: str, domain: str, rule: Optional[dict]) -> None:
        """Set a limit rule for a website. Use None to remove."""
        browser_process = browser_process.lower() if browser_process else "*"
        domain = self.normalize_domain(domain)
        if not domain:
            return
        
        with self._lock:
            if not rule or rule.get("limit_seconds") is None or rule.get("limit_seconds") <= 0:
                if browser_process == "*":
                    for bp in list(self._limits.keys()):
                        self._limits[bp].pop(domain, None)
                        self._limits[bp].pop(f"www.{domain}", None)
                else:
                    if browser_process in self._limits:
                        self._limits[browser_process].pop(domain, None)
                        self._limits[browser_process].pop(f"www.{domain}", None)
            else:
                if browser_process not in self._limits:
                    self._limits[browser_process] = {}
                self._limits[browser_process][domain] = rule
                
            self._save()
            logger.info(f"Set website limit rule for {browser_process} -> {domain}: {rule}")

    def remove_website_limit(self, domain: str, browser_process: Optional[str] = None) -> None:
        """Removes a website limit across specified browser or all browsers if None."""
        domain = self.normalize_domain(domain)
        if not domain:
            return
        with self._lock:
            if browser_process and browser_process != "*":
                bp = browser_process.lower()
                if bp in self._limits:
                    self._limits[bp].pop(domain, None)
                    self._limits[bp].pop(f"www.{domain}", None)
            else:
                for bp in list(self._limits.keys()):
                    self._limits[bp].pop(domain, None)
                    self._limits[bp].pop(f"www.{domain}", None)
            self._save()
            logger.info(f"Removed website limit for domain: {domain}")

    def get_browser_for_domain(self, domain: str) -> Optional[str]:
        """Returns the browser_process key that holds the limit for this domain, or None."""
        domain = self.normalize_domain(domain)
        if not domain:
            return None
        with self._lock:
            # Check specific browsers first
            for bp, dom_map in self._limits.items():
                if bp != "*" and (domain in dom_map or f"www.{domain}" in dom_map):
                    return bp
            # Check wildcard
            if "*" in self._limits:
                dom_map = self._limits["*"]
                if domain in dom_map or f"www.{domain}" in dom_map:
                    return "*"
        return None

    def get_limit_rule(self, browser_process: Optional[str], domain: str) -> Optional[dict]:
        """Return the rule dict for a domain if found."""
        bp = browser_process.lower() if browser_process else "*"
        domain = self.normalize_domain(domain)
        if not domain:
            return None

        with self._lock:
            # 1. Check specified browser (if not "*")
            if bp != "*":
                browser_limits = self._limits.get(bp, {})
                rule = browser_limits.get(domain) or browser_limits.get(f"www.{domain}")
                if rule:
                    return rule

            # 2. Check global wildcard '*'
            wildcard_limits = self._limits.get("*", {})
            rule = wildcard_limits.get(domain) or wildcard_limits.get(f"www.{domain}")
            if rule:
                return rule

            # 3. If caller asked for "*" (generic/unspecified browser query),
            # check any other configured browser so generic UI queries find the rule.
            if bp == "*":
                for other_bp, dom_map in self._limits.items():
                    if other_bp != "*":
                        rule = dom_map.get(domain) or dom_map.get(f"www.{domain}")
                        if rule:
                            return rule

        return None

    def get_limit(self, browser_process: str, domain: str) -> Optional[int]:
        """Return the limit in seconds IF active today, else None."""
        rule = self.get_limit_rule(browser_process, domain)
        if not rule:
            return None
        
        # Check repeat days
        import datetime
        today = datetime.datetime.today().weekday()
        if today not in rule.get("repeat_days", [0, 1, 2, 3, 4, 5, 6]):
            return None
            
        return rule.get("limit_seconds")

    def get_all_limits(self, browser_process: Optional[str] = None) -> Dict[str, dict]:
        """Return limits for a specific browser, or all unique website limits if browser_process is None."""
        with self._lock:
            if browser_process is not None:
                return self._limits.get(browser_process.lower(), {}).copy()
            combined: Dict[str, dict] = {}
            for bp, dom_map in self._limits.items():
                for dom, rule in dom_map.items():
                    if dom not in combined:
                        combined[dom] = rule
            return combined
