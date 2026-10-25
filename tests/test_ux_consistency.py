"""Guardrails for the shared page rhythm and Focus page layout.

These are intentionally source-level checks: the Qt layouts are assembled in
several different ways (direct layouts, scroll areas, lazy pages), so checking
the canonical margin string is the most stable way to prevent a page from
silently drifting back to its own spacing.
"""
from __future__ import annotations

from pathlib import Path

from ui import design_system as ds


ROOT = Path(__file__).resolve().parent.parent


def test_design_tokens_are_canonical():
    assert ds.PAGE_MARGINS == (32, 28, 32, 28)
    assert ds.PAGE_SECTION_SPACING == 24
    assert ds.CARD_RADIUS == ds.RADIUS["lg"]
    assert ds.CARD_MARGINS == (20, 18, 20, 18)
    assert ds.BUTTON_RADIUS == ds.RADIUS["md"]
    assert ds.BUTTON_RADIUS_PILL == ds.RADIUS["pill"]


def test_main_pages_share_the_same_page_margins():
    pages = [
        "dashboard.py",
        "activity.py",
        "app_timer.py",
        "app_locker.py",
        "insights.py",
        "history.py",
        "settings.py",
        "sleepguard_page.py",
        "websites.py",
        "wellbeing.py",
        "app_details.py",
        "screen_time_details.py",
        "debug.py",
    ]
    for name in pages:
        source = (ROOT / "ui" / "pages" / name).read_text(encoding="utf-8")
        assert "setContentsMargins(32, 28, 32, 28)" in source, name


def test_focus_page_is_not_artificially_narrow():
    source = (ROOT / "ui" / "pages" / "wellbeing.py").read_text(encoding="utf-8")
    assert "setMaximumWidth(1180)" not in source
    assert "AlignHCenter | Qt.AlignmentFlag.AlignTop" not in source
    assert "addWidget(self._focus_timer, 1)" in source


def test_ui_primitives_share_tokens_and_density():
    from PySide6.QtWidgets import QApplication

    from ui.primitives import Button, Card, PageScaffold

    app = QApplication.instance() or QApplication([])
    page = PageScaffold("Title", "Subtitle")
    try:
        margins = page.content_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == ds.PAGE_MARGINS
        page.set_density(True)
        margins = page.content_layout.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (24, 20, 24, 20)
        assert page.content_layout.spacing() == 18
    finally:
        page.deleteLater()

    card = Card()
    try:
        margins = card.body.contentsMargins()
        assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == ds.CARD_MARGINS
    finally:
        card.deleteLater()

    button = Button("Go", "primary")
    try:
        assert button.objectName() == "primary_pill_btn"
    finally:
        button.deleteLater()
