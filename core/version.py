import json
import os
from pathlib import Path

_CACHED_VERSION = None

def get_version() -> str:
    global _CACHED_VERSION
    if _CACHED_VERSION is not None:
        return _CACHED_VERSION

    try:
        # In the PyInstaller bundle, _MEIPASS points to the root directory
        import sys
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            # We are running from source
            base_path = Path(__file__).parent.parent
            
        version_file = base_path / "version.json"
        
        with open(version_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _CACHED_VERSION = data.get("version", "Unknown")
            return _CACHED_VERSION
    except Exception:
        return "Unknown"
