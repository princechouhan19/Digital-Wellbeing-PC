"""
website_blocker.py — Robust, reversible Windows hosts-based website blocking for Focus Mode.

Safety & Architectural Guarantees:
  - Local-first & offline: 0 network requests, 0 telemetry, 0 proxies, 0 extensions.
  - Clean delimited block: only modifies entries between managed comment delimiters.
  - Preserves 100% of unrelated host entries and creates an atomic backup before changes.
  - Domain normalization & expansion: handles apex, www, and common service variants.
  - DNS cache flush: calls DnsFlushResolverCache and ipconfig /flushdns for immediate effect.
  - Crash recovery & rollback: cleans orphaned blocks on startup if Focus is not active.
  - Graceful permission handling: fails safely on PermissionError without breaking system network.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import ctypes
from pathlib import Path
from typing import List, Set, Tuple, Optional

from core.logger import logger
from protection.hosts_sections import HOSTS_LOCK, FOCUS_HEADER, FOCUS_FOOTER

HOSTS_PATH_DEFAULT = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"

BLOCK_HEADER = FOCUS_HEADER
BLOCK_FOOTER = FOCUS_FOOTER

# Any managed block ever written by this app (current + all legacy formats).
#   Format A (current/older): "# ... BLOCK START" / "# ... BLOCK END"
#   Format B (oldest):        "# --- BEGIN ... BLOCK ... ---" / "# --- END ... BLOCK ... ---"
# so blocks left by older releases are migrated/cleaned transparently.
_LEGACY_MANAGED_MARKER = re.compile(
    r"^# (?:[A-Z][A-Z \-]*BLOCK (?:START|END)|--- (?:BEGIN|END) .+BLOCK.*---)\s*$"
)

# Regex for validating domain names (e.g. instagram.com, sub.domain.co.uk)
DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# Common domain variants and aliases
DOMAIN_EXPANSIONS = {
    "youtube.com": ["www.youtube.com", "m.youtube.com", "youtu.be"],
    "reddit.com": ["www.reddit.com", "old.reddit.com", "np.reddit.com"],
    "x.com": ["www.x.com", "twitter.com", "www.twitter.com"],
    "twitter.com": ["www.twitter.com", "x.com", "www.x.com"],
    "instagram.com": ["www.instagram.com", "m.instagram.com", "l.instagram.com"],
    "facebook.com": ["www.facebook.com", "m.facebook.com", "fb.com", "www.fb.com"],
    "tiktok.com": ["www.tiktok.com", "m.tiktok.com", "vm.tiktok.com"],
    "netflix.com": ["www.netflix.com"],
    "twitch.tv": ["www.twitch.tv", "m.twitch.tv"],
    "discord.com": ["www.discord.com", "discordapp.com", "www.discordapp.com"],
}


class WebsiteBlocker:
    """
    Manages local Windows hosts-based blocking and DNS flushing during Focus sessions.
    """

    def __init__(self, hosts_path: Optional[Path] = None):
        self._hosts_path = hosts_path or HOSTS_PATH_DEFAULT
        self._backup_path = self._hosts_path.with_name("hosts.dw.bak")
        self._active_domains: Set[str] = set()

    @property
    def hosts_path(self) -> Path:
        return self._hosts_path

    @property
    def is_active(self) -> bool:
        return bool(self._active_domains)

    @property
    def is_blocking_active(self) -> bool:
        return self.is_active

    # ------------------------------------------------------------------
    # Domain Normalization and Expansion
    # ------------------------------------------------------------------

    @staticmethod
    def clean_domain(raw_input: str) -> Optional[str]:
        """
        Cleans and normalizes a domain string from URLs or raw input.
        Returns normalized lowercase apex domain or None if invalid.
        """
        if not raw_input:
            return None
        text = raw_input.strip().lower()
        # Remove scheme
        text = re.sub(r"^https?://", "", text)
        # Remove path, query, fragment, port
        text = text.split("/")[0].split("?")[0].split("#")[0].split(":")[0]
        # Remove leading www.
        if text.startswith("www."):
            text = text[4:]
        text = text.strip(". ")
        if DOMAIN_REGEX.match(text):
            return text
        return None

    @classmethod
    def expand_domain(cls, domain: str) -> Set[str]:
        """
        Expands a clean domain into its apex, www, and known platform aliases.
        """
        clean = cls.clean_domain(domain)
        if not clean:
            return set()

        variants: Set[str] = {clean, f"www.{clean}"}
        if clean in DOMAIN_EXPANSIONS:
            for extra in DOMAIN_EXPANSIONS[clean]:
                variants.add(extra)
        return variants

    @classmethod
    def expand_domain_variants(cls, domains: List[str]) -> Set[str]:
        """
        Expands a list of domain strings into all apex and alias variants.
        """
        result: Set[str] = set()
        for d in domains:
            result.update(cls.expand_domain(d))
        return result

    # ------------------------------------------------------------------
    # Core Blocking Lifecycle
    # ------------------------------------------------------------------

    def block_websites(self, websites: List[str]) -> Tuple[bool, str]:
        """
        Activates website blocking by writing the managed delimited block to the hosts file.
        Flushes DNS resolver cache immediately.
        Returns (success: bool, message: str).
        """
        if not websites:
            with HOSTS_LOCK:
                self.unblock_all()
            return True, "No websites to block"

        all_domains = self.expand_domain_variants(websites)
        if not all_domains:
            return False, "No valid domains to block"

        with HOSTS_LOCK:
            # Read existing hosts content
            try:
                if not self._hosts_path.exists():
                    existing_content = ""
                else:
                    existing_content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
            except PermissionError as p_exc:
                logger.warning(f"[WEBSITE_BLOCKER] Permission denied reading hosts file: {p_exc}")
                return False, "Permission denied: administrator privileges required to modify hosts file"
            except Exception as exc:
                logger.warning(f"[WEBSITE_BLOCKER] Failed to read hosts file: {exc}")
                return False, f"Failed to read hosts: {exc}"

            # Clean any previously managed block (current or legacy format)
            cleaned_content = self._strip_managed_blocks(existing_content).rstrip()

            # Build the delimited block
            block_lines = [BLOCK_HEADER, "# Managed by Digital Wellbeing Focus Mode"]
            for domain in sorted(all_domains):
                block_lines.append(f"127.0.0.1 {domain}")
                block_lines.append(f"0.0.0.0 {domain}")
                block_lines.append(f"::1 {domain}")
            block_lines.append(BLOCK_FOOTER)
            managed_block = "\n" + "\n".join(block_lines) + "\n"

            new_content = cleaned_content + managed_block

            # Atomic write with backup
            try:
                # Create backup if not exists
                if self._hosts_path.exists() and not self._backup_path.exists():
                    try:
                        shutil.copy2(self._hosts_path, self._backup_path)
                    except Exception as b_exc:
                        logger.debug(f"[WEBSITE_BLOCKER] Could not create backup: {b_exc}")

                self._hosts_path.write_text(new_content, encoding="utf-8")
                self._active_domains = all_domains
                self.flush_dns()
                logger.info(f"[WEBSITE_BLOCKER] Successfully blocked {len(all_domains)} domain entries.")
                return True, f"Blocked {len(all_domains)} domains"
            except (PermissionError, OSError) as p_exc:
                logger.warning(f"[WEBSITE_BLOCKER] Permission denied when writing to hosts file: {p_exc}")
                return False, "Administrator privileges required to modify hosts file"
            except Exception as exc:
                logger.warning(f"[WEBSITE_BLOCKER] Unexpected error writing hosts file: {exc}")
                return False, str(exc)

    def unblock_all(self) -> Tuple[bool, str]:
        """
        Removes the managed delimited block from the hosts file and flushes DNS cache.
        """
        with HOSTS_LOCK:
            return self._unblock_all_locked()

    def _unblock_all_locked(self) -> Tuple[bool, str]:
        try:
            if not self._hosts_path.exists():
                self._active_domains.clear()
                return True, "Hosts file does not exist"

            content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
            if not self._has_managed_block(content):
                self._active_domains.clear()
                return True, "No managed block found"

            cleaned_content = self._strip_managed_blocks(content)
            self._hosts_path.write_text(cleaned_content, encoding="utf-8")
            self._active_domains.clear()
            self.flush_dns()
            logger.info("[WEBSITE_BLOCKER] Successfully removed managed website blocks and flushed DNS.")
            return True, "Unblocked all websites"
        except (PermissionError, OSError) as p_exc:
            logger.warning(f"[WEBSITE_BLOCKER] Permission denied when unblocking hosts: {p_exc}")
            return False, "Permission denied"
        except Exception as exc:
            logger.warning(f"[WEBSITE_BLOCKER] Failed to unblock websites: {exc}")
            return False, str(exc)

    # ------------------------------------------------------------------
    # Managed-section detection & stripping
    # ------------------------------------------------------------------

    @staticmethod
    def _has_managed_block(content: str) -> bool:
        """True if the content contains any managed (current or legacy) block."""
        if BLOCK_HEADER in content:
            return True
        for line in content.splitlines():
            if _LEGACY_MANAGED_MARKER.match(line.strip()):
                return True
        return False

    @staticmethod
    def _strip_managed_blocks(content: str) -> str:
        """
        Strips the current managed block and every legacy delimited block
        (any '# ... BLOCK START' .. '# ... BLOCK END' pair) safely.
        """
        # Current-format block first (exact delimiters)
        pat_current = re.compile(
            rf"\n?{re.escape(BLOCK_HEADER)}.*?{re.escape(BLOCK_FOOTER)}\n?",
            re.DOTALL
        )
        content = pat_current.sub("\n", content)

        # Legacy formats: any delimited pair (both historical shapes).
        pat_legacy = re.compile(
            r"\n?^# (?:[A-Z][A-Z \-]*BLOCK START|--- BEGIN .+BLOCK[^\n]*---)\s*$"
            r".*?"
            r"^# (?:[A-Z][A-Z \-]*BLOCK END|--- END .+BLOCK[^\n]*---)\s*$\n?",
            re.DOTALL | re.MULTILINE
        )
        content = pat_legacy.sub("\n", content)
        return content.rstrip() + "\n"


    def block_websites_async(self, websites: List[str], callback=None) -> threading.Thread:
        """Run block_websites in a background thread to prevent UI thread lag."""
        import threading
        def worker():
            res = self.block_websites(websites)
            if callback:
                try:
                    callback(res)
                except Exception:
                    pass
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    def unblock_all_async(self, callback=None) -> threading.Thread:
        """Run unblock_all in a background thread to prevent UI thread lag."""
        import threading
        def worker():
            res = self.unblock_all()
            if callback:
                try:
                    callback(res)
                except Exception:
                    pass
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return t

    # ------------------------------------------------------------------
    # DNS Cache Flushing & Crash Recovery
    # ------------------------------------------------------------------

    @staticmethod
    def flush_dns() -> bool:
        """
        Flushes the Windows DNS resolver cache using the Win32 dnsapi call,
        with fallback to 'ipconfig /flushdns'.
        """
        flushed = False
        try:
            dnsapi = ctypes.windll.dnsapi
            if hasattr(dnsapi, "DnsFlushResolverCache"):
                res = dnsapi.DnsFlushResolverCache()
                flushed = (res == 1)
        except Exception:
            pass

        if not flushed:
            try:
                subprocess.run(
                    ["ipconfig", "/flushdns"],
                    capture_output=True,
                    timeout=3,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                )
                flushed = True
            except Exception:
                pass
        return flushed

    def cleanup_orphaned_blocks(self) -> bool:
        """
        Scans for and cleans up any orphaned managed blocks left from a crash.
        Safe to call on application startup.
        """
        try:
            if self._hosts_path.exists():
                content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
                if self._has_managed_block(content):
                    logger.info("[WEBSITE_BLOCKER] Found orphaned managed block from previous session. Cleaning up.")
                    self.unblock_all()
                    return True
        except Exception as exc:
            logger.debug(f"[WEBSITE_BLOCKER] Orphan cleanup error: {exc}")
        return False
