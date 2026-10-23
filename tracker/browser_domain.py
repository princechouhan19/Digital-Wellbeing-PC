"""
browser_domain.py — High-performance, non-blocking browser domain detection for Digital Wellbeing.

Architecture:
1. Fast Title Matching (<0.05 ms, synchronous, memoised):
   Inspects the foreground browser window title across Chrome, Edge, Brave,
   Firefox, etc. and matches known services / explicit domain patterns.
2. Background UIA Fallback (single worker, coalesced, cached):
   Queries the browser address bar via UI Automation when the title has no
   usable domain. Requests are queued per window (latest request wins), results
   are cached with positive/negative TTLs, and repeated failures back off
   exponentially. No thread is spawned per call, so rapid tab switching cannot
   create a thread/COM storm.
"""
from __future__ import annotations

import queue
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional, Tuple

from core.logger import logger

from tracker.foreground import BROWSER_PROCESSES

# Suffixes added to window titles by browsers
_BROWSER_SUFFIX_PATTERNS = [
    re.compile(r"\s+and\s+\d+\s+more\s+pages?\s*-\s*(?:Personal|Work|Profile\s+\d+)?\s*-\s*Microsoft\s+Edge$", re.I),
    re.compile(r"\s*-\s*Personal\s*-\s*Microsoft\s+Edge$", re.I),
    re.compile(r"\s*-\s*Work\s*-\s*Microsoft\s+Edge$", re.I),
    re.compile(r"\s*-\s*Microsoft\s+Edge$", re.I),
    re.compile(r"\s*-\s*Google\s+Chrome$", re.I),
    re.compile(r"\s*-\s*Brave$", re.I),
    re.compile(r"\s*[—–-]\s*Mozilla\s+Firefox$", re.I),
    re.compile(r"\s*-\s*Opera\s*GX$", re.I),
    re.compile(r"\s*-\s*Opera$", re.I),
    re.compile(r"\s*-\s*Vivaldi$", re.I),
    re.compile(r"\s*-\s*Arc$", re.I),
    re.compile(r"\s*-\s*Atlas$", re.I),
    re.compile(r"\s*-\s*Comet$", re.I),
    re.compile(r"\s*-\s*Zen(?:\s+Browser)?$", re.I),
    re.compile(r"\s*-\s*Chromium$", re.I),
    re.compile(r"\s*-\s*Waterfox$", re.I),
    re.compile(r"\s*-\s*LibreWolf$", re.I),
    re.compile(r"\s*-\s*Tor\s+Browser$", re.I),
    re.compile(r"\s*-\s*DuckDuckGo$", re.I),
]

# Patterns for popular services (case-insensitive)
_KNOWN_SERVICE_PATTERNS = [
    (re.compile(r"\byoutube\b|youtu\.be", re.I), "youtube.com"),
    (re.compile(r"\bgoogle(?:\s+search)?\b", re.I), "google.com"),
    (re.compile(r"\bgithub\b", re.I), "github.com"),
    (re.compile(r"\breddit\b", re.I), "reddit.com"),
    (re.compile(r"\btwitter\b|\b/\s*x\b|^x\s*[-–—]|\bx\.com\b", re.I), "twitter.com"),
    (re.compile(r"\binstagram\b", re.I), "instagram.com"),
    (re.compile(r"\bfacebook\b", re.I), "facebook.com"),
    (re.compile(r"\bnetflix\b", re.I), "netflix.com"),
    (re.compile(r"\btwitch(?:\.tv)?\b", re.I), "twitch.tv"),
    (re.compile(r"\bdiscord(?:\.com|\.gg)?\b", re.I), "discord.com"),
    (re.compile(r"\bamazon\b", re.I), "amazon.com"),
    (re.compile(r"\bwikipedia\b", re.I), "wikipedia.org"),
    (re.compile(r"\blinkedin\b", re.I), "linkedin.com"),
    (re.compile(r"\bstackoverflow\b", re.I), "stackoverflow.com"),
    (re.compile(r"\bchatgpt\b|\bopenai\b", re.I), "chatgpt.com"),
    (re.compile(r"\bclaude(?:\s*-\s*anthropic)?\b|\banthropic\b", re.I), "claude.ai"),
    (re.compile(r"\bnotion\b", re.I), "notion.so"),
    (re.compile(r"\bfigma\b", re.I), "figma.com"),
    (re.compile(r"\bwhatsapp(?:\s+web)?\b", re.I), "whatsapp.com"),
    (re.compile(r"\btelegram(?:\s+web)?\b", re.I), "telegram.org"),
    (re.compile(r"\bslack\b", re.I), "slack.com"),
    (re.compile(r"\bspotify\b", re.I), "spotify.com"),
    (re.compile(r"\btiktok\b", re.I), "tiktok.com"),
    (re.compile(r"\bpinterest\b", re.I), "pinterest.com"),
    (re.compile(r"\bquora\b", re.I), "quora.com"),
    (re.compile(r"\bzoom\b", re.I), "zoom.us"),
    (re.compile(r"\bprime\s*video\b", re.I), "primevideo.com"),
    (re.compile(r"\bdisney(?:\+|plus)?\b|\bhotstar\b", re.I), "disneyplus.com"),
    (re.compile(r"\bcoursera\b", re.I), "coursera.org"),
    (re.compile(r"\budemy\b", re.I), "udemy.com"),
    (re.compile(r"\bleetcode\b", re.I), "leetcode.com"),
    (re.compile(r"\bmedium\b", re.I), "medium.com"),
    (re.compile(r"\bsubstack\b", re.I), "substack.com"),
    (re.compile(r"\bduckduckgo\b", re.I), "duckduckgo.com"),
    (re.compile(r"\bbing\b", re.I), "bing.com"),
    (re.compile(r"\bcanva\b", re.I), "canva.com"),
]

