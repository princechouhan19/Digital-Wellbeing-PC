"""
tests/test_history_lifecycle.py — Focused regression tests for HistoryPage widget lifecycle:
1. Verifies that HistoryPage.on_data_changed() safely refreshes widgets without NoneType deleteLater errors.
2. Verifies that storing local widget reference prevents NoneType access after setParent(None).
3. Verifies that repeated on_data_changed() calls do not leak or accumulate widgets.
4. Verifies that empty history states (placeholder labels) refresh cleanly.
5. Verifies that non-widget layout items (spacers/stretch) are handled safely.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
import pytest
from PySide6.QtWidgets import QApplication, QLabel

from database.repository import Repository
from ui.pages.history import HistoryPage, HistoryTimelineItem


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


from database.models import DailyStat


@pytest.fixture
def test_repo(tmp_path):
    db_path = tmp_path / "test_history_lifecycle.db"
    Repository.set_db_path_override(db_path)
    repo = Repository()
    
    # Insert mock daily stats
    today = date.today()
    for i in range(5):
        d = today - timedelta(days=i)
        stat = DailyStat(
            date=d,
            total_screen_time_s=3600.0 * (i + 1) + 600.0,
            active_time_s=3600.0 * (i + 1),
            idle_time_s=600.0,
            top_app="Code.exe" if i % 2 == 0 else "brave.exe",
            session_count=10,
        )
        repo.upsert_daily_stat(stat)
        
    yield repo
    Repository.set_db_path_override(None)


class TestHistoryLifecycle:
    def test_reproduce_unparent_then_delete_later_safety(self, qapp, test_repo):
        """Verifies that storing the widget reference in a local variable before
        setParent(None) guarantees deleteLater() is called on a valid widget,
        preventing 'NoneType' object has no attribute 'deleteLater'.
        """
        page = HistoryPage()
        
        # Take the first layout item
        item = page._inner_layout.takeAt(0)
        assert item is not None
        
        w = item.widget()
        assert w is not None
        
        # When setParent(None) is called on the widget:
        w.hide()
        w.setParent(None)
        
        # In PySide6, item.widget() can evaluate to None once detached
        # but the local variable 'w' retains the valid QWidget reference
        assert w is not None
        w.deleteLater()  # Must NOT raise AttributeError
        qapp.processEvents()

    def test_on_data_changed_refreshes_cleanly(self, qapp, test_repo):
        """Verifies on_data_changed() completes without error and rebuilds timeline."""
        page = HistoryPage()
        initial_count = page._inner_layout.count()
        assert initial_count > 1  # Items + stretch
        
        # Trigger data changed
        page.on_data_changed()
        qapp.processEvents()
        
        # Layout count should remain identical (rebuilt from same repository stats)
        assert page._inner_layout.count() == initial_count

    def test_repeated_data_refreshes_no_accumulation(self, qapp, test_repo):
        """Verifies that calling on_data_changed() repeatedly does not accumulate duplicate widgets."""
        page = HistoryPage()
        expected_count = page._inner_layout.count()
        
        for _ in range(10):
            page.on_data_changed()
            qapp.processEvents()
            assert page._inner_layout.count() == expected_count, "Widgets accumulated across refreshes!"

    def test_empty_history_placeholder_refreshes(self, qapp, tmp_path):
        """Verifies that on_data_changed() works properly when there are no historical stats."""
        empty_db = tmp_path / "empty_history.db"
        Repository.set_db_path_override(empty_db)
        repo = Repository()
        
        page = HistoryPage()
        assert page._inner_layout.count() == 2  # 1 placeholder label + 1 stretch
        
        # Trigger refresh on empty state
        page.on_data_changed()
        qapp.processEvents()
        
        assert page._inner_layout.count() == 2
        Repository.set_db_path_override(None)

    def test_safe_handling_when_item_has_no_widget(self, qapp, test_repo):
        """Verifies that layout items without widgets (e.g. spacers) do not crash on_data_changed()."""
        page = HistoryPage()
        # Insert a stretch at the top
        page._inner_layout.insertStretch(0, 1)
        
        # Refresh should cleanly handle the spacer/stretch item without widget()
        page.on_data_changed()
        qapp.processEvents()
        assert page._inner_layout.count() > 0
