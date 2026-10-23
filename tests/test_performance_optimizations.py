"""
Regression tests for the v4.2 performance work:
  * event-driven foreground watcher + throttled safety polling
  * idle controller-probe throttling
  * coalesced/cached UIA address-bar fallback
  * memoised browser-title and adult-content classification
  * SQLite mmap + composite index tuning
  * lazy Qt page instantiation
"""
from __future__ import annotations

import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from core.constants import AppCategory
from tracker.foreground import ForegroundApp


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ── Win32 event watcher ──────────────────────────────────────────────────────


def test_watcher_falls_back_when_disabled(monkeypatch):
    monkeypatch.setenv("DW_DISABLE_WINEVENT_HOOK", "1")
    from tracker.win_events import ForegroundEventWatcher

    watcher = ForegroundEventWatcher()
    assert watcher.start() is False
    assert watcher.available is False
    # Ordinary wake semantics still work in the fallback mode.
    assert watcher.wait(0.01) is False
    watcher.notify("test")
    assert watcher.wait(0.1) is True
    assert watcher.wait(0.01) is False
    watcher.stop()


def test_watcher_notify_lost_wakeup_regression():
    from tracker.win_events import ForegroundEventWatcher

    watcher = ForegroundEventWatcher()
    watcher.notify("before-wait")
    # An event that arrives *before* the consumer blocks must not be dropped.
    assert watcher.wait(0.1) is True
    assert watcher.wait(0.01) is False


# ── Tracking loop throttling ────────────────────────────────────────────────


def _make_tracker():
    from tracker.manager import TrackingManager

    return TrackingManager()


def _prime_tracker(manager, app: ForegroundApp):
    manager._watcher._available = True
    manager._fg_dirty = False
    manager._last_fg_query_mono = time.monotonic()
    manager._current_app = app
    manager._current_category = AppCategory.BROWSER
    manager._current_is_idle = False
    manager._current_session_id = None
    manager._session_start = None
    manager._current_website_url = app.url
    manager._current_website_session_id = None
    manager._last_heartbeat = 0.0
    manager._on_active_tick_callbacks.clear()


def _fake_app() -> ForegroundApp:
    return ForegroundApp(
        process_name="chrome.exe",
        exe_path="C:/chrome.exe",
        pid=4242,
        window_title="Some harmless page - Google Chrome",
        hwnd=9911,
        url="example.com",
        is_fullscreen=False,
    )


def test_foreground_query_is_safety_polled(monkeypatch):
    import tracker.manager as manager_mod

    calls = []
    app = _fake_app()
    manager = _make_tracker()
    _prime_tracker(manager, app)
    manager._last_fg_query_mono = 0.0
    monkeypatch.setattr(manager_mod, "get_foreground_app", lambda last=None: calls.append(1) or app)
    monkeypatch.setattr(manager_mod, "get_idle_seconds", lambda: 0.0)

    for _ in range(5):
        manager._last_tick_time = datetime.now()
        manager._tick(1.0)

    # Event-driven mode: hooks are available, so five immediate ticks may only
    # perform the initial/safety foreground read.
    assert len(calls) == 1
    assert manager.get_performance_stats()["event_driven"] is True


def test_dirty_flag_forces_immediate_refresh(monkeypatch):
    import tracker.manager as manager_mod

    calls = []
    app = _fake_app()
    manager = _make_tracker()
    _prime_tracker(manager, app)
    manager._last_fg_query_mono = 0.0
    monkeypatch.setattr(manager_mod, "get_foreground_app", lambda last=None: calls.append(1) or app)
    monkeypatch.setattr(manager_mod, "get_idle_seconds", lambda: 0.0)

    manager._last_tick_time = datetime.now()
    manager._tick(1.0)
    assert len(calls) == 1

    manager._fg_dirty = True  # a Win32 foreground event arrived
    manager._last_tick_time = datetime.now()
    manager._tick(0.02)
    assert len(calls) == 2


def test_no_hook_mode_keeps_fast_polling(monkeypatch):
    import tracker.manager as manager_mod

    calls = []
    app = _fake_app()
    manager = _make_tracker()
    _prime_tracker(manager, app)
    manager._watcher._available = False
    manager._last_fg_query_mono = time.monotonic() - 1.0  # older than 0.5 s fallback
    monkeypatch.setattr(manager_mod, "get_foreground_app", lambda last=None: calls.append(1) or app)
    monkeypatch.setattr(manager_mod, "get_idle_seconds", lambda: 0.0)

    manager._last_tick_time = datetime.now()
    manager._tick(1.0)
    assert len(calls) == 1


# ── Idle controller probe ───────────────────────────────────────────────────


def test_controller_probe_is_throttled(monkeypatch):
    import tracker.idle as idle_mod

    probes = []
    monkeypatch.setattr(idle_mod, "_poll_controllers", lambda tick: probes.append(tick))
    monkeypatch.setattr(idle_mod, "_last_controller_probe_mono", 0.0)

    idle_mod._check_controller_activity(1000)
    idle_mod._check_controller_activity(1001)
    assert len(probes) == 1

    monkeypatch.setattr(idle_mod, "_last_controller_probe_mono", time.monotonic() - 5.0)
    idle_mod._check_controller_activity(1002)
    assert len(probes) == 2