# Generic domain regex in window titles
_DOMAIN_REGEX = re.compile(
    r"\b([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:com|org|net|io|co|ai|tv|app|dev|edu|gov|in|uk|de|jp|ca|me|xyz|so|gg|to|cc|tech|info|biz|site|cloud|us))\b",
    re.I,
)

# ── UIA cache / worker tunables ──────────────────────────────────────────────
_UIA_POSITIVE_TTL_S = 30.0       # serve a resolved domain without re-querying
_UIA_STALE_SERVE_S = 45.0        # serve a stale domain while refreshing it
_UIA_NEGATIVE_TTL_S = 8.0        # do not retry an unresolved address bar immediately
_UIA_BASE_BACKOFF_S = 5.0
_UIA_MAX_BACKOFF_S = 120.0
_UIA_MAX_ENTRIES = 256
_UIA_MAX_PENDING = 64
_UIA_REQUEST_MAX_AGE_S = 5.0


@dataclass
class _UiaEntry:
    title_key: str
    domain: str
    updated_at: float
    next_attempt_at: float = 0.0
    failures: int = 0


_UIA_CACHE: "OrderedDict[int, _UiaEntry]" = OrderedDict()
_UIA_CACHE_LOCK = threading.Lock()
_UIA_PENDING: Dict[int, Tuple[str, float]] = {}
_UIA_QUEUED: set[int] = set()
_UIA_QUEUE: "queue.Queue[int]" = queue.Queue(maxsize=_UIA_MAX_PENDING)
_UIA_WORKER: Optional[threading.Thread] = None
_UIA_WORKER_LOCK = threading.Lock()
_UIA_TIMEOUT_CONFIGURED = False

# Tests set this to exercise the cache/queue logic without a real COM call.
_UIA_SYNC_MODE = False

_UIA_STATS = {
    "hits": 0,
    "stale_hits": 0,
    "negative_hits": 0,
    "queued": 0,
    "queries": 0,
    "resolved": 0,
}


def is_browser_process(process_name: str) -> bool:
    """Return True if process is a recognized web browser."""
    if not process_name:
        return False
    return process_name.lower() in BROWSER_PROCESSES


def clean_browser_title(title: str) -> str:
    """Strip browser branding and multi-tab suffixes from window title."""
    cleaned = title.strip()
    for pat in _BROWSER_SUFFIX_PATTERNS:
        cleaned = pat.sub("", cleaned).strip()
    return cleaned


@lru_cache(maxsize=1024)
def _extract_domain_cached(title: str) -> str:
    cleaned = clean_browser_title(title)
    if not cleaned or cleaned.lower() in {"new tab", "settings", "downloads", "history", "extensions", "untitled"}:
        return ""

    # 1. Match known high-traffic services
    for pattern, domain in _KNOWN_SERVICE_PATTERNS:
        if pattern.search(cleaned):
            return domain

    # 2. Match any explicit domain string in the title (e.g. "example.com - Page")
    match = _DOMAIN_REGEX.search(cleaned)
    if match:
        dom = match.group(1).lower()
        if dom.startswith("www."):
            dom = dom[4:]
        return dom

    return ""


