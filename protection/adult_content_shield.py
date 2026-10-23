"""
adult_content_shield.py — Real-time Adult Search & Content Protection Engine.

Detects adult search queries on major search engines (Google, Bing, Brave,
DuckDuckGo, Yahoo, etc.) and explicit browsing in real-time.
When detected:
1. Closes the offending browser tab or navigates away.
2. Triggers an Apple-styled motivational intervention popup to build self-control.
"""
from __future__ import annotations

import ctypes
import re
import threading
import time
import urllib.parse
from functools import lru_cache
from typing import Callable, Optional, Set, Tuple

from core.logger import logger
from tracker.foreground import BROWSER_PROCESSES


# ---------------------------------------------------------------------------
# Search Engine Window Title Patterns
# ---------------------------------------------------------------------------
_SEARCH_TITLE_PATTERNS = [
    re.compile(r"^(.*?)\s+[-–—]\s+Google\s+Search", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Bing(?:\s+Search)?", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Brave\s+Search", re.IGNORECASE),
    re.compile(r"^(.*?)\s+at\s+DuckDuckGo", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Yahoo\s+Search", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Ecosia", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Yandex", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Startpage", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+Qwant", re.IGNORECASE),
    re.compile(r"^(.*?)\s+[-–—]\s+YouTube", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# High-Confidence Adult Keywords & RegEx
# ---------------------------------------------------------------------------
_EXPLICIT_KEYWORDS = frozenset({
    "porn", "porno", "pornography", "xxx", "nude", "nudes", "nudity",
    "hentai", "erotic", "erotica", "nsfw", "camgirl", "camgirls",
    "camsoda", "chaturbate", "onlyfans", "fansly", "boobs", "milf",
    "dildo", "masturbat", "masturbation", "ejaculat", "ejaculation",
    "blowjob", "handjob", "creampie", "hardcore", "softcore", "gangbang",
    "deepthroat", "threesome", "fetish", "bdsm", "incest", "rule34",
    "jav", "redtube", "xvideos", "xnxx", "xhamster", "spankbang",
    "eporner", "youporn", "brazzers", "stripchat", "fap", "fapping",
    "shemale", "pussy", "bukkake", "voyeur", "voyeurism", "orgasm",
    "naked girls", "naked women", "sexy girls nude", "adult videos",
    "adult movies", "adult games", "hot sex", "free sex", "sex video",
    "sex clips", "sex tape", "sex tube", "sex pics", "leaked nudes",
    "nude leaks", "onlyfans leaks", "nsfw leaks", "uncensored hentai",
})

_ADULT_TLDS = frozenset({
    "porn", "xxx", "adult", "sex", "sexy", "cam", "tube"
})

_SAFE_CONTEXT_EXCLUSIONS = frozenset({
    "sussex", "essex", "middlesex", "sexual education", "sex education",
    "sexual health", "therapist", "aromatherapy", "secular", "insect",
    "insecticide", "dextrose", "gender", "heterosexual", "homosexual",
    "bisexual", "asexual", "sex chromosomes", "biological sex",
})

# Leetspeak translation table
_LEET_MAP = {
    "0": "o", "1": "i", "3": "e", "4": "a", "@": "a",
    "$": "s", "5": "s", "7": "t", "!": "i", "+": "t"
}

# One compiled alternation instead of ~55 per-call regex compilations. This is
# on the tracker hot path (every active browser tick).
_EXPLICIT_TERM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in sorted(_EXPLICIT_KEYWORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_NUDITY_ROOT_RE = re.compile(r"\b(naked|nude|sex|sexy|erotic|strip|leaked)\b", re.IGNORECASE)
_MEDIA_ROOT_RE = re.compile(r"\b(video|videos|clips|pics|photos|movie|movies|stream|leak|leaks)\b", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"[\s\-_.]+")


@lru_cache(maxsize=2048)
def _normalize_cached(text: str) -> str:
    if not text:
        return ""
    try:
        text = urllib.parse.unquote(text)
    except Exception:
        pass
    text = text.lower()
    # Convert simple leetspeak
    for k, v in _LEET_MAP.items():
        text = text.replace(k, v)
    return _WHITESPACE_RE.sub(" ", text).strip()


@lru_cache(maxsize=2048)
def _classify_adult_title(title: str, domain: str) -> Tuple[bool, str]:
    """Memoised full-title classification (pure given the static word lists)."""
    if not title:
        return False, ""

    # Check domain first
    if domain and AdultContentClassifier.is_adult_domain(domain):
        return True, f"Restricted adult domain: {domain}"

    query = AdultContentClassifier.extract_search_query(title)
    if query:
        is_adult, reason = AdultContentClassifier.is_adult_query(query)
        if is_adult:
            return True, reason

    norm_title = AdultContentClassifier.normalize_text(title)
    for safe in _SAFE_CONTEXT_EXCLUSIONS:
        if safe in norm_title:
            return False, ""

    match = _EXPLICIT_TERM_RE.search(norm_title)
    if match:
        return True, f"Window title contains explicit keyword: '{match.group(0)}'"

    return False, ""


class AdultContentClassifier:
    """Classifies search queries, window titles, and domains for adult content."""

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Lowercases, decodes URL characters, and standardizes spacing."""
        return _normalize_cached(text or "")

    @classmethod
    def extract_search_query(cls, title: str) -> Optional[str]:
        """Extracts the actual user search query from a browser window title."""
        if not title:
            return None
        for pattern in _SEARCH_TITLE_PATTERNS:
            match = pattern.search(title)
            if match:
                query = match.group(1).strip()
                if query and query.lower() not in {"new tab", "home", "search"}:
                    return query
        return None

    @classmethod
    def is_adult_query(cls, query: str) -> Tuple[bool, str]:
        """
        Analyzes a search query or URL query parameter.
        Returns (is_adult: bool, reason: str).
        """
        if not query:
            return False, ""

        norm = cls.normalize_text(query)

        # 1. Check safe context exclusions
        for safe in _SAFE_CONTEXT_EXCLUSIONS:
            if safe in norm:
                return False, ""

        # 2. Check explicit keywords with word boundaries (single compiled pass)
        match = _EXPLICIT_TERM_RE.search(norm)
        if match:
            return True, f"Search contains restricted term: '{match.group(0)}'"

        # 3. Compound check (e.g. "naked" + "girls", "sex" + "clips")
        has_nudity_root = bool(_NUDITY_ROOT_RE.search(norm))
        has_media_root = bool(_MEDIA_ROOT_RE.search(norm))
        if has_nudity_root and has_media_root:
            return True, "Compound restricted adult search query detected"

        return False, ""

    @classmethod
    def is_adult_domain(cls, domain: str) -> bool:
        """Checks if a domain name is inherently adult."""
        if not domain:
            return False
        d = domain.lower().strip()
        if d.startswith("www."):
            d = d[4:]

        # Check TLD
        tld = d.split(".")[-1]
        if tld in _ADULT_TLDS:
            return True

        # Check known offline seed list
        from protection.content_blocker import SEED_DOMAINS
        if d in SEED_DOMAINS or f"www.{d}" in SEED_DOMAINS:
            return True

        # Check if any explicit keyword is in the domain apex
        name_part = d.split(".")[0]
        for kw in ("porn", "xxx", "hentai", "xvideo", "xnxx", "xhamster", "erotica", "camgirl", "chaturbate"):
            if kw in name_part:
                return True

        return False

    @classmethod
    def is_adult_title(cls, title: str, domain: str = "") -> Tuple[bool, str]:
        """
        Evaluates a browser window title and optional domain for explicit material.
        Returns (is_adult: bool, reason: str).

        The classification is deterministic and memoised: the same title is
        re-evaluated on every tracking tick while a tab stays in the foreground.
        """
        return _classify_adult_title(title or "", domain or "")


# ---------------------------------------------------------------------------
# Shield Engine & Active Tab Intervention
# ---------------------------------------------------------------------------
class AdultContentShield:
    """
    Singleton monitoring service. Hooks into TrackingManager ticks,
    detects adult searches/sites, closes tabs, and triggers the motivation popup.
    """
    _instance = None

    @classmethod
    def instance(cls) -> "AdultContentShield":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_intervention_ts = 0.0
        self._intervention_cooldown_s = 6.0
        self._motivation_callbacks = []

    def register_motivation_callback(self, cb: Callable[[str, str], None]) -> None:
        """Register a callback to open the motivation modal in the Qt main thread."""
        self._motivation_callbacks.append(cb)

    @staticmethod
    def close_active_browser_tab() -> None:
        """
        Simulates standard Windows shortcut Ctrl+W to immediately close
        the active browser tab displaying restricted content.
        """
        try:
            user32 = ctypes.windll.user32
            VK_CONTROL = 0x11
            VK_W = 0x57
            KEYEVENTF_KEYUP = 0x0002

            user32.keybd_event(VK_CONTROL, 0, 0, 0)
            user32.keybd_event(VK_W, 0, 0, 0)
            user32.keybd_event(VK_W, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            logger.info("[ADULT_SHIELD] Dispatched Ctrl+W to close active browser tab")
        except Exception as e:
            logger.warning(f"[ADULT_SHIELD] Failed to simulate tab close: {e}")

    def inspect(self, process_name: str, window_title: str, domain: str = "", hwnd: int = 0) -> bool:
        """
        Called on active tracking ticks. Returns True if adult content was detected
        and intervention occurred.
        """
        if not process_name:
            return False
        p_lower = process_name.lower()
        if p_lower not in BROWSER_PROCESSES:
            return False

        # Classify first: the classification is memoised and cheap, while the
        # settings lookup hits SQLite. Doing the cheap check first means the
        # common (non-adult) tick never opens a database cursor at all.
        is_adult, reason = AdultContentClassifier.is_adult_title(window_title, domain)
        if not is_adult:
            return False

        # Check if content filtering is enabled in Settings. This only runs for
        # titles that already matched, so the DB read is rare.
        from settings.manager import SettingsManager
        sm = SettingsManager()
        if not (sm.get_bool("adult_filter_enabled", True) or sm.get_bool("content_filter_enabled", True)):
            return False

        now = time.monotonic()
        with self._lock:
            if (now - self._last_intervention_ts) < self._intervention_cooldown_s:
                return True
            self._last_intervention_ts = now

        logger.warning(f"[ADULT_SHIELD] Blocked adult content: {reason} (process={process_name}, title={window_title[:60]})")

        # 1. Close offending browser tab
        self.close_active_browser_tab()

        # 2. Trigger motivation modal dialog
        for cb in self._motivation_callbacks:
            try:
                cb(reason, window_title)
            except Exception as exc:
                logger.warning(f"[ADULT_SHIELD] Motivation callback failed: {exc}")

        return True
