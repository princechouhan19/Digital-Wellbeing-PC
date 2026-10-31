"""
test_ambient_notch.py — Unit and integration tests for the smart Dynamic Island Notch.
"""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.widgets.ambient_notch import AmbientNotch


@pytest.fixture
def notch(qtbot):
    widget = AmbientNotch()
    qtbot.addWidget(widget)
    widget.show()
    return widget


def test_notch_default_idle_state(notch):
    # Ensure idle state by resetting media detection
    notch._on_media_monitor_updated(
        status="Stopped",
        title="",
        artist="",
        accent_color="#38BDF8",
        thumb_bytes=b"",
        pos=0.0,
        dur=0.0,
    )
    # When no music is playing and no active task, should be in IDLE mode showing Time & Battery
    assert notch._current_mode == AmbientNotch.MODE_IDLE
    assert notch._compact_stack.currentIndex() == 0
    assert notch._canvas._show_visualizer_dots is False
    # Verify no emojis in battery text
    assert "⚡" not in notch._lbl_idle_battery.text()


def test_notch_task_mode(notch):
    # Simulate an active focus session
    notch._fm._seconds_remaining = 1500  # 25:00
    notch._on_focus_tick(1500)
    notch._on_focus_state_changed(True)

    assert notch._current_mode == AmbientNotch.MODE_TASK
    assert notch._compact_stack.currentIndex() == 1
    assert notch._lbl_task_timer.text() == "25:00"
    assert notch._canvas._show_visualizer_dots is True


def test_notch_media_monitor_updated(notch):
    # Simulate MediaMonitor delivering real song info
    notch._on_media_monitor_updated(
        status="Playing",
        title="Midnight City",
        artist="M83",
        accent_color="#A855F7",
        thumb_bytes=b"",
        pos=30.0,
        dur=240.0,
    )

    assert notch._current_mode == AmbientNotch.MODE_MEDIA
    assert notch._compact_stack.currentIndex() == 2
    assert "Midnight City" in notch._media_title_lbl.text()
    assert notch._media_accent_color == "#A855F7"
    assert notch._btn_play._kind == "pause"

    # Simulate media stopped
    notch._on_media_monitor_updated("Idle", "", "", "#000000", b"", 0.0, 0.0)
    assert notch._current_mode in (AmbientNotch.MODE_IDLE, AmbientNotch.MODE_TASK)


def test_notch_key_lock_hud(notch):
    # Simulate Caps Lock press
    notch._on_key_lock_changed("Caps Lock", True)
    assert notch._current_mode == AmbientNotch.MODE_VOLUME  # HUD index
    assert notch._hud_title_lbl.text() == "Caps Lock"
    assert notch._hud_sub_lbl.text() == "ON"


def test_notch_perf_and_weather(notch):
    notch._on_perf_updated({"cpu": 42.0, "ram": 58.0, "disk": 70.0, "down": 1024, "up": 512})
    notch._on_weather_updated({"city": "Varanasi", "temp": "28°C", "desc": "Mainly Clear", "wind": "12 km/h"})
    assert notch._perf_data["cpu"] == 42.0
    assert notch._weather_data["temp"] == "28°C"


def test_notch_expansion(notch):
    assert notch._is_expanded is False
    notch.set_expanded(True)
    assert notch._is_expanded is True
    assert not notch._expanded_container.isHidden()

    notch.set_expanded(False)
    assert notch._is_expanded is False


def test_notch_long_title_overflow_handling(notch):
    # Simulate a very long YouTube video title (100+ chars)
    long_title = "💥 COMING 💥 WITH A NEW FORM 👑 FREE FIRE ESPORTS TOURNAMENT HIGHLIGHTS ⚡ | BY FOZY.TAUKEER • NeX TAUKEER"
    notch._on_media_monitor_updated(
        status="Playing",
        title=long_title,
        artist="YouTube Channel",
        accent_color="#FF0000",
        thumb_bytes=b"",
        pos=10.0,
        dur=300.0,
    )
    # Compact title must be cleanly elided
    assert "…" in notch._media_title_lbl.text() or len(notch._media_title_lbl.text()) <= 60
    assert notch.REST_WIDTH_MEDIA <= 280
    assert notch._media_title_lbl.maximumWidth() <= 150


def test_notch_wheel_scroll_widgets(notch):
    # Scrolling wheel flips between interactive panels
    initial_feat = notch.features[notch.current_feature_index]
    # Simulate wheel scroll event with delta
    notch.current_feature_index = (notch.current_feature_index + 1) % len(notch.features)
    notch._update_expanded_panel_visibility()
    new_feat = notch.features[notch.current_feature_index]
    assert new_feat != initial_feat
    assert notch.basics_panel is not None