def extract_domain_from_title(title: str, process_name: str = "") -> str:
    """
    Extract normalized domain (e.g. 'youtube.com', 'google.com', 'github.com')
    from browser window title. Fast and completely non-blocking (<0.05ms).

    Results are memoised: while a tab stays open the same title is parsed on
    every tracking tick, and the regex pass is the only CPU cost in that path.
    """
    if not title:
        return ""
    return _extract_domain_cached(title)


# ── UI Automation fallback ───────────────────────────────────────────────────


def _title_key(title: str) -> str:
    return (title or "").strip().lower()[:160]


def _normalize_address_value(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"^https?://", "", value).split("/")[0].split(":")[0]
    if value.startswith("www."):
        value = value[4:]
    if _DOMAIN_REGEX.match(value):
        return value
    return ""


def _query_uia_domain(hwnd: int) -> str:
    """Query the browser address bar once. Runs on the UIA worker thread."""
    global _UIA_TIMEOUT_CONFIGURED
    try:
        import uiautomation as auto

        if not _UIA_TIMEOUT_CONFIGURED:
            # Set once per process; the call mutates global COM search state.
            auto.SetGlobalSearchTimeout(0.25)
            _UIA_TIMEOUT_CONFIGURED = True

        win = auto.ControlFromHandle(hwnd)
        if not win or not win.Exists(0, 0):
            return ""

        edit = win.EditControl(searchDepth=6)
        if edit and edit.Exists(0, 0):
            val = ""
            try:
                val = edit.GetValuePattern().Value or ""
            except Exception:
                val = ""
            if not val:
                val = edit.Name or ""
            return _normalize_address_value(val)
    except Exception:
        return ""
    return ""


def _evict_if_needed() -> None:
    while len(_UIA_CACHE) > _UIA_MAX_ENTRIES:
        _UIA_CACHE.popitem(last=False)


def _store_entry(hwnd: int, title_key: str, domain: str, now: float) -> None:
    entry = _UIA_CACHE.get(hwnd)
    if entry is None:
        entry = _UiaEntry(title_key=title_key, domain=domain, updated_at=now)
        _UIA_CACHE[hwnd] = entry
    else:
        entry.title_key = title_key
        if domain:
            entry.domain = domain
            entry.updated_at = now
            entry.failures = 0
            entry.next_attempt_at = 0.0
        else:
            # Title changed and the new page could not be resolved: never keep
            # serving the previous tab's domain as if it belonged to this title.
            entry.domain = ""
            entry.updated_at = now
    if entry.domain:
        entry.next_attempt_at = now
    else:
        entry.next_attempt_at = now + _UIA_NEGATIVE_TTL_S
    _UIA_CACHE.move_to_end(hwnd)
    _evict_if_needed()


def _process_request(hwnd: int, title_key: str) -> None:
    domain = _query_uia_domain(hwnd)
    now = time.monotonic()
    with _UIA_CACHE_LOCK:
        _UIA_STATS["queries"] += 1
        entry = _UIA_CACHE.get(hwnd)
        if entry is not None and entry.title_key == title_key:
            if domain:
                entry.domain = domain
                entry.updated_at = now
                entry.failures = 0
                entry.next_attempt_at = 0.0
                _UIA_STATS["resolved"] += 1
            else:
                entry.failures += 1
                backoff = min(
                    _UIA_MAX_BACKOFF_S,
                    _UIA_BASE_BACKOFF_S * (2 ** min(entry.failures - 1, 5)),
                )
                entry.next_attempt_at = now + max(_UIA_NEGATIVE_TTL_S, backoff)
            _UIA_CACHE.move_to_end(hwnd)
        else:
            _store_entry(hwnd, title_key, domain, now)
            if domain:
                _UIA_STATS["resolved"] += 1


def _ensure_worker() -> None:
    global _UIA_WORKER
    if _UIA_WORKER is not None and _UIA_WORKER.is_alive():
        return
    with _UIA_WORKER_LOCK:
        if _UIA_WORKER is not None and _UIA_WORKER.is_alive():
            return
        _UIA_WORKER = threading.Thread(
            target=_uia_worker_loop,
            name="BrowserUiaResolver",
            daemon=True,
        )
        _UIA_WORKER.start()


