"""
website_icon_provider.py — Asynchronous website favicon/logo downloader and cache for Digital Wellbeing.

Features:
- Dual-tier caching: In-memory (0ms) and on-disk in %LOCALAPPDATA%/DigitalWellbeing/favicons
- Asynchronous fetching from high-resolution favicon providers without blocking Qt UI
- Elegant fallback avatar generation (domain-hash based rounded squircles with clean typography)
- Signal-based updates: UI components listening to `icon_ready` update dynamically when icons arrive
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Set

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

from core.logger import logger

# Vibrant modern palette for deterministic avatar backgrounds
_AVATAR_PALETTE = [
    "#0078D4",  # Blue
    "#0A84FF",  # Electric Blue
    "#5E5CE6",  # Indigo
    "#AF52DE",  # Purple
    "#FF2D55",  # Pink
    "#FF3B30",  # Red
    "#FF9500",  # Orange
    "#34C759",  # Green
    "#30D158",  # Mint
    "#00C7BE",  # Teal
    "#32ADE6",  # Cyan
]


class _WebsiteIconSignals(QObject):
    icon_ready = Signal(str, QIcon)  # domain, icon


class WebsiteIconProvider:
    """Singleton provider for website icons/favicons with async download and disk caching."""

    _instance: Optional[WebsiteIconProvider] = None
    _lock = threading.Lock()

    def __new__(cls) -> WebsiteIconProvider:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._signals = _WebsiteIconSignals()
        self._memory_cache: Dict[str, QIcon] = {}
        self._pending_downloads: Set[str] = set()
        self._cache_lock = threading.Lock()

        # Disk cache directory
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            self._cache_dir = Path(local_app_data) / "DigitalWellbeing" / "favicons"
        else:
            self._cache_dir = Path.home() / "AppData" / "Local" / "DigitalWellbeing" / "favicons"

        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create favicons cache directory: %s", exc)

    @property
    def icon_ready(self) -> Signal:
        return self._signals.icon_ready

    @staticmethod
    def normalize_domain(domain: str) -> str:
        """Sanitize and normalize domain name for caching and network requests."""
        if not domain:
            return ""
        d = domain.strip().lower()
        d = re.sub(r"^https?://", "", d)
        d = d.split("/")[0].split(":")[0]
        if d.startswith("www."):
            d = d[4:]
        return d

    def get_icon(self, domain: str, size: int = 32) -> QIcon:
        """
        Get QIcon for domain. If cached, returns immediately.
        If not cached, returns a generated avatar icon and triggers an async fetch.
        """
        norm_domain = self.normalize_domain(domain)
        if not norm_domain:
            return self._create_letter_avatar("?", size)

        with self._cache_lock:
            if norm_domain in self._memory_cache:
                return self._memory_cache[norm_domain]

        # Check disk cache
        disk_file = self._cache_dir / f"{norm_domain}.png"
        if disk_file.exists() and disk_file.stat().st_size > 100:
            try:
                pixmap = QPixmap(str(disk_file))
                if not pixmap.isNull():
                    icon = QIcon(pixmap)
                    with self._cache_lock:
                        self._memory_cache[norm_domain] = icon
                    return icon
            except Exception:
                pass

        # Trigger background fetch if not already in flight
        self._trigger_async_fetch(norm_domain)

        # Return high-quality initial letter avatar while loading
        fallback_icon = self._create_letter_avatar(norm_domain, size)
        return fallback_icon

    def get_pixmap(self, domain: str, size: int = 32) -> QPixmap:
        """Get QPixmap of requested size."""
        icon = self.get_icon(domain, size)
        from PySide6.QtCore import QSize
        return icon.pixmap(QSize(size, size))

    def _trigger_async_fetch(self, domain: str) -> None:
        """Launch background worker thread to download favicon."""
        with self._cache_lock:
            if domain in self._pending_downloads:
                return
            self._pending_downloads.add(domain)

        def worker():
            try:
                # 1. Google Favicon API (primary, high reliability, transparent PNG)
                url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DigitalWellbeing/4.1.0"},
                )
                data = None
                try:
                    with urllib.request.urlopen(req, timeout=3.0) as resp:
                        if resp.status == 200:
                            data = resp.read()
                except Exception:
                    data = None

                # 2. DuckDuckGo fallback if Google failed or returned empty
                if not data or len(data) < 100:
                    try:
                        ddg_url = f"https://icons.duckduckgo.com/ip3/{domain}.ico"
                        req2 = urllib.request.Request(
                            ddg_url,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DigitalWellbeing/4.1.0"},
                        )
                        with urllib.request.urlopen(req2, timeout=3.0) as resp2:
                            if resp2.status == 200:
                                data = resp2.read()
                    except Exception:
                        data = None

                if data and len(data) > 100:
                    # Save to disk cache
                    disk_file = self._cache_dir / f"{domain}.png"
                    try:
                        with open(disk_file, "wb") as f:
                            f.write(data)
                    except Exception as e:
                        logger.debug("Failed to write favicon cache for %s: %s", domain, e)

                    # Create QPixmap and QIcon
                    pix = QPixmap()
                    if pix.loadFromData(data) and not pix.isNull():
                        icon = QIcon(pix)
                        with self._cache_lock:
                            self._memory_cache[domain] = icon
                        # Emit on Qt signal thread
                        self._signals.icon_ready.emit(domain, icon)
            except Exception as exc:
                logger.debug("WebsiteIconProvider error fetching %s: %s", domain, exc)
            finally:
                with self._cache_lock:
                    self._pending_downloads.discard(domain)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _create_letter_avatar(self, domain: str, size: int) -> QIcon:
        """Create a rounded squircle icon with the first letter of the domain."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # Deterministic color from domain name
        hash_val = int(hashlib.md5(domain.encode("utf-8")).hexdigest(), 16)
        bg_hex = _AVATAR_PALETTE[hash_val % len(_AVATAR_PALETTE)]

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded background
        painter.setBrush(QColor(bg_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        radius = size * 0.28
        painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

        # Draw character
        first_char = domain[0].upper() if domain and domain != "?" else "W"
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", int(size * 0.48), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, first_char)
        painter.end()

        return QIcon(pixmap)
