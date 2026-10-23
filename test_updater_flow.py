import threading
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import hashlib
from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication

from utils.updater import Updater
from core.constants import APP_VERSION

FAKE_PORT = 8081

class FakeInstallerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/repos/") and self.path.endswith("/releases"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            mock_data = [
                {
                    "tag_name": "v9.9.9",
                    "draft": False,
                    "prerelease": False,
                    "body": "Update notes",
                    "assets": [
                        {"name": "DigitalWellbeingSetup-9.9.9.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/update.exe"},
                        {"name": "DigitalWellbeingSetup-9.9.9.exe.sha256", "browser_download_url": f"http://localhost:{FAKE_PORT}/update.exe.sha256"}
                    ]
                }
            ]
            self.wfile.write(json.dumps(mock_data).encode("utf-8"))
        elif self.path == "/update.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            fake_data = b"MZ" + b"0" * 1024
            self.send_header("Content-Length", str(len(fake_data)))
            self.end_headers()
            self.wfile.write(fake_data)
            self.server.fake_sha256 = hashlib.sha256(fake_data).hexdigest()
        elif self.path == "/update.exe.sha256":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(self.server.fake_sha256.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args): pass

@pytest.fixture(scope="module")
def fake_server():
    server = HTTPServer(("localhost", FAKE_PORT), FakeInstallerHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    
    os.environ["GITHUB_API_BASE"] = f"http://localhost:{FAKE_PORT}"
    os.environ["GITHUB_OWNER"] = "test-owner"
    import utils.updater
    utils.updater.GITHUB_OWNER = "test-owner"
    utils.updater.GITHUB_API_BASE = f"http://localhost:{FAKE_PORT}"
    
    # We need a QApplication instance for QObject signals and UI widgets to work
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])
        
    yield server
    server.shutdown()
    
    if "GITHUB_API_BASE" in os.environ:
        del os.environ["GITHUB_API_BASE"]
    if "GITHUB_OWNER" in os.environ:
        del os.environ["GITHUB_OWNER"]
    utils.updater.GITHUB_OWNER = ""

def test_updater_flow_check(fake_server):
    updater = Updater()
    
    received_update = []
    
    def on_update_available(info):
        received_update.append(info)
        
    updater.update_available.connect(on_update_available)
    
    # Run the check thread synchronously for testing
    updater._check_thread()
    
    assert len(received_update) == 1
    info = received_update[0]
    assert info["version"] == "v9.9.9"
    assert info["asset_url"] == f"http://localhost:{FAKE_PORT}/update.exe"

