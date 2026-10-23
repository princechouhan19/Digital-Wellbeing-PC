"""
content_blocker.py — "SafeBrowse" adult content filter for Digital Wellbeing.

A local-first, open-source content filter that blocks adult websites at the
system level by writing a managed section into the Windows hosts file.

How it works
------------
1.  Domains are pulled from open-source blocklists (MIT-licensed
    StevenBlack hosts variants, or any user-supplied list URL). Downloaded
    lists are parsed, de-duplicated, and cached in AppData so blocking works
    fully offline after the first sync.
2.  A curated offline seed list ships with the app so filtering is active
    immediately, even before the first successful sync.
3.  The domain set is written as one `0.0.0.0 domain` mapping per line into
    a dedicated hosts section ("# DW-SAFEBROWSE START/END"), which coexists
    safely with Focus Mode's separate section.
4.  Hosts modification requires administrator rights. The app tries a direct
    write first; if the process is not elevated it relaunches itself once as
    a single-action UAC elevated helper (utils/elevation.py).

Privacy: no network request carries any user data. The only outbound call is
an anonymous HTTPS GET of a public blocklist file.
"""
from __future__ import annotations

import os
import re
import shutil
import threading
import time
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from core.logger import logger
from protection.hosts_sections import HOSTS_LOCK, CONTENT_HEADER, CONTENT_FOOTER

HOSTS_PATH_DEFAULT = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"

APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "DigitalWellbeing"
BLOCKLIST_DIR = APP_DATA_DIR / "blocklist"
CACHED_DOMAINS_FILE = BLOCKLIST_DIR / "adult_domains.txt"

# Open-source blocklist sources (StevenBlack/hosts — MIT License)
SOURCES: Dict[str, Dict] = {
    "sb_porn": {
        "label": "StevenBlack — Adult (recommended)",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts",
        "note": "Curated adult-sites list, updated weekly by the community",
    },
    "sb_gambling_porn": {
        "label": "StevenBlack — Adult + Gambling",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/gambling-porn/hosts",
        "note": "Adult sites plus gambling and betting domains",
    },
    "sb_fakenews_gambling_porn": {
        "label": "StevenBlack — Strict (adult + gambling + fake news)",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-gambling-porn/hosts",
        "note": "Widest coverage of the StevenBlack unified variants",
    },
    "custom": {
        "label": "Custom list URL",
        "url": None,  # resolved from settings (content_filter_custom_url)
        "note": "Any hosts-format list served over HTTPS",
    },
}

DEFAULT_SOURCE = "sb_porn"
SYNC_INTERVAL_S = 7 * 24 * 3600.0      # weekly auto-refresh
DOWNLOAD_TIMEOUT_S = 30.0

_HOSTS_LINE_RE = re.compile(r"^(?:0\.0\.0\.0|127\.0\.0\.1|::1|::)\s+(\S+)")
_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
_LOCAL_HOSTS = {"localhost", "localhost.localdomain", "local", "broadcasthost", "ip6-localhost", "ip6-loopback"}

