"""
icon_provider.py — Utility to extract and cache application icons from executables.
"""

import os
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo
from database.repository import Repository

class AppIconProvider:
    _instance = None
    _cache: dict[str, QIcon] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._provider = QFileIconProvider()
            cls._instance._repo = Repository()
        return cls._instance

    def get_icon(self, process_name: str, exe_path: str = "") -> QIcon:
        """Get the cached icon for the given process name or executable path, or extract it."""
        cache_key = (exe_path or process_name).lower()
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        icon = self._extract_icon(process_name, exe_path)
        if not icon.isNull():
            self._cache[cache_key] = icon
        return icon
        
    def _extract_icon(self, process_name: str, exe_path: str = "") -> QIcon:
        # Direct extraction if valid executable path provided
        if exe_path and os.path.exists(exe_path):
            try:
                info = QFileInfo(exe_path)
                icon = self._provider.icon(info)
                if not icon.isNull():
                    return icon
            except Exception:
                pass

        # First, see if we have the full path in app_info
        app_info = self._repo.get_app_info(process_name)
        if not exe_path:
            exe_path = app_info.exe_path if app_info else ""
        
        # If no path from DB, try searching common locations (heuristic)
        if not exe_path or not os.path.exists(exe_path):
            import shutil
            found = shutil.which(process_name)
            if found:
                exe_path = found
            else:
                # Common hardcoded fallbacks
                common_paths = [
                    os.path.expandvars(f"%ProgramFiles%\\Google\\Chrome\\Application\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles(x86)%\\Google\\Chrome\\Application\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles%\\Mozilla Firefox\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles%\\Microsoft VS Code\\{process_name}"),
                    os.path.expandvars(f"%LocalAppData%\\Programs\\Microsoft VS Code\\{process_name}"),
                    os.path.expandvars(f"%LocalAppData%\\Discord\\app-*\\{process_name}"),
                    os.path.expandvars(f"%ProgramFiles(x86)%\\Steam\\{process_name}"),
                ]
                import glob
                for cp in common_paths:
                    matches = glob.glob(cp)
                    if matches and os.path.exists(matches[0]):
                        exe_path = matches[0]
                        break

        # If we finally have a valid path, extract
        if exe_path and os.path.exists(exe_path):
            try:
                info = QFileInfo(exe_path)
                return self._provider.icon(info)
            except Exception:
                pass
            
        # Fallback to default Windows executable/file icon
        return self._provider.icon(QFileIconProvider.IconType.File)
