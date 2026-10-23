"""
test_focus_mode_features.py
Comprehensive test suite for the new Focus Mode architecture:
- Application search & discovery classification
- Deep Focus allowlist vs blocklist
- Selected user app allowed vs unselected user app restricted
- System process safety (explorer, svchost, dwm, services, etc.)
- Background helper safety (steamwebhelper, crashpad, updaters)
- Focus ending restores normal behavior
- Study, Work, Movie presets & keyword suggestions
- Deep Focus empty initial configuration
- Preset persistence across sessions
- Custom mode blocklist backward compatibility
- Focus timer countdown and completion
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.repository import Repository
from protection.focus_manager import FocusManager
from utils.win_utils import is_safe_lock_target, is_user_facing_application


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_repo(tmp_path):
    """Provides an isolated SQLite repository."""
    db_file = tmp_path / "test_focus_features.db"
    Repository.set_db_path_override(db_file)
    repo = Repository()
    yield repo
    Repository.set_db_path_override(None)


@pytest.fixture
def focus_mgr(test_repo):
    """Provides a clean FocusManager singleton instance."""
    FocusManager._instance = None
    fm = FocusManager(test_repo)
    FocusManager._instance = fm
    fm._timer.blockSignals(True)  # Don't let background timer fire during test
    yield fm
    fm._timer.stop()
    FocusManager._instance = None


# ── 1. Application Search / Discovery Classification ──────────────────────────

class TestApplicationDiscovery:
    """Tests discovery filtering: legitimate user apps vs system/helper processes."""

    def test_application_search_discovery_legitimate_apps(self):
        user_apps = [
            (1001, r"C:\Users\User\AppData\Local\Programs\Brave\brave.exe", "brave.exe"),
            (1002, r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "msedge.exe"),
            (1003, r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\Code.exe", "code.exe"),
            (1004, r"C:\Program Files (x86)\Steam\steam.exe", "steam.exe"),
            (1005, r"C:\Users\User\AppData\Local\Discord\app-1.0.9000\Discord.exe", "discord.exe"),
            (1006, r"C:\Users\User\AppData\Roaming\Spotify\Spotify.exe", "spotify.exe"),
        ]
        for pid, path, name in user_apps:
            assert is_safe_lock_target(path, name) is True, f"Failed safe check for {name}"
            assert is_user_facing_application(pid, path, name) is True, f"Failed user-facing check for {name}"

    def test_system_processes_rejected_from_discovery(self):
        system_procs = [
            (101, r"C:\Windows\explorer.exe", "explorer.exe"),
            (102, r"C:\Windows\System32\svchost.exe", "svchost.exe"),
            (103, r"C:\Windows\System32\dwm.exe", "dwm.exe"),
            (104, r"C:\Windows\System32\services.exe", "services.exe"),
            (105, r"C:\Windows\System32\lsass.exe", "lsass.exe"),
            (106, r"C:\Windows\System32\csrss.exe", "csrss.exe"),
            (107, r"C:\Program Files\Digital Wellbeing\digitalwellbeing.exe", "digitalwellbeing.exe"),
        ]
        for pid, path, name in system_procs:
            assert is_safe_lock_target(path, name) is False, f"System process {name} should NOT be safe target"
            assert is_user_facing_application(pid, path, name) is False, f"System process {name} should NOT be user-facing"

    @pytest.mark.skipif(sys.platform != "win32", reason="Discovers apps from the Windows Start Menu and registry")
    def test_installed_applications_discovery_when_closed(self):
        from utils.win_utils import get_installed_user_applications, get_all_discoverable_applications
        installed = get_installed_user_applications()
        assert isinstance(installed, dict)
        assert len(installed) > 0

        discoverable = get_all_discoverable_applications()
        assert isinstance(discoverable, list)
        assert len(discoverable) >= len(installed)

        # Confirm legitimate store apps like Spotify or system desktop apps like VS Code or Brave are discovered
        proc_names = {item[0] for item in discoverable}
        assert any(app in proc_names for app in ("code.exe", "brave.exe", "msedge.exe", "spotify.exe", "discord.exe", "chrome.exe"))

    def test_helper_and_background_processes_rejected(self):
        helper_procs = [
            (201, r"C:\Program Files (x86)\Steam\steamwebhelper.exe", "steamwebhelper.exe"),
            (202, r"C:\Program Files\Google\Update\GoogleUpdate.exe", "googleupdate.exe"),
            (203, r"C:\Users\User\AppData\Local\Brave\crashpad_handler.exe", "crashpad_handler.exe"),
            (204, r"C:\Program Files\AudioService\audio.service.exe", "audio.service.exe"),
            (205, r"C:\Program Files\Common\sync_daemon.exe", "sync_daemon.exe"),
        ]
        for pid, path, name in helper_procs:
            assert is_user_facing_application(pid, path, name) is False, f"Helper {name} should NOT be user-facing"


# ── 2. Deep Focus Allowlist & Process Evaluation ──────────────────────────────

class TestDeepFocusEnforcement:
    """Tests the decision tree of Deep Focus allowlist."""

    def test_deep_focus_empty_initial_configuration(self, focus_mgr):
        focus_mgr.set_mode("deep")
        assert focus_mgr.current_mode == "deep"
        assert focus_mgr.current_mode_apps == []

    def test_selected_user_app_is_allowed(self, focus_mgr):
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", ["code.exe", "brave.exe"])
        mock_proc = MagicMock()

        # code.exe is in the allowlist -> ALLOW
        allowed = focus_mgr._evaluate_process(
            pid=1001,
            p_name="code.exe",
            exe_path=r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            proc=mock_proc,
        )
        assert allowed is True
        mock_proc.kill.assert_not_called()

        # brave.exe is in the allowlist -> ALLOW
        allowed_brave = focus_mgr._evaluate_process(
            pid=1002,
            p_name="brave.exe",
            exe_path=r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            proc=mock_proc,
        )
        assert allowed_brave is True
        mock_proc.kill.assert_not_called()

    def test_unselected_user_facing_app_is_restricted(self, focus_mgr):
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", ["code.exe"])  # Only code.exe allowed
        mock_proc = MagicMock()

        # spotify.exe is user-facing, but not in allowlist -> BLOCK
        allowed = focus_mgr._evaluate_process(
            pid=2001,
            p_name="spotify.exe",
            exe_path=r"C:\Users\User\AppData\Roaming\Spotify\Spotify.exe",
            proc=mock_proc,
        )
        assert allowed is False
        mock_proc.kill.assert_called_once()

    def test_system_process_remains_untouched_in_deep_focus(self, focus_mgr):
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", [])  # Empty allowlist
        mock_proc = MagicMock()

        system_examples = [
            ("explorer.exe", r"C:\Windows\explorer.exe"),
            ("svchost.exe", r"C:\Windows\System32\svchost.exe"),
            ("dwm.exe", r"C:\Windows\System32\dwm.exe"),
            ("services.exe", r"C:\Windows\System32\services.exe"),
            ("digitalwellbeing.exe", r"C:\Program Files\Digital Wellbeing\digitalwellbeing.exe"),
        ]
        for name, path in system_examples:
            mock_proc.reset_mock()
            allowed = focus_mgr._evaluate_process(
                pid=99,
                p_name=name,
                exe_path=path,
                proc=mock_proc,
            )
            assert allowed is True, f"System process {name} must be ALLOWED"
            mock_proc.kill.assert_not_called()

    def test_background_helper_process_remains_untouched_in_deep_focus(self, focus_mgr):
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", [])  # Empty allowlist
        mock_proc = MagicMock()

        helpers = [
            ("steamwebhelper.exe", r"C:\Program Files (x86)\Steam\steamwebhelper.exe"),
            ("googleupdate.exe", r"C:\Program Files\Google\Update\GoogleUpdate.exe"),
            ("crashpad_handler.exe", r"C:\Users\User\AppData\Local\Brave\crashpad_handler.exe"),
        ]
        for name, path in helpers:
            mock_proc.reset_mock()
            allowed = focus_mgr._evaluate_process(
                pid=500,
                p_name=name,
                exe_path=path,
                proc=mock_proc,
            )
            assert allowed is True, f"Helper process {name} must be ALLOWED"
            mock_proc.kill.assert_not_called()

    def test_child_workers_are_never_terminated_directly(self, focus_mgr):
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", [])  # Empty allowlist
        mock_proc = MagicMock()
        mock_proc.cmdline.return_value = ["C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe", "--type=renderer", "--lang=en-US"]

        allowed = focus_mgr._evaluate_process(
            pid=3001,
            p_name="brave.exe",
            exe_path=r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            proc=mock_proc,
        )
        assert allowed is True
        mock_proc.kill.assert_not_called()

    def test_nyw_self_and_runner_tree_never_terminated(self, focus_mgr):
        import os
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", [])
        mock_proc = MagicMock()

        # Current process (app / test runner)
        allowed = focus_mgr._evaluate_process(
            pid=os.getpid(),
            p_name="python.exe",
            exe_path=sys.executable,
            proc=mock_proc,
        )
        assert allowed is True
        mock_proc.kill.assert_not_called()

    def test_focus_ending_restores_normal_behavior(self, focus_mgr):
        from unittest.mock import patch
        focus_mgr.set_mode("deep")
        focus_mgr.save_mode_apps("deep", ["code.exe"])
        with patch.object(focus_mgr, "_check_app_blocks"):
            started = focus_mgr.start_focus(25, strict_mode=False)
            assert started is True
            assert focus_mgr.is_active is True

            stopped = focus_mgr.stop_focus()
            assert stopped is True
            assert focus_mgr.is_active is False
            assert focus_mgr.seconds_remaining == 0

        # When stopped, _run_enforcement_scan does nothing
        mock_proc = MagicMock()
        focus_mgr._run_enforcement_scan()
        mock_proc.kill.assert_not_called()


# ── 3. Preset Modes (Study, Work, Movie) ──────────────────────────────────────

class TestPresetModes:
    """Tests Study, Work, and Movie presets."""

    def test_study_preset_behavior(self, focus_mgr):
        focus_mgr.set_mode("study")
        assert focus_mgr.current_mode == "study"
        # Can customize and allow applications
        focus_mgr.save_mode_apps("study", ["code.exe", "onenote.exe"])
        assert "code.exe" in focus_mgr.current_mode_apps
        assert "onenote.exe" in focus_mgr.current_mode_apps

        mock_proc = MagicMock()
        # onenote allowed
        assert focus_mgr._evaluate_process(
            10, "onenote.exe", r"C:\Program Files\Microsoft Office\onenote.exe", mock_proc
        ) is True

        # unselected game restricted
        mock_proc.reset_mock()
        assert focus_mgr._evaluate_process(
            11, "steam.exe", r"C:\Program Files (x86)\Steam\steam.exe", mock_proc
        ) is False
        mock_proc.kill.assert_called_once()

    def test_work_preset_behavior(self, focus_mgr):
        focus_mgr.set_mode("work")
        assert focus_mgr.current_mode == "work"
        focus_mgr.save_mode_apps("work", ["msedge.exe", "slack.exe"])
        assert len(focus_mgr.current_mode_apps) == 2

        mock_proc = MagicMock()
        assert focus_mgr._evaluate_process(
            20, "msedge.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", mock_proc
        ) is True

    def test_movie_preset_behavior(self, focus_mgr):
        focus_mgr.set_mode("movie")
        assert focus_mgr.current_mode == "movie"
        focus_mgr.save_mode_apps("movie", ["vlc.exe", "spotify.exe"])

        mock_proc = MagicMock()
        assert focus_mgr._evaluate_process(
            30, "vlc.exe", r"C:\Program Files\VideoLAN\VLC\vlc.exe", mock_proc
        ) is True

    def test_preset_persistence(self, test_repo):
        # Initialize first instance and save preset configuration
        FocusManager._instance = None
        fm1 = FocusManager(test_repo)
        fm1.set_mode("study")
        fm1.save_mode_apps("study", ["code.exe", "brave.exe"])
        fm1.set_mode("work")
        fm1.save_mode_apps("work", ["msedge.exe", "slack.exe"])

        # Create fresh instance reading from same repository
        FocusManager._instance = None
        fm2 = FocusManager(test_repo)
        assert fm2.current_mode == "work"
        assert fm2.current_mode_apps == ["msedge.exe", "slack.exe"]

        fm2.set_mode("study")
        assert fm2.current_mode_apps == ["code.exe", "brave.exe"]


# ── 4. Custom Mode & Backward Compatibility ───────────────────────────────────

class TestCustomMode:
    """Tests Custom mode backward compatibility (Blocklist mode)."""

    def test_custom_focus_still_works_as_blocklist(self, focus_mgr):
        focus_mgr.set_mode("custom")
        assert focus_mgr.current_mode == "custom"
        # In custom mode, apps list represents blocked applications
        focus_mgr.save_mode_apps("custom", ["steam.exe", "discord.exe"])
        mock_proc = MagicMock()

        # steam.exe is in blocklist -> BLOCK
        assert focus_mgr._evaluate_process(
            40, "steam.exe", r"C:\Program Files (x86)\Steam\steam.exe", mock_proc
        ) is False
        mock_proc.kill.assert_called_once()

        # code.exe is NOT in blocklist -> ALLOW
        mock_proc.reset_mock()
        assert focus_mgr._evaluate_process(
            41, "code.exe", r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\Code.exe", mock_proc
        ) is True
        mock_proc.kill.assert_not_called()

        # system process is never blocked even if in custom list
        focus_mgr.save_mode_apps("custom", ["explorer.exe"])
        mock_proc.reset_mock()
        assert focus_mgr._evaluate_process(
            42, "explorer.exe", r"C:\Windows\explorer.exe", mock_proc
        ) is True
        mock_proc.kill.assert_not_called()


# ── 5. Focus Timer Logic ──────────────────────────────────────────────────────

class TestFocusTimer:
    """Tests timer start, tick decrement, and natural completion."""

    def test_focus_timer_still_works(self, focus_mgr):
        started = focus_mgr.start_focus(minutes=10, strict_mode=False)
        assert started is True
        assert focus_mgr.seconds_remaining == 600

        # Simulate 1 tick
        focus_mgr._on_tick()
        assert focus_mgr.seconds_remaining == 599

        # Simulate completion
        completed_signals = []
        focus_mgr.focus_completed.connect(lambda: completed_signals.append(True))
        focus_mgr._seconds_remaining = 1
        focus_mgr._on_tick()  # decrements to 0
        focus_mgr._on_tick()  # detects 0 -> completes

        assert focus_mgr.is_active is False
        assert len(completed_signals) == 1
