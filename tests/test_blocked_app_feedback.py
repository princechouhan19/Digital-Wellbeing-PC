"""
test_blocked_app_feedback.py — Tests for Focus Mode blocked-application feedback and anti-spam rate limiting.
"""

import time
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
import pytest

from protection.focus_manager import FocusManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestBlockedAppFeedback:
    def test_signal_emission_and_rate_limiting(self, qapp):
        """Verify app_blocked signal emits on blocked application with proper cooldown."""
        fm = FocusManager.instance()
        
        received_signals = []
        def on_blocked(app_name, mode_name, remaining_secs):
            received_signals.append((app_name, mode_name, remaining_secs))

        fm.app_blocked.connect(on_blocked)
        
        # Reset cooldown tracking
        fm._last_blocked_feedback.clear()

        mock_proc = MagicMock()

        # Emit for discord.exe
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received_signals) == 1
        assert received_signals[0][0] == "discord.exe"

        # Immediate repeated call should be rate-limited (no spam)
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received_signals) == 1

        # Different app should NOT be blocked by discord's cooldown
        fm._handle_blocked_app(mock_proc, "steam.exe")
        assert len(received_signals) == 2
        assert received_signals[1][0] == "steam.exe"

        # After cooldown passes (simulate by adjusting timestamp)
        fm._last_blocked_feedback["discord.exe"] = time.time() - 10.0
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received_signals) == 3
        assert received_signals[2][0] == "discord.exe"

        fm.app_blocked.disconnect(on_blocked)

    def test_blocked_app_dialog_initialization(self, qapp):
        """Verify BlockedAppFeedbackDialog initializes properly with friendly names and remaining time."""
        from ui.widgets.blocked_app_dialog import BlockedAppFeedbackDialog
        
        dlg = BlockedAppFeedbackDialog(
            process_name="discord.exe",
            mode_name="Deep Focus",
            seconds_remaining=1500
        )
        assert dlg.windowTitle() == "App Blocked by Focus"
        assert dlg.process_name == "discord.exe"
        assert dlg.mode_name == "Deep Focus"
        assert dlg.seconds_remaining == 1500

    def test_suppression_on_back_to_focus(self, qapp):
        """Verify suppress_blocked_app prevents repeated popup emissions during suppression window."""
        fm = FocusManager.instance()
        fm._last_blocked_feedback.clear()
        fm._suppressed_blocked_apps.clear()

        received = []
        def on_blocked(app, mode, rem):
            received.append(app)

        fm.app_blocked.connect(on_blocked)
        mock_proc = MagicMock()

        # Normal emission
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received) == 1

        # User clicked 'Back to Focus' -> engage suppression for 10 seconds
        fm.suppress_blocked_app("discord.exe", duration=10.0)

        # Immediate tick should be suppressed
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received) == 1, "Should be suppressed after user clicks Back to Focus"

        # Even after standard 6s debounce passes, suppression window still holds
        fm._last_blocked_feedback["discord.exe"] = time.time() - 8.0
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received) == 1, "Must remain suppressed while suppression window is active"

        # Once suppression expires, genuine attempts emit again
        fm._suppressed_blocked_apps["discord.exe"] = time.time() - 1.0
        fm._last_blocked_feedback["discord.exe"] = time.time() - 10.0
        fm._handle_blocked_app(mock_proc, "discord.exe")
        assert len(received) == 2, "Should emit again after suppression window expires"

        fm.app_blocked.disconnect(on_blocked)

    def test_screenshot_utilities_protected(self):
        """Verify Windows Snipping Tool and screen clipping hosts are protected and never blocked."""
        from protection.app_locker import SYSTEM_SAFE
        from utils.win_utils import is_safe_lock_target, is_user_facing_application

        # SYSTEM_SAFE membership
        assert "snippingtool.exe" in SYSTEM_SAFE
        assert "screenclippinghost.exe" in SYSTEM_SAFE
        assert "shellexperiencehost.exe" in SYSTEM_SAFE

        # is_safe_lock_target rejects WindowsApps ScreenSketch package
        snip_path = r"C:\Program Files\WindowsApps\Microsoft.ScreenSketch_11.2607.23.0_x64__8wekyb3d8bbwe\SnippingTool\SnippingTool.exe"
        assert is_safe_lock_target(snip_path, "snippingtool.exe") is False

        clip_path = r"C:\Windows\SystemApps\MicrosoftWindows.Client.Core_cw5n1h2txyewy\ScreenClippingHost.exe"
        assert is_safe_lock_target(clip_path, "screenclippinghost.exe") is False

        # is_user_facing_application returns False
        assert is_user_facing_application(None, snip_path, "snippingtool.exe") is False
        assert is_user_facing_application(None, clip_path, "screenclippinghost.exe") is False

        # FocusManager._evaluate_process permits screenshot utility unconditionally
        fm = FocusManager.instance()
        fm.set_mode("study")
        mock_proc = MagicMock()
        allowed = fm._evaluate_process(8888, "snippingtool.exe", snip_path, mock_proc)
        assert allowed is True, "Snipping Tool must ALWAYS be allowed in Focus Mode"
        mock_proc.kill.assert_not_called()

    def test_hp_system_management_oem_classification(self):
        """Verify OEM hardware / thermal helpers (HP SystemManagement) are classified as protected/non-user-facing."""
        from utils.win_utils import is_safe_lock_target, is_user_facing_application

        hp_path = r"C:\Program Files\WindowsApps\AD2F1837.HPThermalControl_1.11.60.0_x64__v10z8vjag6ke6\HpSystemManagement.exe"

        # Protected from locking / blocking by OEM package detection
        assert is_safe_lock_target(hp_path, "hpsystemmanagement.exe") is False

        # Discovered as non-user-facing application
        assert is_user_facing_application(None, hp_path, "hpsystemmanagement.exe") is False

        # DCOM server inspection with -ServerName:
        mock_psutil_proc = MagicMock()
        mock_psutil_proc.cmdline.return_value = [hp_path, "-ServerName:App.AppXmcvs2p9zyves5qdatny8ncvx7p1ttnbe.mca"]
        mock_parent = MagicMock()
        mock_parent.name.return_value = "svchost.exe"
        mock_psutil_proc.parent.return_value = mock_parent

        with patch("psutil.Process", return_value=mock_psutil_proc):
            assert is_user_facing_application(22752, hp_path, "hpsystemmanagement.exe") is False

        # FocusManager._evaluate_process permits HP SystemManagement
        fm = FocusManager.instance()
        fm.set_mode("study")
        mock_proc = MagicMock()
        allowed = fm._evaluate_process(22752, "hpsystemmanagement.exe", hp_path, mock_proc)
        assert allowed is True, "HP SystemManagement must NEVER be blocked"
        mock_proc.kill.assert_not_called()


