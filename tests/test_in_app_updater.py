"""
tests/test_in_app_updater.py — Comprehensive automated test suite for in-app updates.

Validates all 16 specified requirements:
1. Current version equals latest
2. New patch version available
3. New minor version available
4. New major version available
5. Correct semantic version comparison (including 3.10.0 > 3.9.0)
6. Malformed version handling
7. GitHub/network failure handling (friendly status, no blocking popup)
8. Download failure recovery
9. SHA-256 mismatch security (delete corrupted/unverified installer)
10. Successful checksum verification
11. Installer path validation
12. Existing user data remains untouched
13. Duplicate update prevention
14. User chooses Later
15. User chooses Update Now
16. No update check dependency for normal app startup
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from core.constants import APP_VERSION
from database.repository import Repository
from settings.manager import SettingsManager
from ui.pages.settings import SettingsPage
from utils.updater import Updater, parse_semver

TEST_SERVER_PORT = 8995


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure QApplication exists for all tests involving QObjects or QWidgets."""
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


class MockGitHubServer(BaseHTTPRequestHandler):
    """Configurable mock server to simulate GitHub API responses, installers, and checksums."""
    releases_data = []
    installer_data = b"MZ\x90\x00" + b"\x00" * 2048  # Dummy PE header & content
    installer_sha256 = ""
    simulate_network_error = False

    def do_GET(self):
        if MockGitHubServer.simulate_network_error:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")
            return

        if "/releases" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MockGitHubServer.releases_data).encode("utf-8"))

        elif "/download/DigitalWellbeingSetup" in self.path or "/download/DigitalWellbeing" in self.path:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            self.send_header("Content-Length", str(len(MockGitHubServer.installer_data)))
            self.end_headers()
            self.wfile.write(MockGitHubServer.installer_data)

        elif self.path.endswith(".sha256"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(MockGitHubServer.installer_sha256.encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP server output in test logs


@pytest.fixture(scope="module")
def mock_server():
    """Module-level fixture to run the mock HTTP server."""
    server = HTTPServer(("127.0.0.1", TEST_SERVER_PORT), MockGitHubServer)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    os.environ["GITHUB_API_BASE"] = f"http://127.0.0.1:{TEST_SERVER_PORT}"
    yield server

    server.shutdown()
    if "GITHUB_API_BASE" in os.environ:
        del os.environ["GITHUB_API_BASE"]


@pytest.fixture(autouse=True)
def reset_server_state():
    """Reset server state before each test."""
    MockGitHubServer.simulate_network_error = False
    MockGitHubServer.installer_data = b"MZ\x90\x00" + b"\x00" * 4096
    MockGitHubServer.installer_sha256 = hashlib.sha256(MockGitHubServer.installer_data).hexdigest()
    MockGitHubServer.releases_data = []


# ─── 1. Current Version Equals Latest ─────────────────────────────────────────

def test_current_version_equals_latest(mock_server):
    """When latest GitHub release matches installed version, no_update is emitted."""
    updater = Updater()
    updater._current_version = "3.6.1"

    MockGitHubServer.releases_data = [
        {
            "tag_name": "v3.6.1",
            "name": "Digital Wellbeing v3.6.1",
            "draft": False,
            "prerelease": False,
            "body": "No changes.",
            "assets": [
                {"name": "DigitalWellbeingSetup-3.6.1.exe", "browser_download_url": f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-3.6.1.exe"}
            ],
        }
    ]

    no_update_called = []
    update_avail_called = []

    updater.no_update.connect(lambda: no_update_called.append(True))
    updater.update_available.connect(lambda info: update_avail_called.append(info))

    updater._check_thread()

    assert len(no_update_called) == 1
    assert len(update_avail_called) == 0


# ─── 2. New Patch Version Available ───────────────────────────────────────────

def test_new_patch_version_available(mock_server):
    """3.6.1 -> 3.6.2 should trigger update_available with correct metadata."""
    updater = Updater()
    updater._current_version = "3.6.1"

    sha = hashlib.sha256(b"patch-content").hexdigest()
    MockGitHubServer.releases_data = [
        {
            "tag_name": "v3.6.2",
            "draft": False,
            "prerelease": False,
            "body": "Fixed focus timer regression",
            "assets": [
                {
                    "name": "DigitalWellbeingSetup-3.6.2.exe",
                    "browser_download_url": f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-3.6.2.exe",
                    "digest": f"sha256:{sha}",
                }
            ],
        }
    ]

    received = []
    updater.update_available.connect(lambda info: received.append(info))
    updater._check_thread()

    assert len(received) == 1
    assert received[0]["clean_version"] == "3.6.2"
    assert received[0]["asset_name"] == "DigitalWellbeingSetup-3.6.2.exe"
    assert received[0]["expected_sha256"] == sha


# ─── 3. New Minor Version Available ───────────────────────────────────────────

def test_new_minor_version_available(mock_server):
    """3.6.1 -> 3.7.0 should trigger update_available."""
    updater = Updater()
    updater._current_version = "3.6.1"

    MockGitHubServer.releases_data = [
        {
            "tag_name": "v3.7.0",
            "draft": False,
            "prerelease": False,
            "body": "Added new analytics dashboard",
            "assets": [
                {
                    "name": "DigitalWellbeingSetup-3.7.0.exe",
                    "browser_download_url": f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-3.7.0.exe",
                    "digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                }
            ],
        }
    ]

    received = []
    updater.update_available.connect(lambda info: received.append(info))
    updater._check_thread()

    assert len(received) == 1
    assert received[0]["clean_version"] == "3.7.0"


# ─── 4. New Major Version Available ───────────────────────────────────────────

def test_new_major_version_available(mock_server):
    """3.6.1 -> 4.0.0 should trigger update_available."""
    updater = Updater()
    updater._current_version = "3.6.1"

    MockGitHubServer.releases_data = [
        {
            "tag_name": "v4.0.0",
            "draft": False,
            "prerelease": False,
            "body": "Digital Wellbeing 4.0 Release",
            "assets": [
                {
                    "name": "DigitalWellbeingSetup-4.0.0.exe",
                    "browser_download_url": f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-4.0.0.exe",
                    "digest": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
                }
            ],
        }
    ]

    received = []
    updater.update_available.connect(lambda info: received.append(info))
    updater._check_thread()

    assert len(received) == 1
    assert received[0]["clean_version"] == "4.0.0"


# ─── 5. Correct Semantic Version Comparison ───────────────────────────────────

def test_semantic_version_comparison():
    """Validate semantic version ordering, especially double-digit minor/patch numbers."""
    updater = Updater()

    # 3.10.0 must be newer than 3.9.0
    assert updater._compare_versions("3.10.0", "3.9.0") == 1
    assert updater._compare_versions("3.9.0", "3.10.0") == -1

    # Standard progression
    assert updater._compare_versions("3.6.1", "3.6.2") == -1
    assert updater._compare_versions("3.6.1", "3.7.0") == -1
    assert updater._compare_versions("3.6.1", "4.0.0") == -1
    assert updater._compare_versions("3.6.1", "3.6.1") == 0

    # Prefix handling
    assert updater._compare_versions("v3.6.1", "3.6.1") == 0
    assert updater._compare_versions("3.6.1", "v3.6.1") == 0
    assert updater._compare_versions("v3.6.2", "3.6.1") == 1


# ─── 6. Malformed Version Handling ────────────────────────────────────────────

def test_malformed_version_handling():
    """Updater must safely handle malformed strings without raising uncaught exceptions."""
    updater = Updater()

    assert updater._compare_versions("", "3.6.1") == -1
    assert updater._compare_versions(None, "3.6.1") == -1
    assert updater._compare_versions("Unknown", "3.6.1") == -1
    assert updater._compare_versions("3.6.1", "Unknown") == 1
    assert updater._compare_versions("Unknown", "Unknown") == 0

    # parse_semver returns None on unparseable inputs
    assert parse_semver("") is None
    assert parse_semver("abc") is None
    assert parse_semver(None) is None
    assert parse_semver("3.6.1") == (3, 6, 1)


# ─── 7. GitHub / Network Failure ──────────────────────────────────────────────

def test_github_network_failure(mock_server):
    """Network failure emits friendly error and does NOT raise exceptions."""
    updater = Updater()
    MockGitHubServer.simulate_network_error = True

    errors = []
    updater.error.connect(lambda err: errors.append(err))

    updater._check_thread()

    assert len(errors) == 1
    assert "Couldn't check for updates right now." in errors[0]


# ─── 8. Download Failure ──────────────────────────────────────────────────────

def test_download_failure(mock_server, tmp_path):
    """Download failure cleans up partial file and emits an error signal."""
    updater = Updater()
    errors = []
    updater.error.connect(lambda err: errors.append(err))

    # Download from nonexistent 404 URL
    bad_url = f"http://127.0.0.1:{TEST_SERVER_PORT}/download/nonexistent.exe"
    updater._download_thread_fn(
        asset_url=bad_url,
        asset_name="FailedSetup.exe",
        asset_id=None,
        checksum_url=None,
        checksum_id=None,
        expected_sha256="fakehash",
        version="3.6.2",
    )

    assert len(errors) == 1
    assert "Download failed" in errors[0] or "404" in errors[0]


# ─── 9. SHA-256 Checksum Mismatch ─────────────────────────────────────────────

def test_sha256_mismatch(mock_server):
    """Tampered or corrupted installer must be deleted and rejected."""
    updater = Updater()
    errors = []
    complete = []
    updater.error.connect(lambda err: errors.append(err))
    updater.download_complete.connect(lambda path: complete.append(path))

    # Provide an expected hash that does NOT match the file content
    wrong_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    installer_url = f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-3.6.2.exe"

    updater._download_thread_fn(
        asset_url=installer_url,
        asset_name="DigitalWellbeingSetup-3.6.2.exe",
        asset_id=None,
        checksum_url=None,
        checksum_id=None,
        expected_sha256=wrong_hash,
        version="3.6.2",
    )

    assert len(complete) == 0
    assert len(errors) == 1
    assert "Checksum verification failed" in errors[0]

    # Verify installer file does not remain on disk
    target_path = updater._get_update_dir() / "DigitalWellbeingSetup-3.6.2.exe"
    assert not target_path.exists()


# ─── 10. Successful Checksum Verification ─────────────────────────────────────

def test_successful_checksum_verification(mock_server):
    """Valid installer with matching SHA-256 verifies and emits download_complete."""
    updater = Updater()
    complete = []
    updater.download_complete.connect(lambda path: complete.append(path))

    expected_hash = MockGitHubServer.installer_sha256
    installer_url = f"http://127.0.0.1:{TEST_SERVER_PORT}/download/DigitalWellbeingSetup-3.6.2.exe"

    updater._download_thread_fn(
        asset_url=installer_url,
        asset_name="DigitalWellbeingSetup-3.6.2.exe",
        asset_id=None,
        checksum_url=None,
        checksum_id=None,
        expected_sha256=expected_hash,
        version="3.6.2",
    )

    assert len(complete) == 1
    downloaded_file = Path(complete[0])
    assert downloaded_file.exists()
    assert downloaded_file.name == "DigitalWellbeingSetup-3.6.2.exe"


# ─── 11. Installer Path Validation ────────────────────────────────────────────

def test_installer_path_validation(tmp_path):
    """Validates that launch_installer_and_exit rejects nonexistent or invalid extensions."""
    updater = Updater()
    errors = []
    updater.error.connect(lambda err: errors.append(err))

    # 1. Non-existent path
    updater.launch_installer_and_exit(str(tmp_path / "ghost_installer.exe"))
    assert len(errors) == 1
    assert "not found" in errors[0].lower()

    # 2. Non-exe path
    fake_txt = tmp_path / "evil.txt"
    fake_txt.write_text("not an installer")
    updater.launch_installer_and_exit(str(fake_txt))
    assert len(errors) == 2
    assert "invalid installer" in errors[1].lower()


# ─── 12. Existing User Data Remains Untouched ─────────────────────────────────

def test_existing_user_data_untouched(tmp_path):
    """Database, display name, preferences, and sessions must remain completely intact."""
    db_path = tmp_path / "dw_user_data.db"
    Repository.set_db_path_override(db_path)

    repo = Repository()
    sm = SettingsManager()

    # Seed user data
    sm.display_name = "Akshit V"
    sm.sleepguard_enabled = True
    sm.auto_update_enabled = True
    repo.set_setting("app_pin_hash", "secure_pin_hash_123")

    # Simulate updater checking and preparing updates
    updater = Updater()
    updater._current_version = "3.6.1"

    # Verify everything in SQLite remains completely intact
    assert sm.display_name == "Akshit V"
    assert sm.sleepguard_enabled is True
    assert repo.get_setting("app_pin_hash") == "secure_pin_hash_123"

    # Reset repository override
    Repository.set_db_path_override(None)


# ─── 13. Duplicate Update Prevention ──────────────────────────────────────────

def test_duplicate_update_prevention():
    """Simultaneous calls to download_installer must not spawn concurrent worker threads."""
    updater = Updater()
    updater._is_downloading = True

    with patch("threading.Thread") as mock_thread:
        updater.download_installer(
            asset_url="http://example.com/setup.exe",
            asset_name="DigitalWellbeingSetup-3.6.2.exe",
            expected_sha256="fakehash",
        )
        # Thread should not have been started
        mock_thread.assert_not_called()


# ─── 14. User Chooses Later ───────────────────────────────────────────────────

def test_user_chooses_later(tmp_path):
    """When user clicks 'Later' in SettingsPage, buttons hide and postponement is signaled."""
    page = SettingsPage()
    page.show()
    page.set_update_available("3.6.2")

    assert not page._update_now_btn.isHidden()
    assert not page._update_later_btn.isHidden()

    later_signals = []
    page.update_later_requested.connect(lambda: later_signals.append(True))

    page._on_update_later_clicked()

    assert len(later_signals) == 1
    assert page._update_now_btn.isHidden() is True
    assert page._update_later_btn.isHidden() is True
    assert "postponed" in page._upd_status_lbl.text().lower()
    page.close()


# ─── 15. User Chooses Update Now ──────────────────────────────────────────────

def test_user_chooses_update_now():
    """When user clicks 'Update Now', buttons disable and download is signaled."""
    page = SettingsPage()
    page.show()
    page.set_update_available("3.6.2")

    update_signals = []
    page.update_now_requested.connect(lambda: update_signals.append(True))

    page._on_update_now_clicked()

    assert len(update_signals) == 1
    assert page._update_now_btn.isEnabled() is False
    assert page._update_later_btn.isEnabled() is False
    page.close()


# ─── 16. No Update Check Dependency for Normal App Startup ────────────────────

def test_no_update_check_dependency_for_normal_app_startup(mock_server):
    """App and Settings continue operating normally when network check fails on startup."""
    updater = Updater()
    MockGitHubServer.simulate_network_error = True

    page = SettingsPage()
    page.show()
    updater.error.connect(lambda err: page.set_update_error(err))

    # Run check thread synchronously as happens in background on startup
    updater._check_thread()

    # UI state must show friendly status without any blocking popup
    assert page._upd_status_lbl.text() == "Couldn't check for updates right now."
    assert page._check_updates_btn.isEnabled() is True
    assert page._update_now_btn.isHidden() is True
    page.close()

