"""
test_apple_focus_ui.py — Automated verification suite for the Apple-style Focus Page & Widgets.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

# Ensure QApplication is initialized for UI tests
app = QApplication.instance() or QApplication(sys.argv)

from database.repository import Repository
from protection.focus_manager import FocusManager
from ui.pages.wellbeing import WellbeingPage
from ui.theme import ThemeManager
from ui.widgets.focus_timer import (
    AddWebsiteDialog,
    AppleFocusRing,
    ChipWidget,
    DeepFocusPreflightDialog,
    FocusModeCard,
    FocusTimerWidget,
    MODE_CONFIG,
    _get_mode_color,
)


def setup_clean_focus_manager():
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, "dw_test_apple_focus.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass
    Repository.set_db_path_override(Path(db_path))
    repo = Repository()
    FocusManager._instance = None
    fm = FocusManager(repo)
    FocusManager._instance = fm
    return repo, fm


def test_apple_focus_ring():
    ring = AppleFocusRing()
    ring.resize(250, 250)

    # Test initial and updated states
    ring.update_state(
        time_text="25:00",
        progress=0.0,
        tag_text="Deep Focus",
        status_text="Ready to focus",
        mode_color="#BF5AF2",
        is_active=False,
    )
    assert ring._time_text == "25:00"
    assert ring._progress == 0.0
    assert ring._tag_text == "DEEP FOCUS"
    assert ring._mode_color == "#BF5AF2"

    # Test active progress update
    ring.update_state(
        time_text="12:30",
        progress=0.5,
        tag_text="Work",
        status_text="Deep concentration",
        mode_color="#0A84FF",
        is_active=True,
    )
    assert ring._time_text == "12:30"
    assert ring._progress == 0.5
    assert ring._tag_text == "WORK"

    # Trigger paintEvent without exceptions
    ring.repaint()
    print("[OK] test_apple_focus_ring passed")


def test_focus_mode_cards():
    repo, fm = setup_clean_focus_manager()
    fm._timer.blockSignals(True)

    for m_id, cfg in MODE_CONFIG.items():
        card = FocusModeCard(m_id)
        assert card.title_str == cfg["title"]
        assert card.icon_name == cfg["icon"]

        # Selection toggle
        card.set_selected(True)
        assert card._is_selected is True
        card.set_selected(False)
        assert card._is_selected is False

    print("[OK] test_focus_mode_cards passed")


def test_chip_widget():
    chip = ChipWidget("reddit.com")
    assert chip.text_val == "reddit.com"

    removed_payload = []
    chip.removed.connect(lambda t: removed_payload.append(t))
    chip.btn.click()
    assert removed_payload == ["reddit.com"]
    print("[OK] test_chip_widget passed")


def test_focus_timer_widget_controls():
    repo, fm = setup_clean_focus_manager()
    fm._timer.blockSignals(True)
    fm.save_mode_apps("work", ["code.exe"])
    fm.save_mode_apps("study", ["word.exe"])

    widget = FocusTimerWidget()

    # 1. Test Mode Switching
    widget._set_mode("work")
    assert fm.current_mode == "work"
    assert widget._mode_cards["work"]._is_selected is True
    assert widget._mode_cards["deep"]._is_selected is False

    widget._set_mode("study")
    assert fm.current_mode == "study"
    assert widget._mode_cards["study"]._is_selected is True

    # 2. Test Duration Preset Pills
    widget.set_preset(45)
    assert widget._selected_minutes == 45
    assert widget._session_total_seconds == 45 * 60
    assert widget._focus_ring._time_text == "45:00"

    # 3. Test Steppers (-5m, +5m)
    widget._adjust_duration(5)
    assert widget._selected_minutes == 50
    assert widget._focus_ring._time_text == "50:00"

    widget._adjust_duration(-10)
    assert widget._selected_minutes == 40
    assert widget._focus_ring._time_text == "40:00"

    # 4. Test Website Quick Presets (toggle)
    initially_in = "youtube.com" in fm.get_mode_websites("study")
    widget._quick_toggle_site("youtube.com")
    assert ("youtube.com" in fm.get_mode_websites("study")) != initially_in

    # Toggle again restores initial
    widget._quick_toggle_site("youtube.com")
    assert ("youtube.com" in fm.get_mode_websites("study")) == initially_in

    # 5. Test Search Filtering
    fm.add_mode_website("study", "wikipedia.org")
    fm.add_mode_website("study", "coursera.org")
    widget._on_search_websites("wiki")
    assert widget._site_search_query == "wiki"

    widget._on_search_websites("")
    assert widget._site_search_query == ""

    # 6. Test Active Tick Countdown
    widget._on_tick(1200)  # 20m remaining out of 40m
    assert widget._active_elapsed_pill.text_lbl.text() == "20m elapsed"
    assert widget._active_remaining_pill.text_lbl.text() == "20m remaining"

    # 7. Test Theme Changes
    widget._apply_theme(is_dark=True)
    widget._apply_theme(is_dark=False)
    widget._apply_theme(is_dark=True)

    print("[OK] test_focus_timer_widget_controls passed")


def test_wellbeing_page_instantiation():
    repo, fm = setup_clean_focus_manager()
    fm._timer.blockSignals(True)

    page = WellbeingPage()
    assert page._status_capsule.text_lbl.text() == "Focus Inactive"

    # Simulate active focus
    page._on_focus_state_changed(True)
    assert "Focus Active" in page._status_capsule.text_lbl.text()

    # Simulate inactive focus
    page._on_focus_state_changed(False)
    assert page._status_capsule.text_lbl.text() == "Focus Inactive"

    print("[OK] test_wellbeing_page_instantiation passed")


def run_all():
    print("=== RUNNING APPLE FOCUS UI TESTS ===")
    test_apple_focus_ring()
    test_focus_mode_cards()
    test_chip_widget()
    test_focus_timer_widget_controls()
    test_wellbeing_page_instantiation()
    print("=== ALL APPLE FOCUS UI TESTS PASSED ===")


if __name__ == "__main__":
    run_all()
