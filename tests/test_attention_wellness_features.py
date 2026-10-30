"""
Tests for the Advanced Attention & Wellness features:
  * granular URL rules + loopback extension bridge
  * Focus Fragmentation Index / Flow Continuity analytics
  * Circadian display schedule
  * Strict lockout persistence and guards
  * redesigned Focus page structure
"""
from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    db_path = tmp_path / "attention.db"
    Repository.set_db_path_override(db_path)
    repo = Repository()
    try:
        yield repo
    finally:
        try:
            repo.close()
        except Exception:
            pass
        Repository.set_db_path_override(None)


# ── URL rules ───────────────────────────────────────────────────────────────


def test_url_rule_engine_specificity_and_subdomains(temp_repo):
    from protection.url_rules import UrlRuleEngine

    engine = UrlRuleEngine(temp_repo)
    engine.save([])
    assert engine.add("youtube.com/shorts", "block", "Shorts") is not None
    assert engine.add("reddit.com/r/programming", "allow", "Programming") is not None
    assert engine.add("not a host", "block") is None

    rules = engine.load()
    shorts = UrlRuleEngine.decide("https://www.youtube.com/shorts/abc?x=1", "allow", rules)
    assert shorts.action == "block"
    assert shorts.matched_rule == "youtube.com/shorts"

    watch = UrlRuleEngine.decide("https://youtube.com/watch?v=1", "allow", rules)
    assert watch.action == "allow"
    assert watch.matched_rule is None

    programming = UrlRuleEngine.decide(
        "https://old.reddit.com/r/programming/comments/1", "block", rules
    )
    assert programming.action == "allow"

    r_all = UrlRuleEngine.decide("https://reddit.com/r/all", "block", rules)
    assert r_all.action == "block"


def test_focus_check_url_combines_domain_default_and_rules(temp_repo):
    from protection.focus_manager import FocusManager

    fm = FocusManager(temp_repo)
    fm.save_mode_websites("custom", ["reddit.com"])
    fm.add_url_rule("reddit.com/r/programming", "allow")
    fm._mode = "custom"
    fm._is_active = True
    try:
        decision = fm.check_url("https://reddit.com/r/programming/comments/1")
        assert decision["action"] == "allow"
        blocked = fm.check_url("https://reddit.com/r/all")
        assert blocked["action"] == "block"
        # A completely unrelated site is allowed unless the mode blocks it.
        assert fm.check_url("https://example.com/docs")["action"] == "allow"
    finally:
        fm._is_active = False


