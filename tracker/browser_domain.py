"""
browser_domain.py — High-performance, non-blocking browser domain detection for Digital Wellbeing.

Architecture:
1. Fast Title Matching (<0.05ms, synchronous):
   Inspects foreground browser window title across Chrome, Edge, Brave, Firefox, etc.
   Matches known domains (YouTube, Google, GitHub, Reddit, etc.) and explicit domain patterns.
2. Background UIA Fallback (asynchronous, non-blocking):
   Queries browser address bar via UIAutomation in a worker thread with timeout, caching results.
   Never blocks the Qt UI loop or foreground tracking loop.
"""
from __future__ import annotations

import re
import threading
import time
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

# UIA cache: hwnd -> (domain, timestamp)
_UIA_CACHE: Dict[int, Tuple[str, float]] = {}
_UIA_CACHE_LOCK = threading.Lock()
_ACTIVE_UIA_QUERIES = set()
_UIA_QUERY_LOCK = threading.Lock()


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


def extract_domain_from_title(title: str, process_name: str = "") -> str:
    """
    Extract normalized domain (e.g. 'youtube.com', 'google.com', 'github.com')
    from browser window title. Fast and completely non-blocking (<0.05ms).
    """
    if not title:
        return ""

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


def _query_uia_address_bar_async(hwnd: int, process_name: str) -> None:
    """Background worker to query UIA address bar without blocking UI."""
    with _UIA_QUERY_LOCK:
        if hwnd in _ACTIVE_UIA_QUERIES:
            return
        _ACTIVE_UIA_QUERIES.add(hwnd)

    def worker():
        try:
            import uiautomation as auto
            # Short timeout so we don't hold resources
            auto.SetGlobalSearchTimeout(0.25)
            win = auto.ControlFromHandle(hwnd)
            if not win or not win.Exists(0, 0):
                return

            # Find address bar edit control
            edit = win.EditControl(searchDepth=6)
            if edit and edit.Exists(0, 0):
                val = edit.GetValuePattern().Value or edit.Name
                if val:
                    val = val.strip().lower()
                    val = re.sub(r"^https?://", "", val).split("/")[0].split(":")[0]
                    if val.startswith("www."):
                        val = val[4:]
                    if _DOMAIN_REGEX.match(val):
                        with _UIA_CACHE_LOCK:
                            _UIA_CACHE[hwnd] = (val, time.monotonic())
        except Exception:
            pass
        finally:
            with _UIA_QUERY_LOCK:
                _ACTIVE_UIA_QUERIES.discard(hwnd)

    t = threading.Thread(target=worker, daemon=True)
    t.start()


def get_active_browser_domain(process_name: str, window_title: str, hwnd: int = 0) -> str:
    """
    Get the active website domain for the foreground browser.
    Completely non-blocking: uses fast title parsing first, then cached UIA fallback.
    """
    if not is_browser_process(process_name):
        return ""

    # Fast path: window title parsing
    domain = extract_domain_from_title(window_title, process_name)
    if domain:
        return domain

    # Check UIA cache
    if hwnd > 0:
        now = time.monotonic()
        with _UIA_CACHE_LOCK:
            if hwnd in _UIA_CACHE:
                cached_dom, ts = _UIA_CACHE[hwnd]
                if now - ts < 3.0:
                    return cached_dom

        # Trigger background UIA query if not present
        _query_uia_address_bar_async(hwnd, process_name)

    return ""
