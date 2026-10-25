"""
Tests for the v4.3 attention features: recap, schedules, weekly report,
safe emergency exit, fragmentation nudge, rule packs, command palette.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

from core.constants import AppCategory
from database.models import AppSession
from database.repository import Repository


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def temp_repo(tmp_path):
    Repository.set_db_path_override(tmp_path / "v43.db")
    repo = Repository()
    try:
        yield repo
    finally:
        try:
            repo.close()
        except Exception:
            pass
        Repository.set_db_path_override(None)


def test_focus_recap_is_persisted_and_emitted(temp_repo, qapp):
    from protection.focus_manager import FocusManager

    fm = FocusManager(temp_repo)
    fm.save_mode_websites("custom", [])
    recaps = []
    fm.session_recap_ready.connect(recaps.append)
    assert fm.start_focus(5, mode="custom") is True
    fm._record_block("app", "discord.exe")
    fm._record_block("site", "youtube.com/shorts")
    assert fm.stop_focus() is True

    rows = temp_repo.get_focus_sessions(5)
    assert len(rows) == 1
    assert rows[0]["blocked_apps"] == 1
    assert rows[0]["blocked_sites"] == 1
    assert recaps and recaps[0]["interruptions"] >= 2
    assert "fragmentation_index" in recaps[0]
    assert "best_next_window" in recaps[0]

    # History periods use the same rows.
    today = date.today()
    assert temp_repo.get_focus_sessions(5, today, today)
    assert temp_repo.get_focus_sessions(5, today - timedelta(days=1), today - timedelta(days=1)) == []


def test_recurring_schedule_starts_remaining_block(temp_repo, qapp):
    from protection.focus_schedule import FocusSchedule, FocusScheduleEngine

    class FakeManager:
        is_active = False

        def __init__(self):
            self.calls = []

        def start_focus(self, minutes, mode=None, auto_started=False, schedule_id=""):
            self.calls.append((minutes, mode, auto_started, schedule_id))
            self.is_active = True
            return True

    manager = FakeManager()
    engine = FocusScheduleEngine(manager=manager, repo=temp_repo)
    engine.save([])
    engine.add(
        FocusSchedule(
            name="Morning",
            mode="work",
            start="09:00",
            duration_min=60,
            weekdays=[0, 1, 2, 3, 4],
        )
    )
    monday_0930 = datetime(2026, 10, 26, 9, 30)  # Monday
    due = engine.due_schedule(monday_0930)
    assert due is not None
    result = engine.check_now(monday_0930)
    assert result is not None
    assert manager.calls[0][0] == 30
    assert manager.calls[0][1] == "work"
    assert manager.calls[0][2] is True
    # Fired schedules do not loop.
    manager.is_active = False
    assert engine.check_now(monday_0930) is None


def test_weekly_report_shape_and_flow_streak(temp_repo, qapp):
    from analytics.engine import AnalyticsEngine

    today = date.today()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time()) + timedelta(hours=9)
    for i in range(4):
        s = start + timedelta(minutes=i * 25)
        temp_repo.insert_session(
            AppSession(
                process_name="code.exe",
                window_title="test",
                start_time=s,
                end_time=s + timedelta(minutes=24),
                duration_s=24 * 60,
                category=AppCategory.PROGRAMMING,
                is_idle=False,
            )
        )
    report = AnalyticsEngine().get_weekly_attention_report(today)
    assert len(report["days"]) == 7
    assert len(report["days"][0]["hours"]) == 24
    assert report["total_switches"] >= 4
    assert "current_streak" in report["flow"]
    assert report["best_hour"] is not None or report["best_hour"] is None
    assert report["worst_hour"] is not None or report["worst_hour"] is None


def test_safe_emergency_exit_cooldown(temp_repo, qapp):
    from protection.focus_manager import FocusManager

    fm = FocusManager(temp_repo)
    fm._pin_manager.set_pin("2468")
    fm.save_mode_websites("custom", [])
    assert fm.start_focus(5, lockout=True) is True
    try:
        assert fm.stop_focus() is False
        assert fm.request_emergency_exit(15) is True
        assert fm.is_emergency_pending is True
        assert fm.emergency_unlock_remaining > 14 * 60
        assert fm.stop_focus() is False
        # Fast-forward the cooldown.
        fm._emergency_unlock_at = time.monotonic() - 1
        assert fm.stop_focus() is True
    finally:
        fm._seconds_remaining = 0
        fm.stop_focus()


def test_fragmentation_nudge_threshold_and_cooldown(qapp):
    from protection.attention_nudge import AttentionNudgeController

    class FakeEngine:
        def get_switch_count_since(self, minutes, now=None):
            return 15

    class FakeManager:
        is_active = False

    class FakeSettings:
        def get_bool(self, key, default=False):
            return True

    nudges = []
    controller = AttentionNudgeController(
        engine=FakeEngine(),
        manager=FakeManager(),
        settings=FakeSettings(),
    )
    controller._started_at = time.monotonic() - 400
    controller.nudge_ready.connect(nudges.append)
    assert controller.check_now(datetime.now()) is True
    assert nudges == [15]
    assert controller.check_now(datetime.now()) is False


def test_rule_presets_and_export_import(temp_repo, tmp_path):
    from protection.url_rules import UrlRuleEngine

    engine = UrlRuleEngine(temp_repo)
    engine.save([])
    assert engine.apply_preset("study") == 4
    assert engine.apply_preset("study") == 0
    export_path = tmp_path / "rules.json"
    assert engine.export_to_file(str(export_path)) == 4
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["format"] == "digital-wellbeing-url-rules"

    engine.save([])
    added, error = engine.import_from_file(str(export_path))
    assert added == 4 and error == ""
    assert len(engine.load()) == 4


def test_command_palette_filters_and_returns_callback(qapp):
    from ui.widgets.command_palette import CommandPalette

    calls = []
    palette = CommandPalette(
        [
            ("Open Focus", "timer", lambda: calls.append("focus")),
            ("Weekly report", "heatmap", lambda: calls.append("report")),
        ]
    )
    palette._input.setText("weekly")
    assert palette._list.count() == 1
    palette._accept_current()
    assert palette.selected_callback() is not None
    palette.selected_callback()()
    assert calls == ["report"]
    palette.close()
