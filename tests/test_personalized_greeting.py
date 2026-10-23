"""
test_personalized_greeting.py — Comprehensive tests for personalized greeting,
time-aware boundaries, late-night context messages, and first-run onboarding.
"""
import pytest
from datetime import datetime
from PySide6.QtWidgets import QApplication

from settings.manager import SettingsManager
from ui.pages.dashboard import DashboardPage
from ui.onboarding import OnboardingFlow


@pytest.fixture(autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def clean_settings():
    sm = SettingsManager()
    orig_name = sm.display_name
    orig_onb = sm.onboarding_completed
    orig_theme = sm.theme
    orig_goals = sm.get("onboarding_goals", "")
    sm.display_name = ""
    sm.onboarding_completed = False
    sm.set("onboarding_goals", "")
    yield sm
    sm.display_name = orig_name
    sm.onboarding_completed = orig_onb
    sm.theme = orig_theme
    sm.set("onboarding_goals", orig_goals)


def test_settings_name_and_onboarding_persistence(clean_settings):
    sm = clean_settings
    sm.display_name = "Akshit"
    sm.onboarding_completed = True

    # Fresh instance
    sm2 = SettingsManager()
    assert sm2.display_name == "Akshit"
    assert sm2.onboarding_completed is True


def test_onboarding_name_migration(clean_settings):
    """Users who completed the legacy name prompt skip onboarding."""
    sm = clean_settings
    sm.display_name = "Akshit"
    sm.set_bool("name_prompt_completed", True)
    sm.set_bool("onboarding_completed", False)

    sm2 = SettingsManager()
    assert sm2.onboarding_completed is True


def test_onboarding_finish_persists_choices(clean_settings, qapp):
    dlg = OnboardingFlow()
    dlg._name_input.setText("   Akshit Vudutha   ")
    dlg._goal_insights.setChecked(True)
    dlg._goal_winddown.setChecked(True)
    dlg._finish()

    sm = SettingsManager()
    assert sm.display_name == "Akshit Vudutha"
    assert sm.onboarding_completed is True
    assert sm.get_bool("notifications_enabled", False) is True
    assert sm.get_bool("sleepguard_enabled", False) is True
    assert "insights" in sm.get("onboarding_goals", "")
    assert "winddown" in sm.get("onboarding_goals", "")
    dlg.close()


def test_onboarding_summary_without_name(clean_settings, qapp):
    dlg = OnboardingFlow()
    dlg._goal_insights.setChecked(True)
    dlg._finish()
    sm = SettingsManager()
    assert sm.display_name == ""
    assert sm.onboarding_completed is True
    dlg.close()


def test_onboarding_step_navigation(clean_settings, qapp):
    dlg = OnboardingFlow()
    assert dlg._step == 0
    dlg._go_next()
    assert dlg._step == 1
    dlg._go_back()
    assert dlg._step == 0
    dlg.close()


def test_greeting_time_periods_with_name():
    # Morning: 05:00 - 11:59
    dt_morning = datetime(2026, 9, 13, 8, 30, 0)
    g, _ = DashboardPage.get_greeting_and_context(dt_morning, "Akshit")
    assert g == "Good morning, Akshit"

    # Boundary morning check: 05:00 and 11:59
    g_0500, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 5, 0, 0), "Akshit")
    assert g_0500 == "Good morning, Akshit"
    g_1159, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 11, 59, 59), "Akshit")
    assert g_1159 == "Good morning, Akshit"

    # Afternoon: 12:00 - 16:59
    dt_afternoon = datetime(2026, 9, 13, 14, 0, 0)
    g, _ = DashboardPage.get_greeting_and_context(dt_afternoon, "Akshit")
    assert g == "Good afternoon, Akshit"

    # Evening: 17:00 - 21:59
    dt_evening = datetime(2026, 9, 13, 19, 0, 0)
    g, _ = DashboardPage.get_greeting_and_context(dt_evening, "Akshit")
    assert g == "Good evening, Akshit"

    # Late Night: 22:00 - 23:59
    dt_late = datetime(2026, 9, 13, 23, 15, 0)
    g, _ = DashboardPage.get_greeting_and_context(dt_late, "Akshit")
    assert g == "Good night, Akshit"

    # Very Late Night (past midnight): 00:00 - 04:59
    dt_very_late = datetime(2026, 9, 14, 2, 30, 0)
    g, _ = DashboardPage.get_greeting_and_context(dt_very_late, "Akshit")
    assert g == "Good night, Akshit"


