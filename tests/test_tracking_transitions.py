from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from tracker.transitions import (
    TrackingTransition,
    _select_transition_python,
    select_transition,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
    / "tracking_transition_cases.tsv"
)


def _cases():
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        assert len(fields) == 7, f"malformed transition fixture row: {line!r}"
        flags = tuple(field == "1" for field in fields[:5])
        duration_ms = int(fields[5])
        expected = int(fields[6])
        yield flags, duration_ms, expected


def test_python_transition_reference_matches_shared_corpus():
    for flags, duration_ms, expected in _cases():
        actual = _select_transition_python(*flags, session_duration_s=duration_ms / 1000.0)
        assert int(actual) == expected


def test_selected_transition_backend_matches_shared_corpus():
    # If the optional native library is enabled, this exercises its transition
    # function; otherwise the public selector safely uses the Python reference.
    for flags, duration_ms, expected in _cases():
        actual = select_transition(*flags, session_duration_s=duration_ms / 1000.0)
        assert int(actual) == expected


def test_unknown_native_action_falls_back_to_python(monkeypatch):
    import tracker.transitions as transitions

    monkeypatch.setattr(transitions, "_rust_decide_transition", lambda *args: 99)
    assert select_transition(False, False, False, False, False) == TrackingTransition.START


def _manager_for_tick(
    monkeypatch,
    *,
    age_s,
    category,
    process_name="chrome.exe",
    fullscreen=False,
    idle_s=0.0,
):
    import tracker.manager as manager_module
    from core.constants import AppCategory
    from tracker.foreground import ForegroundApp
    from tracker.manager import TrackingManager

    assert isinstance(category, AppCategory)
    current = ForegroundApp(
        process_name=process_name,
        exe_path="C:/app.exe",
        pid=100,
        window_title="Before",
        hwnd=10,
    )
    foreground = ForegroundApp(
        process_name=process_name,
        exe_path="C:/app.exe",
        pid=100,
        window_title="After",
        hwnd=10,
        is_fullscreen=fullscreen,
    )
    effects = []
    manager = object.__new__(TrackingManager)
    manager._tick_count = 0
    manager._last_tick_time = datetime.now()
    manager._watcher = SimpleNamespace(available=True)
    manager._fg_dirty = True
    manager._last_fg_query_mono = 0.0
    manager._fg_query_count = 0
    manager._current_app = current
    manager._session_start = datetime.now() - timedelta(seconds=age_s)
    manager._current_session_id = 37
    manager._current_is_idle = False
    manager._current_category = category
    manager._current_is_fullscreen = False
    manager._current_game_reason = ""
    manager._current_launcher_reason = ""
    manager._current_transition_reason = ""
    manager._current_website_url = ""
    manager._current_website_session_id = None
    manager._current_website_start = None
    manager._last_heartbeat = 0.0
    manager._consecutive_errors = 0
    manager._fg_missing = False
    manager._grace_app = None
    manager._grace_timer = None
    manager._idle_threshold_s = 300.0
    manager._media_engine = SimpleNamespace(
        is_playing=False,
        current=SimpleNamespace(app_name=""),
    )
    manager._on_active_tick_callbacks = []
    manager._debug_enabled = False
    manager._repo = SimpleNamespace(
        update_session_title=lambda session_id, title: effects.append(("title", session_id, title))
    )
    manager._sample_idle_seconds = lambda _now: idle_s
    manager._dispatch_active_tick = lambda *_args: None
    manager._end_current_session = lambda **kwargs: effects.append(
        ("end", kwargs.get("reason"))
    )
    manager._end_website_session = lambda *_args: None
    manager._start_session = lambda _app, _now, _idle, reason="": effects.append(
        ("start", reason)
    )
    manager._start_website_session = lambda *_args: None
    manager._maybe_heartbeat = lambda *_args: None
    monkeypatch.setattr(
        manager_module, "get_foreground_app", lambda _last=None: foreground
    )
    monkeypatch.setattr(
        manager_module.TrackingAuditor,
        "log_poll_event",
        lambda *_args, **_kwargs: None,
    )
    return manager, foreground, effects


def test_manager_applies_title_split_transition(monkeypatch):
    from core.constants import AppCategory

    manager, _foreground, effects = _manager_for_tick(
        monkeypatch, age_s=3.0, category=AppCategory.BROWSER
    )
    manager._tick(1.0)
    assert ("end", "title_split") in effects
    assert ("start", "title_split") in effects


def test_manager_keeps_short_and_fullscreen_game_title_updates_in_place(monkeypatch):
    from core.constants import AppCategory

    short_manager, short_foreground, short_effects = _manager_for_tick(
        monkeypatch, age_s=1.0, category=AppCategory.BROWSER
    )
    short_manager._tick(1.0)
    assert not any(action in {"end", "start"} for action, *_ in short_effects)
    assert short_manager._current_app is short_foreground
    assert ("title", 37, "After") in short_effects

    game_manager, game_foreground, game_effects = _manager_for_tick(
        monkeypatch, age_s=10.0, category=AppCategory.GAMING, fullscreen=True
    )
    game_manager._tick(1.0)
    assert not any(action in {"end", "start"} for action, *_ in game_effects)
    assert game_manager._current_app is game_foreground
    assert ("title", 37, "After") in game_effects
