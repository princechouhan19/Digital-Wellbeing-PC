"""
extension_bridge.py — Loopback-only bridge for the optional browser extension.

The extension is the only reliable way to see a full URL (including sub-path)
for every Chromium/Firefox tab. This server exposes exactly two endpoints on
127.0.0.1:

    GET  /v1/health          -> bridge status
    POST /v1/check           -> {"action": "allow"|"block", "reason": ...}

Security / privacy:
* Bound to loopback only; never exposed to the LAN.
* Requires a per-install bearer token (stored in the local SQLite settings).
* URLs are evaluated in memory and are not logged or persisted.
* The extension sends a URL only when it changes; no browsing history upload.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from core.logger import logger

_MAX_BODY_BYTES = 12 * 1024
_DEFAULT_PORT = 47823
_TOKEN_SETTING = "extension_bridge_token"
_PORT_SETTING = "extension_bridge_port"


class _Handler(BaseHTTPRequestHandler):
    server_version = "DigitalWellbeingBridge/1.0"
    protocol_version = "HTTP/1.1"

    # ── helpers ────────────────────────────────────────────────────────────

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-DW-Token")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self._cors()
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003 - stdlib hook
        # Deliberately silent: URLs must never leak into logs.
        return

    def _authorized(self) -> bool:
        bridge: "ExtensionBridge" = self.server.bridge  # type: ignore[attr-defined]
        token = self.headers.get("X-DW-Token", "").strip()
        return bool(token) and token == bridge.token

    # ── routes ─────────────────────────────────────────────────────────────

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib hook
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook
        bridge: "ExtensionBridge" = self.server.bridge  # type: ignore[attr-defined]
        if self.path.split("?")[0] == "/v1/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "digital-wellbeing",
                    "version": 1,
                    "port": bridge.port,
                },
            )
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook
        if self.path.split("?")[0] != "/v1/check":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"ok": False, "error": "invalid token"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > _MAX_BODY_BYTES:
            self._send_json(413, {"ok": False, "error": "invalid body size"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"ok": False, "error": "invalid json"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"ok": False, "error": "invalid payload"})
            return

        url = str(payload.get("url", ""))[:4096]
        browser = str(payload.get("browser", ""))[:80]
        title = str(payload.get("title", ""))[:512]

        bridge = self.server.bridge  # type: ignore[attr-defined]
        result = bridge.evaluate(url, browser=browser, title=title)
        self._send_json(200, result)


class ExtensionBridge:
    """Singleton HTTP bridge; safe to start before the UI is ready."""

    _instance: Optional["ExtensionBridge"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def instance(cls) -> "ExtensionBridge":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._provider: Optional[Callable[[str], dict]] = None
        self._latest: dict[str, dict] = {}
        self.port = 0
        self.token = ""
        self.last_error = ""

    # ── configuration ──────────────────────────────────────────────────────

    def _ensure_credentials(self) -> None:
        from database.repository import Repository

        repo = Repository()
        token = repo.get_setting(_TOKEN_SETTING) or ""
        if not token:
            token = uuid.uuid4().hex
            repo.set_setting(_TOKEN_SETTING, token)
        stored_port = repo.get_setting(_PORT_SETTING) or str(_DEFAULT_PORT)
        try:
            self._preferred_port = int(stored_port)
        except ValueError:
            self._preferred_port = _DEFAULT_PORT
        self.token = token

    def set_decision_provider(self, provider: Callable[[str], dict]) -> None:
        self._provider = provider

    def evaluate(self, url: str, browser: str = "", title: str = "") -> dict:
        if self._provider is None:
            return {"ok": True, "action": "allow", "reason": "Focus engine not ready"}
        try:
            result = dict(self._provider(url))
        except Exception as exc:
            logger.debug("[EXT_BRIDGE] decision provider failed: %s", exc)
            return {"ok": True, "action": "allow", "reason": "decision error"}

        with self._lock:
            self._latest[(browser or "extension").lower()] = {
                "url": url[:4096],
                "title": title,
                "at": time.monotonic(),
            }
            # Keep the map bounded (a handful of browsers at most).
            if len(self._latest) > 16:
                self._latest.pop(next(iter(self._latest)))
        result.setdefault("ok", True)
        return result

    def latest_url(self, browser: str = "", max_age_s: float = 15.0) -> str:
        now = time.monotonic()
        with self._lock:
            if browser:
                entry = self._latest.get(browser.lower())
                if entry and now - entry.get("at", 0.0) <= max_age_s:
                    return entry.get("url", "")
            if not self._latest:
                return ""
            entry = next(reversed(self._latest.values()))
            if now - entry.get("at", 0.0) > max_age_s:
                return ""
            return entry.get("url", "")

    # ── lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        if self._server is not None:
            return True
        self._ensure_credentials()
        ports = [self._preferred_port, 0]
        for port in ports:
            try:
                server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            except OSError as exc:
                self.last_error = str(exc)
                continue
            server.daemon_threads = True
            server.bridge = self  # type: ignore[attr-defined]
            self._server = server
            self.port = int(server.server_address[1])
            try:
                from database.repository import Repository

                Repository().set_setting(_PORT_SETTING, str(self.port))
            except Exception:
                pass
            self._thread = threading.Thread(
                target=server.serve_forever,
                name="ExtensionBridge",
                daemon=True,
            )
            self._thread.start()
            logger.info("[EXT_BRIDGE] Listening on 127.0.0.1:%d", self.port)
            return True
        logger.warning("[EXT_BRIDGE] Could not start loopback server: %s", self.last_error)
        return False

    def stop(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("[EXT_BRIDGE] Stopped")

    @property
    def is_running(self) -> bool:
        return self._server is not None

    def connection_info(self) -> dict:
        return {
            "running": self.is_running,
            "port": self.port,
            "token": self.token,
            "last_error": self.last_error,
        }