class TestProcessClassificationRegressionMatrix:
    """
    Comprehensive regression matrix validating the 4-tier process classification
    architecture, application process tree inheritance, and desktop window requirement:
      1. Real unallowed user-facing apps (Discord, Epic Games) are blocked.
      2. Allowed user-facing apps (Chrome, VS Code) remain usable.
      3. Multi-process child/helper processes are not independently killed.
      4. Language servers (LSPs) remain alive.
      5. IDE extension hosts, MCP tools, and watchers remain alive.
      6. Windows screenshot utilities remain alive.
      7. HP/OEM hardware services remain alive.
      8. Blocked app popup only appears for the user-facing blocked application.
      9. 'Back to Focus' suppression prevents repeated popup loops.
    """

    def test_discord_unallowed_blocks_root_only(self, qapp):
        """Verify unallowed Discord blocks the user-facing root application and does not alert child helpers."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", ["code.exe"])
        fm._last_blocked_feedback.clear()
        fm._suppressed_blocked_apps.clear()

        signals = []
        def on_blocked(app, mode, rem):
            signals.append(app)
        fm.app_blocked.connect(on_blocked)

        # Root Discord process (owns visible desktop window)
        mock_root = MagicMock()
        mock_root.name.return_value = "Discord.exe"
        mock_root.cmdline.return_value = [r"C:\Users\User\AppData\Local\Discord\app-1.0.9000\Discord.exe"]
        mock_root.parents.return_value = []

        visible_pids = {24424}
        allowed = fm._evaluate_process(
            pid=24424,
            p_name="Discord.exe",
            exe_path=r"C:\Users\User\AppData\Local\Discord\app-1.0.9000\Discord.exe",
            proc=mock_root,
            visible_pids=visible_pids,
            is_foreground=True,
        )
        assert allowed is False
        mock_root.kill.assert_called_once()
        assert signals == ["discord.exe"]

        # Child Discord renderer (no desktop window, child of root)
        mock_child = MagicMock()
        mock_child.name.return_value = "Discord.exe"
        mock_child.cmdline.return_value = [r"C:\Users\User\AppData\Local\Discord\app-1.0.9000\Discord.exe", "--type=renderer"]
        mock_child.parents.return_value = [mock_root]

        child_allowed = fm._evaluate_process(
            pid=28416,
            p_name="Discord.exe",
            exe_path=r"C:\Users\User\AppData\Local\Discord\app-1.0.9000\Discord.exe",
            proc=mock_child,
            visible_pids=visible_pids,
            is_foreground=False,
        )
        # Child process is NOT independently targeted
        assert child_allowed is True
        mock_child.kill.assert_not_called()
        # No additional signals emitted for child
        assert len(signals) == 1

        fm.app_blocked.disconnect(on_blocked)

    def test_epic_games_launcher_blocked_helper_ignored(self, qapp):
        """Verify Epic Games Launcher is blocked while EpicWebHelper is not independently alerted."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", ["code.exe"])
        fm._last_blocked_feedback.clear()

        signals = []
        def on_blocked(app, mode, rem):
            signals.append(app)
        fm.app_blocked.connect(on_blocked)

        mock_root = MagicMock()
        mock_root.name.return_value = "EpicGamesLauncher.exe"
        mock_root.parents.return_value = []

        # Root owns visible window
        visible_pids = {5001}
        allowed = fm._evaluate_process(
            pid=5001,
            p_name="EpicGamesLauncher.exe",
            exe_path=r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
            proc=mock_root,
            visible_pids=visible_pids,
            is_foreground=True,
        )
        assert allowed is False
        mock_root.kill.assert_called_once()
        assert signals == ["epicgameslauncher.exe"]

        # Child EpicWebHelper has no visible window
        mock_helper = MagicMock()
        mock_helper.name.return_value = "EpicWebHelper.exe"
        mock_helper.parents.return_value = [mock_root]

        helper_allowed = fm._evaluate_process(
            pid=5002,
            p_name="EpicWebHelper.exe",
            exe_path=r"C:\Program Files (x86)\Epic Games\Launcher\Engine\Binaries\Win64\EpicWebHelper.exe",
            proc=mock_helper,
            visible_pids=visible_pids,
            is_foreground=False,
        )
        assert helper_allowed is True
        mock_helper.kill.assert_not_called()
        assert len(signals) == 1

        fm.app_blocked.disconnect(on_blocked)

    def test_chrome_allowed_and_descendants_inherit(self, qapp):
        """Verify that when Chrome is allowed, all helper and renderer children inherit allowed status."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", ["chrome.exe"])

        mock_root = MagicMock()
        mock_root.name.return_value = "chrome.exe"
        mock_root.parents.return_value = []

        visible_pids = {6001}
        # Chrome main browser window
        assert fm._evaluate_process(
            pid=6001,
            p_name="chrome.exe",
            exe_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            proc=mock_root,
            visible_pids=visible_pids,
            is_foreground=True,
        ) is True
        mock_root.kill.assert_not_called()

        # Chrome renderer child
        mock_renderer = MagicMock()
        mock_renderer.name.return_value = "chrome.exe"
        mock_renderer.cmdline.return_value = ["chrome.exe", "--type=renderer"]
        mock_renderer.parents.return_value = [mock_root]
        assert fm._evaluate_process(
            pid=6002,
            p_name="chrome.exe",
            exe_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            proc=mock_renderer,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_renderer.kill.assert_not_called()

        # Chrome network utility child
        mock_utility = MagicMock()
        mock_utility.name.return_value = "chrome.exe"
        mock_utility.cmdline.return_value = ["chrome.exe", "--type=utility"]
        mock_utility.parents.return_value = [mock_root]
        assert fm._evaluate_process(
            pid=6003,
            p_name="chrome.exe",
            exe_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            proc=mock_utility,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_utility.kill.assert_not_called()

    def test_vscode_and_language_server_infrastructure_remains_alive(self, qapp):
        """Verify that VS Code and its entire background development infrastructure (LSPs, MCPs, watchers) remain alive."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", ["code.exe"])

        # Main editor process
        mock_editor = MagicMock()
        mock_editor.name.return_value = "Code.exe"
        mock_editor.parents.return_value = []

        visible_pids = {7001}
        assert fm._evaluate_process(
            pid=7001,
            p_name="Code.exe",
            exe_path=r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            proc=mock_editor,
            visible_pids=visible_pids,
            is_foreground=True,
        ) is True
        mock_editor.kill.assert_not_called()

        # Extension Host child
        mock_exthost = MagicMock()
        mock_exthost.name.return_value = "Code.exe"
        mock_exthost.cmdline.return_value = ["Code.exe", "--type=extensionHost"]
        mock_exthost.parents.return_value = [mock_editor]
        assert fm._evaluate_process(
            pid=7002,
            p_name="Code.exe",
            exe_path=r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\Code.exe",
            proc=mock_exthost,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_exthost.kill.assert_not_called()

        # Language Server (language_server_windows_x64.exe) child of editor
        mock_lsp = MagicMock()
        mock_lsp.name.return_value = "language_server_windows_x64.exe"
        mock_lsp.cmdline.return_value = ["language_server_windows_x64.exe", "--enable_lsp"]
        mock_lsp.parents.return_value = [mock_editor]
        assert fm._evaluate_process(
            pid=7003,
            p_name="language_server_windows_x64.exe",
            exe_path=r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\bin\language_server_windows_x64.exe",
            proc=mock_lsp,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_lsp.kill.assert_not_called()

        # Pyrefly Python LSP child of editor
        mock_pyrefly = MagicMock()
        mock_pyrefly.name.return_value = "pyrefly.exe"
        mock_pyrefly.cmdline.return_value = ["pyrefly.exe", "lsp"]
        mock_pyrefly.parents.return_value = [mock_editor]
        assert fm._evaluate_process(
            pid=7004,
            p_name="pyrefly.exe",
            exe_path=r"C:\Users\User\.vscode\extensions\meta.pyrefly\bin\pyrefly.exe",
            proc=mock_pyrefly,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_pyrefly.kill.assert_not_called()

        # Node MCP Tool child of language server
        mock_node_mcp = MagicMock()
        mock_node_mcp.name.return_value = "node.exe"
        mock_node_mcp.cmdline.return_value = ["node.exe", "chrome-devtools-mcp.js"]
        mock_node_mcp.parents.return_value = [mock_lsp, mock_editor]
        assert fm._evaluate_process(
            pid=7005,
            p_name="node.exe",
            exe_path=r"C:\Program Files\nodejs\node.exe",
            proc=mock_node_mcp,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_node_mcp.kill.assert_not_called()

        # File watcher child of editor
        mock_watcher = MagicMock()
        mock_watcher.name.return_value = "watcher.exe"
        mock_watcher.cmdline.return_value = ["watcher.exe"]
        mock_watcher.parents.return_value = [mock_editor]
        assert fm._evaluate_process(
            pid=7006,
            p_name="watcher.exe",
            exe_path=r"C:\Users\User\AppData\Local\Programs\Microsoft VS Code\watcher.exe",
            proc=mock_watcher,
            visible_pids=visible_pids,
            is_foreground=False,
        ) is True
        mock_watcher.kill.assert_not_called()

    def test_generic_unknown_background_process_not_killed_by_default(self, qapp):
        """Verify an unknown non-interactive background process is not killed by default."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", ["code.exe"])

        mock_unknown = MagicMock()
        mock_unknown.name.return_value = "sync_daemon.exe"
        mock_unknown.cmdline.return_value = ["sync_daemon.exe", "--background"]
        mock_unknown.parents.return_value = []

        # Process does NOT own an interactive desktop window (not in visible_pids)
        visible_pids = {1000, 2000}
        allowed = fm._evaluate_process(
            pid=9901,
            p_name="sync_daemon.exe",
            exe_path=r"C:\Program Files\SyncApp\sync_daemon.exe",
            proc=mock_unknown,
            visible_pids=visible_pids,
            is_foreground=False,
        )
        assert allowed is True
        mock_unknown.kill.assert_not_called()

    def test_shell_processes_protected_in_all_modes(self, qapp):
        """Verify Windows shell and desktop host processes are never blocked."""
        fm = FocusManager.instance()
        fm.set_mode("study")
        fm.save_mode_apps("study", [])

        shell_procs = ["explorer.exe", "SearchHost.exe", "taskhostw.exe", "dwm.exe"]
        for sp in shell_procs:
            mock_proc = MagicMock()
            mock_proc.name.return_value = sp
            mock_proc.parents.return_value = []
            allowed = fm._evaluate_process(
                pid=100,
                p_name=sp,
                exe_path=f"C:\\Windows\\{sp}",
                proc=mock_proc,
                visible_pids={100},
                is_foreground=True,
            )
            assert allowed is True, f"{sp} must never be blocked"
            mock_proc.kill.assert_not_called()

