"""
media_awareness.py — Foreground media / lecture / notes detection for SleepGuard.

GSMTC is authoritative for playback state, but it can miss browser players,
VLC variants, and lecture/notes apps. This module adds a lightweight foreground
check so SleepGuard does not power off while someone is watching or reading.

Detection strategy (in priority order):
  1. Gaming processes → explicitly excluded (SleepGuard stays INACTIVE).
  2. Dedicated media-player processes → always ACTIVE (kind="media").
  3. Browser processes → ACTIVE only when:
       a. The window title matches a streaming/lecture service, OR
       b. The title contains "- YouTube" but NOT "Shorts"/"YouTube Shorts", OR
       c. The foreground window is fullscreen (≥ 95 % of the primary monitor).
  4. Reading / note-taking processes → ACTIVE (kind="notes").

Detection is intentionally conservative:
  * Gaming is explicitly excluded to avoid blocking sleep during long sessions.
  * Shorts / TikTok / Reels in browser are NOT treated as blocking media.
  * Fullscreen browser is treated as media regardless of title (e.g. slideshows,
    local HTML, or streaming sites that change the title after load).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

import psutil
import win32api
import win32con
import win32gui
import win32process

# ---------------------------------------------------------------------------
# Cache TTL
# ---------------------------------------------------------------------------
_CACHE_SECONDS = 1.5

# ---------------------------------------------------------------------------
# Process sets
# ---------------------------------------------------------------------------

_MEDIA_PROCESSES = frozenset({
    # VLC
    "vlc.exe", "vlc",
    # MPV
    "mpv.exe", "mpv",
    # Windows built-ins
    "wmplayer.exe", "video.ui.exe", "zunevideo.exe", "music.ui.exe",
    "moviesandtv.exe", "microsoft.zunevideo.exe", "filmstv.exe",
    # MPC family
    "mpc-hc.exe", "mpc-hc64.exe", "mpc-be.exe", "mpc-be64.exe",
    # PotPlayer
    "potplayermini.exe", "potplayermini64.exe", "potplayer.exe",
    "daum potplayer.exe",
    # Other local players
    "kmplayer.exe", "gomplayer.exe", "bsplayer.exe", "bs.player.exe",
    "klite.exe", "gretech.exe", "mxplayer.exe", "mx player.exe",
    "airplayer.exe", "infuse.exe", "mediaplayer.exe",
    # Plex / Kodi / Jellyfin
    "plexmediaplayer.exe", "plex.exe", "kodi.exe", "jellyfin.exe",
    # Music / podcast (still shouldn't sleep mid-playback)
    "spotify.exe", "itunes.exe",
    # Additional popular players
    "dvdplayer.exe", "smplayer.exe", "mplayerc.exe", "mpchc.exe",
    "mediaplayerclassic.exe", "realplayer.exe", "realplay.exe",
    "winamp.exe", "foobar2000.exe", "j river media center.exe",
    "jriver.exe", "mediamonkey.exe", "zoom.exe", "teams.exe",
    "webex.exe", "slack.exe",                          # video calls
})

_BROWSER_PROCESSES = frozenset({
    "chrome.exe", "brave.exe", "msedge.exe", "firefox.exe",
    "opera.exe", "vivaldi.exe", "chromium.exe",
    # Additional browsers
    "opera_gx.exe", "yandex.exe", "browser.exe",      # Yandex Browser
    "thorium.exe", "librewolf.exe", "waterfox.exe",
    "palemoon.exe", "falkon.exe", "maxthon.exe",
    "uc browser.exe", "ucbrowser.exe", "avast browser.exe",
})

_READING_PROCESSES = frozenset({
    # PDF readers
    "acrord32.exe", "acrobat.exe", "sumatrapdf.exe",
    "foxitreader.exe", "foxitpdfreader.exe", "pdfxchangeeditor.exe",
    "pdfxchangeviewer.exe", "nitropdf.exe", "drawboardpdf.exe",
    "drawboard pdf.exe", "xodo.exe",
    # Note-taking / PKM
    "onenote.exe", "onenoteim.exe", "notion.exe", "obsidian.exe",
    "logseq.exe", "remnote.exe", "roamresearch.exe",
    # Reference managers
    "zotero.exe", "mendeley.exe", "mendeleydesktop.exe",
    # Flashcards / study
    "anki.exe",
    # E-book readers
    "kindle.exe", "kobo.exe", "calibre.exe",
    # Office
    "winword.exe", "excel.exe", "powerpnt.exe", "wpp.exe",
})

# ---------------------------------------------------------------------------
# Gaming processes — explicitly EXCLUDED from SleepGuard
# (games typically send input events that reset the idle timer anyway, but
#  this guard ensures we never accidentally block sleep during gaming.)
# ---------------------------------------------------------------------------
_GAMING_PROCESSES = frozenset({
    # Launchers / platforms
    "steam.exe", "epicgameslauncher.exe", "gog galaxy.exe", "goggalaxy.exe",
    "origin.exe", "ubisoft connect.exe", "uplay.exe", "battlenet.exe",
    "battle.net.exe", "riotclientservices.exe", "riotclient.exe",
    # Popular titles (executables)
    "cs2.exe", "csgo.exe", "cs_go.exe",                # Counter-Strike
    "valorant.exe", "valorant-win64-shipping.exe",
    "pubg.exe", "tslgame.exe",                          # PUBG
    "freefire.exe", "garena free fire.exe",
    "fortnite.exe", "fortniteclient-win64-shipping.exe",
    "leagueoflegends.exe", "league of legends.exe",
    "dota2.exe",
    "overwatch.exe", "overwatch2.exe",
    "r5apex.exe",                                       # Apex Legends
    "cod.exe", "modernwarfare.exe", "warzone.exe",
    "minecraft.exe", "minecraftlauncher.exe", "javaw.exe",
    "gta5.exe", "gtav.exe", "rdr2.exe",
    "eldenring.exe", "sekiro.exe", "ds3.exe",
    "cyberpunk2077.exe", "witcher3.exe",
    "battlefieldv.exe", "bf2042.exe",
    "rainbowsix.exe", "r6.exe",
    "rocketleague.exe",
    "fifa23.exe", "fifa24.exe", "eafc24.exe",
    "nba2k24.exe",
    "among us.exe",
    "fall guys.exe", "fallguys_client_game.exe",
})

# ---------------------------------------------------------------------------
# Title regexes
# ---------------------------------------------------------------------------

# Matches streaming / lecture service names or playback-intent keywords in a
# browser window title.  Shorts / TikTok / Reels are intentionally EXCLUDED
# here; they are tested separately in _is_short_form_video().
_BROWSER_TITLE_RE = re.compile(
    r"""
    # ---- Mainstream streaming ----
    youtube | youtu\.be |
    netflix | prime\s*video | amazon\s*prime | hotstar | disney\+? |
    twitch | vimeo | dailymotion | hulu | max\.com |
    apple\s*tv\+? | showtime | peacock |
    # ---- Indian / regional streaming ----
    zee5 | sonyliv | jio\s*cinema | jiosaavn |
    mxplayer | mx\s*player | erosnow |
    # ---- Anime / niche ----
    crunchyroll | funimation | animixplay | 9anime | aniwatch |
    # ---- Education ----
    coursera | udemy | edx | khan\s*academy | skillshare | masterclass |
    lecture | lectures | webinar | course | lesson |
    # ---- Playback-intent words ----
    watching | playing | streaming | live\s*stream |
    # ---- Reading / documents ----
    \.pdf | slides | presentation | notes?
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Matches a YouTube *video* tab: title ends with "- YouTube" but does NOT
# contain "Shorts" or "YouTube Shorts".
_YOUTUBE_VIDEO_RE = re.compile(
    r"-\s*YouTube\s*$",
    re.IGNORECASE,
)
_YOUTUBE_SHORTS_RE = re.compile(
    r"(shorts|youtube\s*shorts)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MediaAwarenessState:
    """Snapshot of whether foreground activity should prevent sleep."""

    active: bool = False
    kind: str = ""       # "media" | "lecture" | "notes" | "fullscreen"
    label: str = ""
    process: str = ""
    title: str = ""

    @property
    def is_active(self) -> bool:
        return self.active


_last_state = MediaAwarenessState()
_last_check = 0.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _foreground_window() -> tuple[str, str, int]:
    """Return (process_name_lower, window_title, hwnd) for the foreground window."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "", "", 0
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return "", title, hwnd
        name = psutil.Process(pid).name().lower()
        return name, title, hwnd
    except Exception:
        return "", "", 0


def _is_fullscreen(hwnd: int) -> bool:
    """Return True when *hwnd* covers ≥ 95 % of the primary monitor work area.

    Uses the primary monitor dimensions from ``GetSystemMetrics`` so it works
    correctly on single-monitor setups.  On multi-monitor systems this is a
    best-effort check against the primary screen only.
    """
    if not hwnd:
        return False
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        w_win = right - left
        h_win = bottom - top
        if w_win <= 0 or h_win <= 0:
            return False

        screen_w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        screen_h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        if screen_w <= 0 or screen_h <= 0:
            return False

        # 95 % threshold to tolerate 1-pixel border / window chrome artefacts
        coverage = (w_win * h_win) / (screen_w * screen_h)
        return coverage >= 0.95
    except Exception:
        return False


def _is_short_form_video(title: str) -> bool:
    """Return True if the title suggests a short-form video (Shorts, Reels, TikTok)."""
    return bool(_YOUTUBE_SHORTS_RE.search(title)) or bool(
        re.search(r"\breels?\b|\btiktok\b", title, re.IGNORECASE)
    )


def _is_youtube_video(title: str) -> bool:
    """Return True for a YouTube *video* tab (title ends with '- YouTube') but
    NOT for YouTube Shorts pages."""
    return (
        bool(_YOUTUBE_VIDEO_RE.search(title))
        and not _is_short_form_video(title)
    )


def _browser_is_media(title: str, hwnd: int) -> tuple[bool, str]:
    """Decide whether a browser window should be treated as media.

    Returns (is_media, kind_str).
    """
    # 1. Explicit short-form → not media
    if _is_short_form_video(title):
        return False, ""

    # 2. YouTube video (title ends with "- YouTube")
    if _is_youtube_video(title):
        return True, "media"

    # 3. Streaming / lecture / document keyword in title
    if _BROWSER_TITLE_RE.search(title):
        is_lecture = bool(
            re.search(
                r"lecture|course|notes?|pdf|slides|webinar|lesson|coursera|"
                r"udemy|edx|khan|skillshare|masterclass",
                title,
                re.IGNORECASE,
            )
        )
        return True, "lecture" if is_lecture else "media"

    # 4. Fullscreen browser → treat as media (e.g. F11 video player, slideshow)
    if _is_fullscreen(hwnd):
        return True, "fullscreen"

    return False, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_foreground_media(force: bool = False) -> MediaAwarenessState:
    """Return a (cached) snapshot of foreground media / lecture / notes activity.

    Parameters
    ----------
    force:
        Bypass the internal cache and re-query the foreground window immediately.

    Returns
    -------
    MediaAwarenessState
        ``active=True`` when SleepGuard should inhibit sleep.
        ``active=False`` for gaming processes, short-form video, idle desktop,
        or any state where sleep should proceed normally.
    """
    global _last_state, _last_check
    now = time.monotonic()
    if not force and now - _last_check < _CACHE_SECONDS:
        return _last_state

    process, title, hwnd = _foreground_window()
    state = MediaAwarenessState()

    if process:
        if process in _GAMING_PROCESSES:
            # Explicit exclusion: gaming should NOT block sleep via SleepGuard.
            # (The OS idle timer is reset by user input independently.)
            state = MediaAwarenessState(
                active=False,
                kind="gaming",
                label=f"{process.rsplit('.', 1)[0].title()} (gaming — sleep allowed)",
                process=process,
                title=title,
            )

        elif process in _MEDIA_PROCESSES:
            state = MediaAwarenessState(
                active=True,
                kind="media",
                label=f"{process.rsplit('.', 1)[0].title()} playback",
                process=process,
                title=title,
            )

        elif process in _BROWSER_PROCESSES:
            is_media, kind = _browser_is_media(title, hwnd)
            if is_media:
                state = MediaAwarenessState(
                    active=True,
                    kind=kind,
                    label=title[:120] or "Browser media",
                    process=process,
                    title=title,
                )

        elif process in _READING_PROCESSES:
            state = MediaAwarenessState(
                active=True,
                kind="notes",
                label=f"{process.rsplit('.', 1)[0].title()} document",
                process=process,
                title=title,
            )

    _last_state = state
    _last_check = now
    return state


def describe_state(state: Optional[MediaAwarenessState]) -> str:
    """Return a human-readable summary of *state* for UI / logging."""
    if not state or not state.active:
        return "No media or lecture activity detected"
    label = state.label or state.kind.title()
    return f"{state.kind.title()} active — {label}"