def _uia_worker_loop() -> None:
    while True:
        hwnd = _UIA_QUEUE.get()
        try:
            with _UIA_CACHE_LOCK:
                item = _UIA_PENDING.pop(hwnd, None)
                _UIA_QUEUED.discard(hwnd)
            if not item:
                continue
            title_key, requested_at = item
            if (time.monotonic() - requested_at) > _UIA_REQUEST_MAX_AGE_S:
                continue
            _process_request(hwnd, title_key)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("UIA resolver error for hwnd %s: %s", hwnd, exc)
        finally:
            try:
                _UIA_QUEUE.task_done()
            except Exception:
                pass


def _enqueue_uia_request(hwnd: int, title_key: str) -> None:
    now = time.monotonic()
    with _UIA_CACHE_LOCK:
        _UIA_PENDING[hwnd] = (title_key, now)
        _UIA_STATS["queued"] += 1
        already_queued = hwnd in _UIA_QUEUED
        _UIA_QUEUED.add(hwnd)

    if _UIA_SYNC_MODE:
        with _UIA_CACHE_LOCK:
            item = _UIA_PENDING.pop(hwnd, None)
            _UIA_QUEUED.discard(hwnd)
        if item:
            _process_request(hwnd, item[0])
        return

    if already_queued:
        # Latest request wins; the worker reads the freshest title from
        # _UIA_PENDING when it dequeues this hwnd.
        return

    _ensure_worker()
    try:
        _UIA_QUEUE.put_nowait(hwnd)
    except queue.Full:
        with _UIA_CACHE_LOCK:
            _UIA_QUEUED.discard(hwnd)
            _UIA_PENDING.pop(hwnd, None)
        logger.debug("UIA request queue full; dropping hwnd %s", hwnd)


def _lookup_cached_domain(hwnd: int, title_key: str, now: float) -> Tuple[bool, str, bool]:
    """Return (handled, domain, should_refresh) for the current cache entry."""
    with _UIA_CACHE_LOCK:
        entry = _UIA_CACHE.get(hwnd)
        if entry is None or entry.title_key != title_key:
            return False, "", True

        age = now - entry.updated_at
        if entry.domain:
            _UIA_CACHE.move_to_end(hwnd)
            if age <= _UIA_POSITIVE_TTL_S:
                _UIA_STATS["hits"] += 1
                return True, entry.domain, False
            if age <= _UIA_STALE_SERVE_S:
                _UIA_STATS["stale_hits"] += 1
                return True, entry.domain, True
            return False, "", True

        # Negative cache: an unresolved address bar is retried only after the
        # backoff window, so a non-standard browser UI cannot cause a COM query
        # on every tick.
        if now < entry.next_attempt_at:
            _UIA_STATS["negative_hits"] += 1
            return True, "", False
        return False, "", True


def get_active_browser_domain(process_name: str, window_title: str, hwnd: int = 0) -> str:
    """
    Get the active website domain for the foreground browser.
    Completely non-blocking: fast title parsing first, then a coalesced and
    cached UIA fallback that never blocks the caller.
    """
    if not is_browser_process(process_name):
        return ""

    # Fast path: window title parsing (memoised)
    domain = extract_domain_from_title(window_title, process_name)
    if domain:
        return domain

    if hwnd <= 0:
        return ""

    title_key = _title_key(window_title)
    now = time.monotonic()
    handled, cached, should_refresh = _lookup_cached_domain(hwnd, title_key, now)
    if handled and not should_refresh:
        return cached

    if not _UIA_SYNC_MODE:
        _enqueue_uia_request(hwnd, title_key)
        return cached

    _enqueue_uia_request(hwnd, title_key)
    with _UIA_CACHE_LOCK:
        entry = _UIA_CACHE.get(hwnd)
        if entry is not None and entry.title_key == title_key:
            return entry.domain
    return cached


# ── Diagnostics / tests ─────────────────────────────────────────────────────


def get_uia_cache_stats() -> dict[str, int]:
    with _UIA_CACHE_LOCK:
        stats = dict(_UIA_STATS)
        stats["cache_entries"] = len(_UIA_CACHE)
        stats["pending"] = len(_UIA_PENDING)
        return stats


def reset_uia_cache() -> None:
    """Clear all cache/queue state (used by tests and profile resets)."""
    global _UIA_TIMEOUT_CONFIGURED
    with _UIA_CACHE_LOCK:
        _UIA_CACHE.clear()
        _UIA_PENDING.clear()
        _UIA_QUEUED.clear()
        for key in _UIA_STATS:
            _UIA_STATS[key] = 0
        _UIA_TIMEOUT_CONFIGURED = False
