"""Geometry-level visual regression checks for the responsive Focus page.

Instead of brittle pixel diffs, these tests verify the two failure modes that
caused the earlier Focus layout bug: horizontal overflow/clipping and a content
column that does not fill the available width at common window sizes.
"""
from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea

from tracker.manager import TrackingManager
from ui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    from ui.design_system import load_fonts

    load_fonts()
    yield app


def _wait(ms: int = 250) -> None:
    app = QApplication.instance()
    deadline = time.monotonic() + ms / 1000.0
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


@pytest.mark.parametrize("width", [1024, 1280, 1440])
def test_focus_page_fills_without_horizontal_overflow(qapp, width):
    window = MainWindow(tracker=TrackingManager())
    try:
        window.resize(width, 800)
        window.show()
        _wait(400)
        window._navigate(2)
        _wait(700)

        page = window._wellbeing_page
        timer = page._focus_timer
        assert timer.width() > 0

        # Only the page's outer scroll area must avoid horizontal scrolling.
        # Inner chip scrollers may legitimately scroll sideways.
        main_areas = [
            area
            for area in page.findChildren(QScrollArea)
            if area.widget() is not None and area.widget().isAncestorOf(timer)
        ]
        assert main_areas
        for area in main_areas:
            assert area.horizontalScrollBar().maximum() == 0

        # The suite should fill the content column, not sit in a narrow centered
        # island. Sidebar is 240 px and page margins are 64 px total.
        expected_min = width - 240 - 64 - 48
        assert timer.width() >= expected_min

        # Every mode card must remain inside the suite.
        for card in timer._mode_cards.values():
            assert card.geometry().right() <= timer.width()
    finally:
        window.close()
