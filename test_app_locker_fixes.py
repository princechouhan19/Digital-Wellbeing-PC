import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
from PySide6.QtWidgets import QApplication

def setup_module(module):
    if not QApplication.instance():
        app = QApplication(sys.argv)

from utils.win_utils import is_safe_lock_target, is_user_facing_application
from ui.widgets.protection_section import ProtectionSection
from protection.core import ProtectionManager
from database.repository import Repository
import os

def test_is_safe_lock_target():
    # Valid apps
    assert is_safe_lock_target("C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe", "brave.exe") is True
    assert is_safe_lock_target("D:\\Games\\Steam\\steam.exe", "steam.exe") is True

    # Invalid apps
    assert is_safe_lock_target("C:\\Windows\\System32\\cmd.exe", "cmd.exe") is False
    assert is_safe_lock_target("C:\\Windows\\explorer.exe", "explorer.exe") is False
    assert is_safe_lock_target("C:\\ProgramData\\SomeService\\service.exe", "service.exe") is False
    assert is_safe_lock_target("C:\\Program Files\\App\\app.dll", "app.dll") is False
    assert is_safe_lock_target("C:\\App\\digitalwellbeing.exe", "digitalwellbeing.exe") is False
    
    # System apps defined in SYSTEM_SAFE
    assert is_safe_lock_target("C:\\Program Files\\App\\dwm.exe", "dwm.exe") is False

@patch("utils.win_utils.get_session_id")
def test_is_user_facing_application(mock_get_session_id):
    # Session 1 = User session, Session 0 = Service session
    
    # 1. Normal user apps (Session 1)
    mock_get_session_id.return_value = 1
    assert is_user_facing_application(1234, "C:\\Program Files\\App\\app.exe", "app.exe") is True
    assert is_user_facing_application(1235, "C:\\AppData\\Local\\Discord\\discord.exe", "discord.exe") is True
    
    # 2. Service apps (Session 0)
    mock_get_session_id.return_value = 0
    assert is_user_facing_application(9999, "C:\\Program Files\\App\\app.exe", "app.exe") is False
    
    # 3. Known infrastructure processes
    mock_get_session_id.return_value = 1
    assert is_user_facing_application(100, "C:\\Windows\\System32\\svchost.exe", "svchost.exe") is False
    assert is_user_facing_application(101, "C:\\Windows\\explorer.exe", "explorer.exe") is False
    assert is_user_facing_application(102, "C:\\Windows\\System32\\taskhostw.exe", "taskhostw.exe") is False
    
    # 4. Helper/tray patterns explicitly tested (filename matches)
    assert is_user_facing_application(200, "C:\\App\\updater.exe", "updater.exe") is False
    assert is_user_facing_application(201, "C:\\App\\helper.exe", "helper.exe") is False
    assert is_user_facing_application(202, "C:\\App\\crashpad.exe", "crashpad.exe") is False
    assert is_user_facing_application(203, "C:\\App\\omeninstallmonitor.exe", "omeninstallmonitor.exe") is False
    assert is_user_facing_application(204, "C:\\App\\officeclicktorun.exe", "officeclicktorun.exe") is False
    assert is_user_facing_application(205, "C:\\App\\servicehost.exe", "servicehost.exe") is False
    
    # 5. Specific exclusions required by user
    assert is_user_facing_application(300, "C:\\Program Files\\HP\\hpcommrecovery.exe", "hpcommrecovery.exe") is False
    assert is_user_facing_application(301, "C:\\Program Files\\HP\\hpprintscandoctorservice.exe", "hpprintscandoctorservice.exe") is False
    assert is_user_facing_application(302, "C:\\Program Files\\VG\\vgtray.exe", "vgtray.exe") is False
    assert is_user_facing_application(303, "C:\\Program Files\\Java\\jusched.exe", "jusched.exe") is False
    
    # 6. Test visible window override
    # If a process normally matches a background suffix (e.g. some game named "ghost.exe")
    # but it has a visible window, it should be ACCEPTED.
    visible_pids = {400}
    assert is_user_facing_application(400, "C:\\App\\ghost.exe", "ghost.exe", visible_pids) is True
    # Without visible window, "host.exe" suffix is rejected
    assert is_user_facing_application(400, "C:\\App\\ghost.exe", "ghost.exe") is False

@patch("win32api.GetFileVersionInfo")
@patch("utils.win_utils.get_session_id")
def test_is_user_facing_metadata_blocking(mock_get_session_id, mock_get_file_info):
    mock_get_session_id.return_value = 1
    # Mocking win32api to return a description containing "proxy"
    # The classification should block it even if filename is innocent
    
    def fake_get_file_info(path, subblock):
        if subblock == "\\": return True
        if "Translation" in subblock: return [(1033, 1200)]
        if "FileDescription" in subblock: return "McAfee WebAdvisor(browser proxy)"
        return None
        
    mock_get_file_info.side_effect = fake_get_file_info
    
    # "innocent.exe" has "proxy" in its metadata description
    assert is_user_facing_application(500, "C:\\App\\innocent.exe", "innocent.exe") is False

def test_protection_section_requires_auth_on_disable(tmp_path):
    import tempfile
    db_path = tmp_path / "focus_test.db"
    
    Repository.set_db_path_override(db_path)
    section = None
    try:
        repo = Repository()
        pm = ProtectionManager(repo)
        
        # Setup PIN
        pm.pin.set_pin("1234")
        assert pm.pin.is_enabled() is True
        
        section = ProtectionSection(pm)
        
        # Mock AppLockerAuthDialog to return Rejected (simulating user canceling/failing auth)
        with patch("ui.widgets.auth_dialog.AppLockerAuthDialog.exec") as mock_exec:
            from PySide6.QtWidgets import QDialog
            mock_exec.return_value = QDialog.DialogCode.Rejected
            
            # Click disable button
            section._on_disable()
            
            # Verify PIN is STILL enabled (because auth failed)
            assert pm.pin.is_enabled() is True
            mock_exec.assert_called_once()
            
        # Mock AppLockerAuthDialog to return Accepted (simulating successful auth)
        with patch("ui.widgets.auth_dialog.AppLockerAuthDialog.exec") as mock_exec:
            from PySide6.QtWidgets import QDialog
            mock_exec.return_value = QDialog.DialogCode.Accepted
            
            with patch("ui.widgets.protection_section.QMessageBox.information"):
                # Click disable button
                section._on_disable()
                
                # Verify PIN is now disabled
                assert pm.pin.is_enabled() is False
                mock_exec.assert_called_once()
    finally:
        if section is not None:
            section.deleteLater()
        QApplication.processEvents()
        Repository.set_db_path_override(None)
