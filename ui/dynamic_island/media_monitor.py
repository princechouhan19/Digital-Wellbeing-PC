"""
media_monitor.py — Real-time Windows Media Playback, Album Art & Synchronized Lyrics Engine.
Ported and enhanced for PySide6 & Digital Wellbeing.
"""
from __future__ import annotations

import asyncio
import datetime
import io
import re
from typing import Optional

from PIL import Image
from PySide6.QtCore import QThread, Signal
import requests


class MediaMonitor(QThread):
    media_updated = Signal(str, str, str, str, bytes, float, float)
    # args: (status, title, artist, accent_color_hex, thumb_bytes, position_sec, duration_sec)
    lyrics_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.manager = None
        self.current_session = None
        self.lyrics: list[tuple[float, str]] = []
        self.last_lyric_sent = ""
        self.current_title = ""
        self.current_artist = ""
        self.last_state = ""

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.monitor_media())
        except Exception as e:
            pass

    async def monitor_media(self):
        try:
            from winrt.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as SM,
            )
            self.manager = await SM.request_async()
            await self.update_media_info()
            self.manager.add_sessions_changed(self.on_sessions_changed)
            self.subscribe_to_current_session()
        except Exception:
            return

        while self._is_running:
            await self.check_lyric_sync()
            await asyncio.sleep(0.05)

    async def check_lyric_sync(self):
        if not self.current_session or not self.lyrics:
            return
        try:
            timeline = await self.loop.run_in_executor(None, self.get_safe_timeline)
            if not timeline:
                return

            now = datetime.datetime.now(datetime.timezone.utc)
            last_updated = timeline.last_updated_time
            pos_base = timeline.position.total_seconds()
            delta = (now - last_updated).total_seconds()
            pos_sec = pos_base + delta

            current_line = ""
            for ts, text in self.lyrics:
                if pos_sec >= ts:
                    current_line = text
                else:
                    break

            if current_line != self.last_lyric_sent:
                self.last_lyric_sent = current_line
                self.lyrics_updated.emit(current_line)
        except Exception:
            pass

    def get_safe_timeline(self):
        try:
            if self.current_session:
                return self.current_session.get_timeline_properties()
        except Exception:
            pass
        return None

    def subscribe_to_current_session(self):
        try:
            new_session = self.manager.get_current_session()
            if not new_session:
                sessions = self.manager.get_sessions()
                if sessions:
                    new_session = sessions[0]

            if self.current_session and new_session:
                if getattr(self.current_session, "source_app_user_model_id", None) == getattr(new_session, "source_app_user_model_id", None):
                    return

            self.current_session = new_session
            if self.current_session:
                self.current_session.add_media_properties_changed(self.on_properties_changed)
                self.current_session.add_playback_info_changed(self.on_playback_changed)
                try:
                    self.current_session.add_timeline_properties_changed(self.on_playback_changed)
                except Exception:
                    pass
        except Exception:
            self.current_session = None

    def on_sessions_changed(self, sender, args):
        if self.loop and self._is_running:
            self.subscribe_to_current_session()
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    def on_properties_changed(self, sender, args):
        if self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    def on_playback_changed(self, sender, args):
        if self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(self.update_media_info(), self.loop)

    async def update_media_info(self):
        try:
            if not self.current_session:
                self.subscribe_to_current_session()
                if not self.current_session:
                    self.media_updated.emit("Idle", "", "", "#000000", b"", 0.0, 0.0)
                    return

            info = await self.loop.run_in_executor(None, self.get_safe_playback_info)
            if not info:
                self.current_session = None
                self.media_updated.emit("Idle", "", "", "#000000", b"", 0.0, 0.0)
                return

            status = int(info.playback_status)
            # Status 4 = Playing, 5 = Paused
            state_str = "Idle"
            if status == 4:
                state_str = "Playing"
            elif status == 5:
                state_str = "Paused"

            if state_str in ("Playing", "Paused"):
                props = await self.current_session.try_get_media_properties_async()
                title = props.title if props and props.title else "Unknown Title"
                artist = props.artist if props and props.artist else ""
                accent_color = "#38BDF8"
                image_data = b""

                if props and props.thumbnail:
                    try:
                        from winrt.windows.storage.streams import DataReader
                        thumb_stream = await props.thumbnail.open_read_async()
                        reader = DataReader(thumb_stream.get_input_stream_at(0))
                        await reader.load_async(thumb_stream.size)
                        buffer = reader.read_buffer(thumb_stream.size)
                        image_data = bytes(buffer)

                        # Extract dominant color using PIL
                        image = Image.open(io.BytesIO(image_data))
                        image = image.resize((32, 32))
                        colors = image.getcolors(32 * 32)
                        filtered = [c for c in colors if sum(c[1][:3]) > 60 and sum(c[1][:3]) < 680]
                        if filtered:
                            dominant = max(filtered, key=lambda x: x[0])[1]
                            accent_color = f"#{dominant[0]:02x}{dominant[1]:02x}{dominant[2]:02x}"
                        else:
                            avg = image.resize((1, 1)).getpixel((0, 0))
                            accent_color = f"#{avg[0]:02x}{avg[1]:02x}{avg[2]:02x}"
                    except Exception:
                        pass

                # Timeline
                position_sec = 0.0
                duration_sec = 0.0
                try:
                    timeline = self.current_session.get_timeline_properties()
                    if timeline:
                        position_sec = timeline.position.total_seconds()
                        duration_sec = timeline.end_time.total_seconds()
                except Exception:
                    pass

                if (state_str != self.last_state or title != self.current_title or artist != self.current_artist):
                    self.current_title = title
                    self.current_artist = artist
                    self.last_state = state_str
                    self.lyrics = []
                    self.last_lyric_sent = ""
                    self.lyrics_updated.emit("")
                    if title and title != "Unknown Title":
                        asyncio.create_task(self.fetch_lyrics(artist, title))

                self.media_updated.emit(state_str, title, artist, accent_color, image_data, position_sec, duration_sec)
            else:
                if self.last_state != "Idle":
                    self.current_title = ""
                    self.current_artist = ""
                    self.last_state = "Idle"
                    self.lyrics = []
                    self.media_updated.emit("Idle", "", "", "#000000", b"", 0.0, 0.0)
        except Exception:
            self.current_session = None

    def get_safe_playback_info(self):
        try:
            if self.current_session:
                return self.current_session.get_playback_info()
        except Exception:
            pass
        return None

    async def fetch_lyrics(self, artist: str, title: str):
        if not artist or not title:
            return

        def do_fetch():
            try:
                clean_title = re.sub(r"\(.*?\)|\[.*?\]", "", title).strip()
                url = "https://lrclib.net/api/get"
                params = {"artist_name": artist, "track_name": clean_title}
                resp = requests.get(url, params=params, timeout=4)
                if resp.status_code == 200:
                    data = resp.json()
                    lrc = data.get("syncedLyrics")
                    if lrc:
                        return self.parse_lrc(lrc)
            except Exception:
                pass
            return []

        lyrics_result = await self.loop.run_in_executor(None, do_fetch)
        if lyrics_result:
            self.lyrics = lyrics_result

    @staticmethod
    def parse_lrc(lrc_text: str) -> list[tuple[float, str]]:
        parsed = []
        for line in lrc_text.splitlines():
            m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)", line)
            if m:
                mins = float(m.group(1))
                secs = float(m.group(2))
                txt = m.group(3).strip()
                parsed.append((mins * 60 + secs, txt))
        return sorted(parsed, key=lambda x: x[0])

    def stop(self):
        self._is_running = False
        self.wait(500)