# ── UIA address-bar cache ──────────────────────────────────────────────────


def test_uia_positive_cache_and_title_invalidation(monkeypatch):
    import tracker.browser_domain as bd

    bd.reset_uia_cache()
    calls = []
    monkeypatch.setattr(bd, "_UIA_SYNC_MODE", True)
    monkeypatch.setattr(bd, "_query_uia_domain", lambda hwnd: calls.append(hwnd) or "example.com")

    try:
        assert bd.get_active_browser_domain("chrome.exe", "Unrecognized dashboard", 42) == "example.com"
        assert bd.get_active_browser_domain("chrome.exe", "Unrecognized dashboard", 42) == "example.com"
        assert len(calls) == 1
        assert bd.get_uia_cache_stats()["hits"] == 1

        # A different title must not inherit the previous tab's domain.
        assert bd.get_active_browser_domain("chrome.exe", "Another unrecognized page", 42) == "example.com"
        assert len(calls) == 2
    finally:
        bd.reset_uia_cache()


def test_uia_negative_cache_backs_off(monkeypatch):
    import tracker.browser_domain as bd

    bd.reset_uia_cache()
    calls = []
    monkeypatch.setattr(bd, "_UIA_SYNC_MODE", True)
    monkeypatch.setattr(bd, "_query_uia_domain", lambda hwnd: calls.append(hwnd) or "")

    try:
        assert bd.get_active_browser_domain("chrome.exe", "Unresolvable page", 77) == ""
        assert bd.get_active_browser_domain("chrome.exe", "Unresolvable page", 77) == ""
        assert len(calls) == 1
        assert bd.get_uia_cache_stats()["negative_hits"] == 1
    finally:
        bd.reset_uia_cache()


def test_domain_from_title_is_memoised():
    import tracker.browser_domain as bd

    bd._extract_domain_cached.cache_clear()
    assert bd.extract_domain_from_title("YouTube - Google Chrome", "chrome.exe") == "youtube.com"
    info_before = bd._extract_domain_cached.cache_info()
    for _ in range(5):
        assert bd.extract_domain_from_title("YouTube - Google Chrome", "chrome.exe") == "youtube.com"
    info_after = bd._extract_domain_cached.cache_info()
    assert info_after.hits >= info_before.hits + 5


# ── Adult-content classifier ────────────────────────────────────────────────


def test_adult_classifier_detection_and_memoisation():
    from protection.adult_content_shield import AdultContentClassifier

    _classify = sys.modules["protection.adult_content_shield"]._classify_adult_title
    _classify.cache_clear()
    assert AdultContentClassifier.is_adult_title("porn videos - Google Chrome")[0] is True
    assert AdultContentClassifier.is_adult_title("Essex county news - Google Chrome")[0] is False
    info_before = _classify.cache_info()
    for _ in range(5):
        AdultContentClassifier.is_adult_title("porn videos - Google Chrome")
    assert _classify.cache_info().hits >= info_before.hits + 5


# ── SQLite tuning ───────────────────────────────────────────────────────────


def test_sqlite_mmap_and_composite_indexes(tmp_path):
    from database.repository import Repository

    db_path = tmp_path / "tuned.db"
    Repository.set_db_path_override(db_path)
    try:
        repo = Repository()
        conn = repo._connection()
        assert conn.execute("PRAGMA mmap_size").fetchone()[0] > 0
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000

        indexes = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        }
        assert "idx_sessions_process_start" in indexes
        assert "idx_website_domain_start" in indexes
        assert "idx_website_browser_start" in indexes

        plan = conn.execute(
            "EXPLAIN QUERY PLAN SELECT SUM(duration_s) FROM app_sessions "
            "WHERE process_name=? AND start_time>=? AND start_time<=? AND is_idle=0",
            ("chrome.exe", "2024-01-01", "2025-01-01"),
        ).fetchall()
        plan_text = " ".join(str(tuple(row)) for row in plan)
        assert "idx_sessions_process_start" in plan_text
        repo.close()
    finally:
        Repository.set_db_path_override(None)


# ── Lazy UI instantiation ───────────────────────────────────────────────────


def test_main_window_builds_only_the_landing_page(qapp):
    from tracker.manager import TrackingManager
    from ui.main_window import MainWindow

    tracker = TrackingManager()
    window = MainWindow(tracker=tracker)
    try:
        assert window._stack.count() == window._PAGE_COUNT
        assert 0 in window._pages
        assert sorted(window._pages) == [0]
        assert window.get_loaded_page("_settings_page") is None

        window._navigate(8)
        assert 8 in window._pages
        assert window.get_loaded_page("_settings_page") is window._pages[8]
        assert window._stack.count() == window._PAGE_COUNT

        # The page occupies its stable slot (Settings == index 8).
        assert window._stack.widget(8) is window._pages[8]
    finally:
        window.close()
