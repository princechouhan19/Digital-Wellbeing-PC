"""
test_website_tracking.py — Comprehensive automated test suite for browser website tracking and logo fetching.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile
from datetime import date, datetime, timedelta

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

# Ensure QApplication is initialized for UI tests
app = QApplication.instance() or QApplication(sys.argv)

from analytics.engine import AnalyticsEngine
from database.models import WebsiteSession
from database.repository import Repository
from tracker.browser_domain import (
    clean_browser_title,
    extract_domain_from_title,
    is_browser_process,
)
from ui.widgets.website_row import WebsiteUsageRow
from ui.widgets.website_timer_widgets import WebsiteTimerItem
from utils.website_icon_provider import WebsiteIconProvider


def test_domain_normalization():
    p = WebsiteIconProvider()
    assert p.normalize_domain("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "youtube.com"
    assert p.normalize_domain("http://github.com/torvalds/linux") == "github.com"
    assert p.normalize_domain("WWW.REDDIT.COM/r/python") == "reddit.com"
    assert p.normalize_domain("claude.ai/chat/123") == "claude.ai"
    assert p.normalize_domain("") == ""
    print("[OK] test_domain_normalization passed")


def test_browser_domain_extraction():
    assert is_browser_process("chrome.exe")
    assert is_browser_process("msedge.exe")
    assert is_browser_process("brave.exe")
    assert not is_browser_process("code.exe")

    # Title suffix cleaning
    cleaned = clean_browser_title("YouTube - Google Chrome")
    assert cleaned == "YouTube"

    # Known services extraction
    assert extract_domain_from_title("YouTube - Google Chrome", "chrome.exe") == "youtube.com"
    assert extract_domain_from_title("GitHub - princechouhan19/Digital-Wellbeing-PC - Microsoft Edge", "msedge.exe") == "github.com"
    assert extract_domain_from_title("Claude - Anthropic - Google Chrome", "chrome.exe") == "claude.ai"
    assert extract_domain_from_title("Notion – The all-in-one workspace - Brave", "brave.exe") == "notion.so"
    assert extract_domain_from_title("ChatGPT - Mozilla Firefox", "firefox.exe") == "chatgpt.com"
    assert extract_domain_from_title("Reddit: The front page of the internet - Google Chrome", "chrome.exe") == "reddit.com"

    # Generic domain extraction
    assert extract_domain_from_title("Welcome to example.com - Microsoft Edge", "msedge.exe") == "example.com"
    assert extract_domain_from_title("python.org - Official Documentation - Google Chrome", "chrome.exe") == "python.org"
    print("[OK] test_browser_domain_extraction passed")


def test_website_icon_provider():
    p = WebsiteIconProvider()
    # Check fallback letter avatar generation
    icon = p.get_icon("youtube.com", size=32)
    assert not icon.isNull()
    pix = p.get_pixmap("youtube.com", size=32)
    assert not pix.isNull()
    assert pix.width() in (32, int(32 * pix.devicePixelRatio()))
    assert pix.height() in (32, int(32 * pix.devicePixelRatio()))

    # Check that disk cache path is created
    assert p._cache_dir.exists()
    print("[OK] test_website_icon_provider passed")


def test_website_repository_and_analytics():
    # Setup isolated test database
    temp_db = Path(tempfile.gettempdir()) / "dw_test_website_tracking.db"
    if temp_db.exists():
        try:
            temp_db.unlink()
        except Exception:
            pass
    Repository.set_db_path_override(temp_db)

    repo = Repository()
    engine = AnalyticsEngine()
    test_date = date(2026, 5, 20)
    base_time = datetime(2026, 5, 20, 14, 30, 0)

    # Insert website sessions for Chrome
    s1 = WebsiteSession(
        domain="youtube.com",
        browser_process="chrome.exe",
        start_time=base_time - timedelta(minutes=45),
        end_time=base_time - timedelta(minutes=15),
        duration_s=1800.0,
        was_closed=True,
    )
    s2 = WebsiteSession(
        domain="github.com",
        browser_process="chrome.exe",
        start_time=base_time - timedelta(minutes=15),
        end_time=base_time,
        duration_s=900.0,
        was_closed=True,
    )
    # Insert website session for Edge
    s3 = WebsiteSession(
        domain="reddit.com",
        browser_process="msedge.exe",
        start_time=base_time - timedelta(minutes=30),
        end_time=base_time - timedelta(minutes=10),
        duration_s=1200.0,
        was_closed=True,
    )

    repo.insert_website_session(s1)
    repo.insert_website_session(s2)
    repo.insert_website_session(s3)

    # 1. Test top websites for Chrome
    chrome_sites = repo.get_top_websites_for_browser("chrome.exe", test_date, test_date)
    assert len(chrome_sites) == 2
    assert chrome_sites[0]["domain"] == "youtube.com"
    assert chrome_sites[0]["total_s"] == 1800.0
    assert chrome_sites[1]["domain"] == "github.com"
    assert chrome_sites[1]["total_s"] == 900.0

    # 2. Test top websites across all browsers
    all_sites = repo.get_top_websites_for_range(test_date, test_date)
    assert len(all_sites) == 3
    assert all_sites[0]["domain"] == "youtube.com"
    assert all_sites[1]["domain"] == "reddit.com"
    assert all_sites[2]["domain"] == "github.com"

    # 3. Test total website time
    total_time = repo.get_total_website_time_for_range(test_date, test_date)
    assert total_time == 3900.0  # 1800 + 900 + 1200

    # 4. Test AnalyticsEngine wrapper methods
    engine_chrome_sites = engine.get_top_websites_for_browser("chrome.exe", test_date, test_date)
    assert len(engine_chrome_sites) == 2

    engine_all_sites = engine.get_top_websites_for_range(test_date, test_date)
    assert len(engine_all_sites) == 3

    assert engine.get_total_website_time(test_date, test_date) == 3900.0
    assert engine.get_total_website_time(test_date, test_date, browser_process="chrome.exe") == 2700.0

    print("[OK] test_website_repository_and_analytics passed")


def test_website_ui_widgets():
    # 1. WebsiteUsageRow
    row = WebsiteUsageRow(
        domain="github.com",
        duration_s=1800.0,
        max_duration_s=3600.0,
        browser_process="chrome.exe",
        show_limit_button=True,
    )
    assert row.domain == "github.com"
    assert row._domain_lbl.text() == "github.com"
    assert "30m" in row._duration_lbl.text()
    assert row._progress_bar.value() == 500  # 50%

    # 2. WebsiteTimerItem with icon
    item = WebsiteTimerItem(
        domain="youtube.com",
        limit_s=3600,
        used_s=1800.0,
    )
    assert item.domain == "youtube.com"
    assert hasattr(item, "icon_lbl")
    assert not item.icon_lbl.pixmap().isNull()

    print("[OK] test_website_ui_widgets passed")


def test_cross_browser_website_aggregation():
    temp_db = Path(tempfile.gettempdir()) / "dw_test_cross_browser.db"
    if temp_db.exists():
        try:
            temp_db.unlink()
        except Exception:
            pass
    Repository.set_db_path_override(temp_db)

    repo = Repository()
    engine = AnalyticsEngine()
    test_d = date(2026, 6, 15)
    t = datetime(2026, 6, 15, 10, 0, 0)

    # User watches YouTube on Chrome (30m), then Brave (20m), then Edge (10m)
    repo.insert_website_session(WebsiteSession("youtube.com", "chrome.exe", t, t + timedelta(minutes=30), 1800.0, True))
    repo.insert_website_session(WebsiteSession("youtube.com", "brave.exe", t + timedelta(minutes=30), t + timedelta(minutes=50), 1200.0, True))
    repo.insert_website_session(WebsiteSession("youtube.com", "msedge.exe", t + timedelta(minutes=50), t + timedelta(hours=1), 600.0, True))

    # User browses GitHub on Atlas (25m) and Comet (15m)
    repo.insert_website_session(WebsiteSession("github.com", "atlas.exe", t, t + timedelta(minutes=25), 1500.0, True))
    repo.insert_website_session(WebsiteSession("github.com", "comet.exe", t + timedelta(minutes=25), t + timedelta(minutes=40), 900.0, True))

    # 1. Cross-browser aggregation: YouTube total should be 3600s (1 hour)
    overall = repo.get_top_websites_for_range(test_d, test_d)
    assert len(overall) == 2
    assert overall[0]["domain"] == "youtube.com"
    assert overall[0]["total_s"] == 3600.0
    assert overall[0]["session_count"] == 3
    # Check that all 3 browsers are captured
    assert "chrome.exe" in overall[0]["browser_list"]
    assert "brave.exe" in overall[0]["browser_list"]
    assert "msedge.exe" in overall[0]["browser_list"]

    # 2. Check GitHub total is 2400s (40m) across Atlas and Comet
    assert overall[1]["domain"] == "github.com"
    assert overall[1]["total_s"] == 2400.0
    assert "atlas.exe" in overall[1]["browser_list"]
    assert "comet.exe" in overall[1]["browser_list"]

    # 3. Test filtering by specific browser
    chrome_only = repo.get_top_websites_for_range(test_d, test_d, browser_process="chrome.exe")
    assert len(chrome_only) == 1
    assert chrome_only[0]["domain"] == "youtube.com"
    assert chrome_only[0]["total_s"] == 1800.0

    brave_only = repo.get_top_websites_for_range(test_d, test_d, browser_process="brave.exe")
    assert len(brave_only) == 1
    assert brave_only[0]["total_s"] == 1200.0

    # 4. Distinct browsers list
    browsers = repo.get_distinct_browsers_for_range(test_d, test_d)
    assert set(browsers) == {"chrome.exe", "brave.exe", "msedge.exe", "atlas.exe", "comet.exe"}

    print("[OK] test_cross_browser_website_aggregation passed")


def test_cross_browser_website_limits():
    temp_db = Path(tempfile.gettempdir()) / "dw_test_cross_limits.db"
    if temp_db.exists():
        try:
            temp_db.unlink()
        except Exception:
            pass
    Repository.set_db_path_override(temp_db)
    repo = Repository()

    from protection.website_limits import WebsiteLimitManager
    mgr = WebsiteLimitManager(repo)

    # Set cross-browser wildcard limit on youtube.com (1800s / 30m)
    rule = {"limit_seconds": 1800, "repeat_days": [0, 1, 2, 3, 4, 5, 6]}
    mgr.set_limit_rule("*", "youtube.com", rule)

    # Verify limit is enforced across ANY browser
    assert mgr.get_limit("chrome.exe", "youtube.com") == 1800
    assert mgr.get_limit("brave.exe", "youtube.com") == 1800
    assert mgr.get_limit("msedge.exe", "youtube.com") == 1800
    assert mgr.get_limit("atlas.exe", "youtube.com") == 1800
    assert mgr.get_limit("comet.exe", "youtube.com") == 1800
    assert mgr.get_limit("firefox.exe", "youtube.com") == 1800

    print("[OK] test_cross_browser_website_limits passed")


def test_websites_page_instantiation():
    from ui.pages.websites import WebsitesPage
    page = WebsitesPage(protection_manager=None)
    page.refresh()
    assert hasattr(page, "_sites_list_layout")
    assert hasattr(page, "_kpi_web_time")
    assert hasattr(page, "_browser_combo")
    print("[OK] test_websites_page_instantiation passed")


if __name__ == "__main__":
    print("=== RUNNING WEBSITE TRACKING TESTS ===")
    test_domain_normalization()
    test_browser_domain_extraction()
    test_website_icon_provider()
    test_website_repository_and_analytics()
    test_website_ui_widgets()
    test_cross_browser_website_aggregation()
    test_cross_browser_website_limits()
    test_websites_page_instantiation()
    print("=== ALL WEBSITE TRACKING TESTS PASSED ===")