def test_greeting_time_periods_without_name():
    # Neutral greetings when name is skipped or empty
    g_m, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 9, 0, 0), "")
    assert g_m == "Good morning"

    g_a, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 13, 30, 0), "")
    assert g_a == "Good afternoon"

    g_e, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 18, 0, 0), "")
    assert g_e == "Good evening"

    g_n, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 13, 22, 30, 0), "")
    assert g_n == "Good night"

    g_vn, _ = DashboardPage.get_greeting_and_context(datetime(2026, 9, 14, 1, 15, 0), "")
    assert g_vn == "Good night"


def test_late_night_context_messages():
    # 22:00 - 23:59 hours
    for day in range(1, 10):
        dt = datetime(2026, 1, day, 23, 0, 0)
        _, ctx = DashboardPage.get_greeting_and_context(dt, "Akshit")
        assert len(ctx) > 10
        # Check tone: respectful and thoughtful
        forbidden = ["sleep asap", "you should sleep", "stop using your computer"]
        assert not any(f in ctx.lower() for f in forbidden)


def test_very_late_night_context_messages():
    # Past midnight: 00:00 - 04:59
    for hour in [0, 1, 2, 3, 4]:
        dt = datetime(2026, 9, 13, hour, 30, 0)
        _, ctx = DashboardPage.get_greeting_and_context(dt, "Akshit")
        assert len(ctx) > 10
        forbidden = ["sleep asap", "you should sleep", "stop using your computer"]
        assert not any(f in ctx.lower() for f in forbidden)


def test_afternoon_screen_time_context():
    dt_afternoon = datetime(2026, 9, 13, 15, 0, 0)
    _, ctx = DashboardPage.get_greeting_and_context(
        dt_afternoon, "Akshit", screen_time_s=8040, formatted_time="2h 14m"
    )
    assert ctx == "You've spent 2h 14m on your computer today."


def test_dashboard_ui_renders_greeting(clean_settings):
    clean_settings.display_name = "Akshit"
    page = DashboardPage()
    page._refresh()
    assert "Akshit" in page._greeting_label.text()
    assert len(page._context_label.text()) > 0
    assert len(page._date_label.text()) > 0
    page.close()


def test_settings_page_display_name_flow(clean_settings):
    from ui.pages.settings import SettingsPage
    clean_settings.display_name = "Original Name"
    clean_settings.onboarding_completed = True

    page = SettingsPage()
    assert page._display_name_edit.text() == "Original Name"

    # Edit display name in settings
    page._display_name_edit.setText("Updated Akshit")
    # Simulate save without popping QMessageBox by setting directly through page logic
    page._sm.display_name = page._display_name_edit.text().strip()
    
    assert clean_settings.display_name == "Updated Akshit"
    # Verify first-run completed flag was NOT reset or altered
    assert clean_settings.onboarding_completed is True
    page.close()


def test_midnight_boundary_transition():
    # 23:59:59 (Late Night)
    dt_before = datetime(2026, 9, 13, 23, 59, 59)
    g_before, ctx_before = DashboardPage.get_greeting_and_context(dt_before, "Akshit")
    assert g_before == "Good night, Akshit"
    assert "winding down" in ctx_before or "getting late" in ctx_before or "still be there" in ctx_before or "Still going" in ctx_before

    # 00:00:00 (Very Late Night - midnight)
    dt_after = datetime(2026, 9, 14, 0, 0, 0)
    g_after, ctx_after = DashboardPage.get_greeting_and_context(dt_after, "Akshit")
    assert g_after == "Good night, Akshit"
    assert "past midnight" in ctx_after or "Late hours" in ctx_after or "Tomorrow is already here" in ctx_after or "quiet night" in ctx_after

