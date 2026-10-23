"""
test_website_blocking.py — Comprehensive unit and integration tests for Focus Mode Website Blocking.

Tests cover:
1. Domain normalization, validation, and sanitation.
2. Domain variant expansion (apex, www, subdomains).
3. Managed delimited block generation and parsing.
4. Activation and unblocking with strict rollback preserving unrelated hosts entries.
5. Duplicate entry prevention and idempotent operations.
6. Crash/restart recovery (orphan delimited block removal).
7. Graceful permission error handling and fail-safe fallback.
8. FocusManager mode website persistence and lifecycle integration.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from protection.website_blocker import (
    WebsiteBlocker,
    BLOCK_HEADER,
    BLOCK_FOOTER,
)
from protection.focus_manager import DEFAULT_MODE_WEBSITES


@pytest.fixture
def temp_hosts_file():
    """Provides a temporary hosts file with standard Windows contents."""
    initial_content = (
        "# Copyright (c) 1993-2009 Microsoft Corp.\n"
        "# Standard Windows hosts file\n"
        "127.0.0.1       localhost\n"
        "::1             localhost\n"
        "# User custom entries\n"
        "192.168.1.100   myrouter.local\n"
    )
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        f.write(initial_content)
        path = Path(f.name)
    yield path
    try:
        if path.exists():
            path.unlink()
        bak = path.with_suffix(".dw.bak")
        if bak.exists():
            bak.unlink()
    except Exception:
        pass


class TestWebsiteBlockerDomainHandling:
    def test_clean_domain_variants(self):
        """Verify various raw inputs are properly cleaned to canonical domain names."""
        assert WebsiteBlocker.clean_domain("https://www.youtube.com/watch?v=123") == "youtube.com"
        assert WebsiteBlocker.clean_domain("http://instagram.com/p/abc/") == "instagram.com"
        assert WebsiteBlocker.clean_domain("reddit.com") == "reddit.com"
        assert WebsiteBlocker.clean_domain("  WWW.X.COM  ") == "x.com"
        assert WebsiteBlocker.clean_domain("https://sub.domain.co.uk/path") == "sub.domain.co.uk"
        assert WebsiteBlocker.clean_domain("") is None
        assert WebsiteBlocker.clean_domain("not a valid domain") is None
        assert WebsiteBlocker.clean_domain("http://") is None

    def test_domain_variant_expansion(self):
        """Verify known platform aliases and apex/www variants are expanded."""
        blocker = WebsiteBlocker(Path("dummy_hosts"))
        
        # Test youtube expansion
        expanded_yt = blocker.expand_domain_variants(["youtube.com"])
        assert "youtube.com" in expanded_yt
        assert "www.youtube.com" in expanded_yt
        assert "m.youtube.com" in expanded_yt
        assert "youtu.be" in expanded_yt

        # Test x.com / twitter.com expansion
        expanded_x = blocker.expand_domain_variants(["x.com"])
        assert "x.com" in expanded_x
        assert "www.x.com" in expanded_x
        assert "twitter.com" in expanded_x
        assert "www.twitter.com" in expanded_x

        # Test arbitrary domain gets both apex and www
        expanded_arb = blocker.expand_domain_variants(["distractinggame.io"])
        assert "distractinggame.io" in expanded_arb
        assert "www.distractinggame.io" in expanded_arb


class TestWebsiteBlockerHostsOperations:
    def test_block_websites_creates_clean_delimited_block(self, temp_hosts_file):
        """Verify blocking writes the managed delimited block and preserves unrelated content."""
        blocker = WebsiteBlocker(temp_hosts_file)
        
        success, msg = blocker.block_websites(["instagram.com", "reddit.com"])
        assert success is True
        assert blocker.is_blocking_active is True

        content = temp_hosts_file.read_text(encoding="utf-8")
        assert "192.168.1.100   myrouter.local" in content  # Preserved original
        assert BLOCK_HEADER in content
        assert BLOCK_FOOTER in content
        assert "0.0.0.0 instagram.com" in content
        assert "::1 instagram.com" in content
        assert "0.0.0.0 www.instagram.com" in content
        assert "0.0.0.0 reddit.com" in content

    def test_unblock_websites_restores_clean_file(self, temp_hosts_file):
        """Verify unblocking strips the managed block completely."""
        blocker = WebsiteBlocker(temp_hosts_file)
        blocker.block_websites(["youtube.com"])
        
        success, msg = blocker.unblock_all()
        assert success is True
        assert blocker.is_blocking_active is False

        content = temp_hosts_file.read_text(encoding="utf-8")
        assert BLOCK_HEADER not in content
        assert BLOCK_FOOTER not in content
        assert "youtube.com" not in content
        assert "192.168.1.100   myrouter.local" in content

    def test_duplicate_blocking_does_not_create_nested_blocks(self, temp_hosts_file):
        """Verify repeated calls to block_websites safely replace rather than duplicate blocks."""
        blocker = WebsiteBlocker(temp_hosts_file)
        blocker.block_websites(["youtube.com"])
        blocker.block_websites(["youtube.com", "reddit.com"])

        content = temp_hosts_file.read_text(encoding="utf-8")
        assert content.count(BLOCK_HEADER) == 1
        assert content.count(BLOCK_FOOTER) == 1
        assert "reddit.com" in content

    def test_startup_orphan_cleanup(self, temp_hosts_file):
        """Simulate a prior crash leaving a managed block, verify startup cleanup restores it."""
        # Manually inject an orphan block
        orphan = (
            temp_hosts_file.read_text(encoding="utf-8")
            + f"\n{BLOCK_HEADER}\n0.0.0.0 leftover.com\n{BLOCK_FOOTER}\n"
        )
        temp_hosts_file.write_text(orphan, encoding="utf-8")

        # Instantiate fresh blocker simulating app launch
        blocker = WebsiteBlocker(temp_hosts_file)
        cleaned = blocker.cleanup_orphaned_blocks()
        assert cleaned is True

        content = temp_hosts_file.read_text(encoding="utf-8")
        assert BLOCK_HEADER not in content
        assert "leftover.com" not in content
        assert "myrouter.local" in content

    def test_permission_error_fails_safely_without_crashing(self, temp_hosts_file):
        """Verify that when hosts file cannot be opened (EACCES / PermissionError), fail safely."""
        blocker = WebsiteBlocker(temp_hosts_file)
        
        with patch.object(Path, "open", side_effect=PermissionError("Access Denied")):
            success, msg = blocker.block_websites(["reddit.com"])
            assert success is False
            assert "Permission denied" in msg or "administrator" in msg
            # Application did not crash and state remains inactive
            assert blocker.is_blocking_active is False


class TestFocusManagerWebsiteIntegration:
    def test_focus_manager_initializes_default_mode_websites(self):
        """Verify all 5 focus modes have proper default website lists."""
        from protection.focus_manager import FocusManager
        fm = FocusManager.instance()
        
        for mode in ("study", "work", "movie", "deep", "custom"):
            sites = fm.get_mode_websites(mode)
            assert isinstance(sites, list)
            assert len(sites) > 0

    def test_focus_manager_add_and_remove_website(self):
        """Verify dynamic addition and removal of blocked domains."""
        from protection.focus_manager import FocusManager
        fm = FocusManager.instance()
        
        test_domain = "distractingtestsite99.com"
        added = fm.add_mode_website("study", test_domain)
        assert added is True
        assert test_domain in fm.get_mode_websites("study")

        # Duplicate addition returns False
        added_again = fm.add_mode_website("study", test_domain)
        assert added_again is False

        # Removal
        removed = fm.remove_mode_website("study", test_domain)
        assert removed is True
        assert test_domain not in fm.get_mode_websites("study")
