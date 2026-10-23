"""
media.py — GSMTC WinRT Media Playback Detection Engine for Digital Wellbeing Platform v2.

Detects active media playback on Windows via Global System Media Transport Controls (GSMTC)
for browser streams (YouTube, Netflix, Prime Video, JioHotstar) and desktop media apps (Spotify, VLC, WMP).
"""

from __future__ import annotations

import asyncio
import logging
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Optional

import psutil
import win32gui
import win32process

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()
    UNKNOWN = auto()


@dataclass(frozen=True)
class MediaInfo:
    state: PlaybackState = PlaybackState.UNKNOWN
    app_name: str = ""
    service_name: str = ""
    title: str = ""

    @property
    def is_playing(self) -> bool:
        return self.state == PlaybackState.PLAYING

    @property
    def display_name(self) -> str:
        if self.state != PlaybackState.PLAYING:
            return "No media playing"
        name = self.service_name or self._friendly_app()
        verb = "Listening to" if name.lower() in ("spotify",) else "Watching"
        return f"{verb} {name}"

    @property
    def source_label(self) -> str:
        return self.service_name or self._friendly_app() or "None"

    def _friendly_app(self) -> str:
        mapping = {
            "brave": "Brave",
            "chrome": "Chrome",
            "msedge": "Edge",
            "firefox": "Firefox",
            "vlc": "VLC",
            "spotify": "Spotify",
            "wmplayer": "Windows Media Player",
        }
        key = self.app_name.lower().split(".exe")[0].split("!")[0]
        for k, v in mapping.items():
            if k in key:
                return v
        return self.app_name or "Unknown"


class BaseMediaDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def check(self) -> Optional[MediaInfo]:
        pass


_PLAYBACK_STATUS_PLAYING: int = 4
_PLAYBACK_STATUS_PAUSED: int = 5


def _playback_status_to_state(status: int) -> PlaybackState:
    if status == _PLAYBACK_STATUS_PLAYING:
        return PlaybackState.PLAYING
    if status == _PLAYBACK_STATUS_PAUSED:
        return PlaybackState.PAUSED
    return PlaybackState.STOPPED


async def _query_gsmtc() -> list[dict]:
    try:
        from winrt.windows.media.control import (
            GlobalSystemMediaTransportControlsSessionManager as _MediaManager,
        )
        mgr = await _MediaManager.request_async()
        sessions = mgr.get_sessions()
        results: list[dict] = []
        for session in sessions:
            try:
                info = session.get_playback_info()
                playback_status = int(info.playback_status)
                is_playing = playback_status == _PLAYBACK_STATUS_PLAYING
                props = await session.try_get_media_properties_async()
                results.append({
                    "app_id": session.source_app_user_model_id or "",
                    "is_playing": is_playing,
                    "playback_status": playback_status,
                    "title": props.title or "",
                    "artist": props.artist or "",
                })
            except Exception as exc:
                logger.debug("Error reading GSMTC session: %s", exc)
        return results
    except Exception as exc:
        logger.debug("GSMTC query failed: %s", exc)
        return []


_SERVICE_PATTERNS: list[tuple[str, str]] = [
    (r"netflix", "Netflix"),
    (r"jiohotstar|hotstar", "JioHotstar"),
    (r"prime\s*video|amazon\s*prime", "Prime Video"),
    (r"youtube", "YouTube"),
    (r"spotify", "Spotify"),
]
_SERVICE_RE: list[tuple[re.Pattern, str]] = [
    (re.compile(p, re.IGNORECASE), label)
    for p, label in _SERVICE_PATTERNS
]

_BROWSER_EXES = frozenset({"chrome.exe", "brave.exe", "msedge.exe", "firefox.exe"})
_BROWSER_AUMIDS = frozenset({"chrome", "brave", "msedge", "firefox", "chromium"})

_browser_title_cache: list[str] = []
_browser_title_cache_at: float = 0.0