# ---------------------------------------------------------------------------
# Curated offline seed (top adult domains, from open community blocklists).
# Provides immediate protection before the first list sync.
# ---------------------------------------------------------------------------
SEED_DOMAINS = {
    "pornhub.com", "www.pornhub.com", "xvideos.com", "www.xvideos.com",
    "xnxx.com", "www.xnxx.com", "xhamster.com", "www.xhamster.com",
    "redtube.com", "www.redtube.com", "youporn.com", "www.youporn.com",
    "tube8.com", "www.tube8.com", "spankbang.com", "www.spankbang.com",
    "hqporner.com", "www.hqporner.com", "porn.com", "www.porn.com",
    "4chan.org", "www.4chan.org", "8kun.top", "motherless.com",
    "www.motherless.com", "pornone.com", "eporner.com", "www.eporner.com",
    "txxx.com", "www.txxx.com", "upornia.com", "hclips.com",
    "porn300.com", "fapdex.com", "beeg.com", "www.beeg.com",
    "tnaflix.com", "www.tnaflix.com", "empflix.com", "movie4k.org",
    "adultsite.com", "camsoda.com", "chaturbate.com", "www.chaturbate.com",
    "stripchat.com", "www.stripchat.com", "bongacams.com", "cam4.com",
    "myfreecams.com", "livejasmin.com", "www.livejasmin.com", "flirt4free.com",
    "onlyfans.com", "www.onlyfans.com", "fansly.com", "www.fansly.com",
    "brazzers.com", "www.brazzers.com", "naughtyamerica.com",
    "adultfriendfinder.com", "www.adultfriendfinder.com", "ashleymadison.com",
    "f95zone.to", "www.f95zone.to", "thehun.net", "tnthits.com",
    "watchxxxx.com", "hitomi.la", "nhentai.net", "www.nhentai.net",
    "e-hentai.org", "exhentai.org", "hentaihaven.com", "hanime.tv",
    "www.hanime.tv", "rule34video.com", "www.rule34video.com", "rule34.xxx",
    "luscious.net", "incognitymous.com", "8muses.com", "comics.xxx",
    "megapornfree.com", "tubesafari.com", "www.tubesafari.com",
    "pornsos.com", "yespornplease.com", "xozilla.com", "pix-route.com",
    "sex.com", "www.sex.com", "xtapes.co", "javmost.com", "jav.guru",
    "missav.com", "www.missav.com", "iwara.to", "coomer.party",
    "kemono.party", "sinparty.com", "nsfwmonster.com", "leaktape.com",
}


def _now() -> float:
    return time.time()