def test_extension_bridge_round_trip(temp_repo):
    from protection.extension_bridge import ExtensionBridge

    bridge = ExtensionBridge.instance()
    # Force an ephemeral port for the test.
    temp_repo.set_setting("extension_bridge_port", "0")
    bridge.set_decision_provider(lambda url: {"action": "block", "reason": "unit", "domain": "x.com"})
    assert bridge.start() is True
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{bridge.port}/v1/check",
            data=json.dumps({"url": "https://x.com/a"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-DW-Token": bridge.token},
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            payload = json.loads(response.read())
        assert payload["action"] == "block"
        assert bridge.latest_url("extension") == "https://x.com/a"
        with urllib.request.urlopen(f"http://127.0.0.1:{bridge.port}/v1/health", timeout=3) as response:
            health = json.loads(response.read())
        assert health["ok"] is True

        # Test /v1/rules
        bridge.set_rules_provider(lambda: {
            "focus_active": True,
            "mode": "study",
            "seconds_remaining": 600,
            "session_total_seconds": 1500,
            "rules": [{"pattern": "youtube.com/shorts", "action": "block"}],
            "blocked_domains": ["reddit.com"],
            "revision": 42,
        })
        rules_req = urllib.request.Request(
            f"http://127.0.0.1:{bridge.port}/v1/rules",
            headers={"X-DW-Token": bridge.token},
        )
        with urllib.request.urlopen(rules_req, timeout=3) as response:
            rules_payload = json.loads(response.read())
        assert rules_payload["focus_active"] is True
        assert rules_payload["revision"] == 42
        assert len(rules_payload["rules"]) == 1

        # Test /v1/pair with code
        code = bridge.enable_pairing(duration_s=60)
        pair_req = urllib.request.Request(
            f"http://127.0.0.1:{bridge.port}/v1/pair",
            data=json.dumps({"code": code}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(pair_req, timeout=3) as response:
            pair_payload = json.loads(response.read())
        assert pair_payload["ok"] is True
        assert pair_payload["token"] == bridge.token

        # Test /v1/heartbeat
        hb_req = urllib.request.Request(
            f"http://127.0.0.1:{bridge.port}/v1/heartbeat",
            data=json.dumps({"url": "https://docs.python.org", "browser": "chrome.exe", "title": "Docs"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-DW-Token": bridge.token},
        )
        with urllib.request.urlopen(hb_req, timeout=3) as response:
            hb_payload = json.loads(response.read())
        assert hb_payload["ok"] is True
        assert hb_payload["focus_active"] is True
        assert bridge.latest_url("chrome.exe") == "https://docs.python.org"
    finally:
        bridge.stop()


# ── Flow analytics ──────────────────────────────────────────────────────────


def test_focus_fragmentation_and_flow_continuity(temp_repo):
    from analytics.engine import AnalyticsEngine

    base = datetime(2026, 10, 20, 9, 0)
    rows = [
        ("code.exe", base, 25 * 60, AppCategory.PROGRAMMING),
        ("code.exe", base + timedelta(minutes=25, seconds=60), 25 * 60, AppCategory.PROGRAMMING),
        ("chrome.exe", base + timedelta(minutes=52), 8 * 60, AppCategory.BROWSER),
        ("notion.exe", base + timedelta(minutes=61), 30 * 60, AppCategory.PRODUCTIVITY),
    ]
    for name, start, duration, category in rows:
        temp_repo.insert_session(
            AppSession(
                process_name=name,
                window_title="test",
                start_time=start,
                end_time=start + timedelta(seconds=duration),
                duration_s=duration,
                category=category,
                is_idle=False,
            )
        )

    engine = AnalyticsEngine()
    fragmentation = engine.get_focus_fragmentation(date(2026, 10, 20))
    assert fragmentation["total_switches"] == 4
    assert fragmentation["peak_hour"] == "09:00"
    assert fragmentation["fragmentation_index"] > 0

    flow = engine.get_flow_analytics(days=1, end_date=date(2026, 10, 20))
    assert flow["count"] == 1
    longest = flow["longest"]
    assert longest is not None
    assert longest["primary_app"] == "code.exe"
    assert longest["duration_s"] >= 45 * 60


def test_flow_breaks_on_non_productive_category(temp_repo):
    from analytics.engine import AnalyticsEngine

    base = datetime(2026, 10, 21, 10, 0)
    for name, start, duration, category in (
        ("code.exe", base, 30 * 60, AppCategory.PROGRAMMING),
        ("chrome.exe", base + timedelta(minutes=30), 30 * 60, AppCategory.BROWSER),
        ("code.exe", base + timedelta(minutes=60), 30 * 60, AppCategory.PROGRAMMING),
    ):
        temp_repo.insert_session(
            AppSession(
                process_name=name,
                window_title="test",
                start_time=start,
                end_time=start + timedelta(seconds=duration),
                duration_s=duration,
                category=category,
                is_idle=False,
            )
        )
    flow = AnalyticsEngine().get_flow_analytics(days=1, end_date=date(2026, 10, 21))
    assert flow["count"] == 0


# ── Circadian ───────────────────────────────────────────────────────────────


def test_circadian_schedule_phases():
    from protection.circadian import compute_state

    def at(hour, minute=0):
        return compute_state(datetime(2026, 10, 22, hour, minute), "23:00", "06:00", 90, 3400)

    assert at(12).phase == "day"
    assert at(12).kelvin == 6500
    assert at(21, 30).phase == "winding_down"
    assert at(22, 30).kelvin < 6500
    assert at(23, 30).phase == "night"
    assert at(2).phase == "night"
    assert at(6, 30).phase == "day"


def test_circadian_controller_applies_and_restores(temp_repo, qapp):
    from protection.circadian import CircadianController
    from settings.manager import SettingsManager

    sm = SettingsManager()
    sm.circadian_enabled = True
    sm.bedtime_start = "23:00"
    sm.bedtime_end = "06:00"
    sm.circadian_lead_minutes = 90
    sm.circadian_target_kelvin = 3400

    class FakeApplier:
        def __init__(self):
            self.applied = []
            self.restored = 0

        def apply_kelvin(self, kelvin):
            self.applied.append(kelvin)
            return True

        def restore(self):
            self.restored += 1

    applier = FakeApplier()
    controller = CircadianController(
        settings=sm,
        applier=applier,
        clock=lambda: datetime(2026, 10, 22, 23, 30),
    )
    state = controller.tick()
    assert state.phase == "night"
    assert applier.applied and applier.applied[-1] == 3400

    sm.circadian_enabled = False
    controller.tick()
    assert applier.restored >= 1


def test_circadian_settings_clamped(temp_repo):
    from settings.manager import SettingsManager

    sm = SettingsManager()
    sm.circadian_lead_minutes = 9999
    sm.circadian_target_kelvin = 9999
    assert sm.circadian_lead_minutes == 360
    assert sm.circadian_target_kelvin == 6500


# ── Strict lockout ─────────────────────────────────────────────────────────


def test_lockout_denies_stop_and_persists(temp_repo):
    from protection.focus_manager import FocusManager

    fm = FocusManager(temp_repo)
    fm._pin_manager.set_pin("1234")
    fm.save_mode_websites("custom", [])
    assert fm.start_focus(2, lockout=True) is True
    try:
        assert fm.is_lockout is True
        assert fm.is_strict is True
        assert fm.stop_focus() is False
        assert fm.stop_focus_after_pin_dialog() is False

        raw = temp_repo.get_setting("focus_active_session")
        assert raw and json.loads(raw)["lockout"] is True

        # A second manager restores the same session (simulating relaunch).
        restored = FocusManager(temp_repo)
        assert restored.is_active is True
        assert restored.is_lockout is True
        assert restored.seconds_remaining > 0
        restored._seconds_remaining = 0
        assert restored.stop_focus() is True
    finally:
        fm._seconds_remaining = 0
        fm.stop_focus()
        temp_repo.set_setting("focus_active_session", "")


def test_expired_persisted_session_is_cleared(temp_repo):
    from protection.focus_manager import FocusManager

    temp_repo.set_setting(
        "focus_active_session",
        json.dumps(
            {
                "mode": "custom",
                "minutes": 1,
                "lockout": True,
                "deadline_epoch": 1,
            }
        ),
    )
    fm = FocusManager(temp_repo)
    assert fm.is_active is False
    assert temp_repo.get_setting("focus_active_session") in ("", None)


# ── Redesigned Focus page ──────────────────────────────────────────────────


def test_extension_manifest_is_valid():
    extension = Path(__file__).resolve().parent.parent / "assets" / "browser_extension"
    manifest = json.loads((extension / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    assert (extension / manifest["background"]["service_worker"]).is_file()
    assert (extension / manifest["options_page"]).is_file()
    assert (extension / "blocked.html").is_file()


def test_focus_page_is_split_into_sections(temp_repo, qapp):
    from ui.pages.wellbeing import WellbeingPage

    page = WellbeingPage()
    try:
        timer = page._focus_timer
        assert timer.objectName() == "focus_suite_root"
        assert timer._guardrail_stack.count() == 3
        assert len(timer._guardrail_tabs) == 3
        assert timer._lockout_switch is not None
        assert timer._manage_rules_btn is not None
        assert timer._strict_switch is not None
    finally:
        page.close()