def _get_browser_window_titles() -> list[str]:
    global _browser_title_cache_at
    if time.monotonic() - _browser_title_cache_at < 10.0:
        return _browser_title_cache

    titles: list[str] = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            if proc.name().lower() in _BROWSER_EXES:
                titles.append(title)
        except Exception:
            pass

    try:
        win32gui.EnumWindows(_cb, None)
    except Exception:
        pass
    _browser_title_cache[:] = titles
    _browser_title_cache_at = time.monotonic()
    return titles


def _identify_service(app_id: str, media_title: str = "") -> str:
    app_lower = app_id.lower()
    if "spotify" in app_lower:
        return "Spotify"
    if "vlc" in app_lower:
        return "VLC"
    if "wmplayer" in app_lower or "zune" in app_lower:
        return "Windows Media Player"

    if media_title:
        for pattern, label in _SERVICE_RE:
            if pattern.search(media_title):
                return label

    for aumid_prefix in _BROWSER_AUMIDS:
        if aumid_prefix in app_lower:
            titles = _get_browser_window_titles()
            for t in titles:
                for pattern, label in _SERVICE_RE:
                    if pattern.search(t):
                        return label
    return ""


class GSMTCDetector(BaseMediaDetector):
    name = "GSMTC"

    async def check(self) -> Optional[MediaInfo]:
        sessions = await _query_gsmtc()
        if not sessions:
            return None

        playing = [s for s in sessions if s["is_playing"]]
        chosen = playing[0] if playing else sessions[0]

        state = _playback_status_to_state(chosen["playback_status"])
        app_id = chosen["app_id"]
        service = _identify_service(app_id, media_title=chosen["title"])

        return MediaInfo(
            state=state,
            app_name=app_id,
            service_name=service,
            title=chosen["title"],
        )


class MediaDetectionEngine:
    def __init__(
        self,
        poll_interval: float = 2.0,
        on_state_change: Optional[Callable[[MediaInfo], None]] = None,
    ) -> None:
        self._poll_interval = poll_interval
        self._on_state_change = on_state_change
        self._detectors: list[BaseMediaDetector] = [GSMTCDetector()]
        self._current: MediaInfo = MediaInfo()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="MediaDetectionEngine-loop",
            daemon=True,
        )
        self._thread.start()
        logger.info("MediaDetectionEngine started (poll_interval=%.1fs).", self._poll_interval)

    def stop(self) -> None:
        self._running = False
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("MediaDetectionEngine stopped.")

    @property
    def current(self) -> MediaInfo:
        return self._current

    @property
    def is_playing(self) -> bool:
        return self._current.is_playing

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        self._loop.run_until_complete(self._poll_loop())

    async def _poll_loop(self) -> None:
        while self._running:
            await self._poll_once()
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._stop_event.wait()),
                    timeout=self._poll_interval,
                )
                break
            except asyncio.TimeoutError:
                pass

    async def _poll_once(self) -> None:
        new_info = MediaInfo()
        for detector in self._detectors:
            try:
                res = await detector.check()
                if res is not None:
                    if res.is_playing:
                        new_info = res
                        break
                    elif new_info.state == PlaybackState.UNKNOWN:
                        new_info = res
            except Exception as exc:
                logger.error("Detector %s raised: %s", detector.name, exc)

        prev_playing = self._current.is_playing
        curr_playing = new_info.is_playing

        if new_info.is_playing and not new_info.service_name and self._current.service_name:
            if new_info.app_name == self._current.app_name:
                new_info = MediaInfo(
                    state=new_info.state,
                    app_name=new_info.app_name,
                    service_name=self._current.service_name,
                    title=new_info.title,
                )

        changed = prev_playing != curr_playing or (
            curr_playing and (
                self._current.service_name != new_info.service_name
                or self._current.app_name != new_info.app_name
            )
        )

        self._current = new_info

        if changed and self._on_state_change:
            try:
                self._on_state_change(new_info)
            except Exception as exc:
                logger.error("on_state_change callback error: %s", exc)