class ContentBlocker:
    """Singleton engine managing the SafeBrowse content filter."""

    _instance = None

    @classmethod
    def instance(cls) -> "ContentBlocker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, hosts_path: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._hosts_path = hosts_path or HOSTS_PATH_DEFAULT
        self._backup_path = self._hosts_path.with_name("hosts.dw.bak")
        self._settings = None          # lazy — avoids import cycles at module load
        self._syncing = False
        self._sync_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Settings access (lazy)
    # ------------------------------------------------------------------

    def _sm(self):
        if self._settings is None:
            from settings.manager import SettingsManager
            self._settings = SettingsManager()
        return self._settings

    # ------------------------------------------------------------------
    # Public status API
    # ------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        return self._sm().get_bool("content_filter_enabled", False)

    @property
    def source_key(self) -> str:
        key = self._sm().get("content_filter_source", DEFAULT_SOURCE)
        return key if key in SOURCES else DEFAULT_SOURCE

    def status(self) -> dict:
        """Snapshot for the Settings UI and Onboarding."""
        enabled = self.is_enabled
        count = self.cached_domain_count()
        last_sync = self.last_sync_ts()
        section_active = False
        try:
            if self._hosts_path.exists():
                content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
                section_active = CONTENT_HEADER in content
        except Exception:
            pass
        return {
            "enabled": enabled,
            "section_active": section_active,
            "domain_count": count,
            "last_sync": last_sync,
            "source": self.source_key,
            "source_label": SOURCES[self.source_key]["label"],
            "has_cache": CACHED_DOMAINS_FILE.exists(),
        }

    def cached_domain_count(self) -> int:
        try:
            if not CACHED_DOMAINS_FILE.exists():
                return 0
            with open(CACHED_DOMAINS_FILE, "r", encoding="utf-8", errors="replace") as f:
                return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def last_sync_ts(self) -> float:
        try:
            return float(self._sm().get("content_filter_last_sync", "0") or 0)
        except Exception:
            return 0.0

    def sync_is_stale(self) -> bool:
        return (_now() - self.last_sync_ts()) > SYNC_INTERVAL_S

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def enable(self, apply_now: bool = True) -> Tuple[bool, str]:
        """Enable the filter: persists the setting and applies the hosts block."""
        self._sm().set("content_filter_enabled", True)

        if not apply_now:
            return True, "SafeBrowse will activate on next launch"

        # Guarantee a usable list (seed at minimum)
        if self.cached_domain_count() == 0:
            self._write_cache(SEED_DOMAINS)

        ok, msg = self._apply_hosts_block()
        if ok:
            self._schedule_sync_if_stale()   # refresh to the full list in background
        return ok, msg

    def disable(self) -> Tuple[bool, str]:
        """Disable the filter: persists the setting and removes the hosts block."""
        self._sm().set("content_filter_enabled", False)
        return self._remove_hosts_block()

    # ------------------------------------------------------------------
    # Blocklist sync (open-source lists)
    # ------------------------------------------------------------------

    def sync_now(self, callback: Optional[Callable[[bool, str], None]] = None) -> threading.Thread:
        """Download the active list in a background thread and re-apply if enabled."""
        if self._syncing:
            if callback:
                callback(False, "A sync is already running")
            return self._sync_thread
        self._syncing = True

        def worker():
            try:
                ok, msg = self._download_and_cache()
                if ok and self.is_enabled:
                    ok2, msg2 = self._apply_hosts_block()
                    msg = f"{msg} — {msg2}" if ok else msg
                    ok = ok2
                elif ok:
                    msg = f"{msg} — filter is disabled, list cached"
            except Exception as exc:
                logger.warning(f"[SAFEBROWSE] Sync error: {exc}")
                ok, msg = False, f"Sync failed: {exc}"
            finally:
                self._syncing = False
            if callback:
                try:
                    callback(ok, msg)
                except Exception:
                    pass

        self._sync_thread = threading.Thread(target=worker, daemon=True, name="DW-SafeBrowse-Sync")
        self._sync_thread.start()
        return self._sync_thread

    def _schedule_sync_if_stale(self) -> None:
        """Fire-and-forget weekly refresh; called on enable and app start."""
        if self._syncing or not self.sync_is_stale():
            return
        self.sync_now(callback=lambda ok, msg: logger.info(f"[SAFEBROWSE] Auto-sync: {msg}"))

    def maybe_auto_sync_on_startup(self) -> None:
        """Called once from the app shell when the filter is enabled."""
        if self.is_enabled:
            self._schedule_sync_if_stale()

    def _resolve_source_url(self) -> Optional[str]:
        if self.source_key == "custom":
            url = (self._sm().get("content_filter_custom_url", "") or "").strip()
            return url or None
        return SOURCES[self.source_key]["url"]

    def _download_and_cache(self) -> Tuple[bool, str]:
        url = self._resolve_source_url()
        if not url:
            return False, "No custom list URL configured"
        if not url.lower().startswith(("https://", "http://")):
            return False, "List URL must start with https://"

        logger.info(f"[SAFEBROWSE] Downloading blocklist: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "DigitalWellbeing/4.1 SafeBrowse"})
        try:
            with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_S) as resp:
                raw = resp.read(20 * 1024 * 1024).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning(f"[SAFEBROWSE] Download failed: {exc}")
            return False, f"Download failed — check your connection ({exc.__class__.__name__})"

        domains = self.parse_hosts_payload(raw)
        if len(domains) < 100:
            return False, "Downloaded list looks empty or malformed"

        self._write_cache(domains)
        self._sm().set("content_filter_last_sync", str(_now()))
        logger.info(f"[SAFEBROWSE] Cached {len(domains)} domains from {url}")
        return True, f"Updated — {len(domains):,} domains"

    @staticmethod
    def parse_hosts_payload(raw: str) -> set:
        """Extract clean domains from any hosts-format payload."""
        domains = set()
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _HOSTS_LINE_RE.match(line)
            if not m:
                continue
            d = m.group(1).lower().strip(".")
            if d in _LOCAL_HOSTS or not _DOMAIN_RE.match(d):
                continue
            domains.add(d)
        return domains

    def _write_cache(self, domains: set) -> None:
        try:
            BLOCKLIST_DIR.mkdir(parents=True, exist_ok=True)
            tmp = CACHED_DOMAINS_FILE.with_suffix(".tmp")
            tmp.write_text("\n".join(sorted(domains)) + "\n", encoding="utf-8")
            tmp.replace(CACHED_DOMAINS_FILE)
        except Exception as exc:
            logger.warning(f"[SAFEBROWSE] Could not write cache: {exc}")

    def _load_domains(self) -> set:
        try:
            if CACHED_DOMAINS_FILE.exists():
                text = CACHED_DOMAINS_FILE.read_text(encoding="utf-8", errors="replace")
                return {d for d in (ln.strip().lower() for ln in text.splitlines()) if d}
        except Exception as exc:
            logger.warning(f"[SAFEBROWSE] Cache read failed: {exc}")
        return set(SEED_DOMAINS)

    # ------------------------------------------------------------------
    # Hosts application
    # ------------------------------------------------------------------

    def _is_admin(self) -> bool:
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _apply_hosts_block(self) -> Tuple[bool, str]:
        """Write the managed section, elevating once via UAC when required."""
        if self._is_admin():
            return self.apply_hosts_block_elevated()

        from utils.elevation import run_elevated
        ok, msg = run_elevated("content-apply")
        if not ok and ("cancel" in msg.lower() or "timed out" in msg.lower()):
            return False, "Administrator approval is required to enable SafeBrowse"
        return ok, msg

    def _remove_hosts_block(self) -> Tuple[bool, str]:
        if self._is_admin():
            return self.remove_hosts_block_elevated()

        from utils.elevation import run_elevated
        ok, msg = run_elevated("content-remove")
        if not ok and ("cancel" in msg.lower() or "timed out" in msg.lower()):
            return False, "Administrator approval is required to update SafeBrowse"
        return ok, msg

    def apply_hosts_block_elevated(self) -> Tuple[bool, str]:
        """Direct hosts write. Runs only inside an elevated helper or admin session."""
        domains = self._load_domains()
        if not domains:
            domains = set(SEED_DOMAINS)

        with HOSTS_LOCK:
            try:
                if not self._hosts_path.exists():
                    existing = ""
                else:
                    existing = self._hosts_path.read_text(encoding="utf-8", errors="replace")
            except (PermissionError, OSError) as exc:
                return False, "Administrator privileges required to modify the hosts file"

            cleaned = self._strip_section(existing).rstrip()
            lines = [CONTENT_HEADER, "# Managed by Digital Wellbeing SafeBrowse"]
            for d in sorted(domains):
                lines.append(f"0.0.0.0 {d}")
            lines.append(CONTENT_FOOTER)
            new_content = cleaned + "\n" + "\n".join(lines) + "\n"

            try:
                if self._hosts_path.exists() and not self._backup_path.exists():
                    try:
                        shutil.copy2(self._hosts_path, self._backup_path)
                    except Exception:
                        pass
                self._hosts_path.write_text(new_content, encoding="utf-8")
            except (PermissionError, OSError):
                return False, "Administrator privileges required to modify the hosts file"
            except Exception as exc:
                return False, str(exc)

        self._flush_dns()
        logger.info(f"[SAFEBROWSE] Hosts block applied: {len(domains)} domains")
        return True, f"SafeBrowse active — {len(domains):,} domains blocked"

    def remove_hosts_block_elevated(self) -> Tuple[bool, str]:
        """Remove the managed section. Runs only inside an elevated helper or admin session."""
        with HOSTS_LOCK:
            try:
                if not self._hosts_path.exists():
                    return True, "Hosts file does not exist"
                content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
                if CONTENT_HEADER not in content:
                    return True, "SafeBrowse block not present"
                cleaned = self._strip_section(content)
                self._hosts_path.write_text(cleaned, encoding="utf-8")
            except (PermissionError, OSError):
                return False, "Administrator privileges required to modify the hosts file"
            except Exception as exc:
                return False, str(exc)

        self._flush_dns()
        logger.info("[SAFEBROWSE] Hosts block removed")
        return True, "SafeBrowse is off"

    @staticmethod
    def _strip_section(content: str) -> str:
        """Remove only the SafeBrowse section, preserving everything else."""
        pat = re.compile(
            rf"\n?{re.escape(CONTENT_HEADER)}.*?{re.escape(CONTENT_FOOTER)}\n?",
            re.DOTALL,
        )
        return pat.sub("\n", content)

    @staticmethod
    def _flush_dns() -> bool:
        try:
            from protection.website_blocker import WebsiteBlocker
            return WebsiteBlocker.flush_dns()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Crash recovery
    # ------------------------------------------------------------------

    def cleanup_orphaned_block(self) -> bool:
        """Remove the hosts section when the filter is disabled (e.g. after a crash)."""
        try:
            if not self.is_enabled and self._hosts_path.exists():
                content = self._hosts_path.read_text(encoding="utf-8", errors="replace")
                if CONTENT_HEADER in content and self._is_admin():
                    self.remove_hosts_block_elevated()
                    return True
        except Exception as exc:
            logger.debug(f"[SAFEBROWSE] Orphan cleanup error: {exc}")
        return False
