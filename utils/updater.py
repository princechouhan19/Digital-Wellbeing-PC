from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Signal

from core.constants import APP_NAME, APP_VERSION
from core.logger import logger
from settings.manager import SettingsManager

GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "princechouhan19")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Digital-Wellbeing-PC")
GITHUB_API_BASE = os.environ.get("GITHUB_API_BASE", "https://api.github.com")


def parse_semver(v: Optional[str]) -> Optional[Tuple[int, ...]]:
    """Parse a semantic version string into a numeric tuple (e.g. (3, 6, 1)).
    Returns None if the string is empty, malformed, or unparseable.
    """
    if not v or not isinstance(v, str):
        return None
    cleaned = v.strip().lstrip("vV")
    if not cleaned:
        return None
    # Strip any prerelease or build metadata (e.g. 3.6.1-beta.1 -> 3.6.1)
    core = re.split(r"[-+]", cleaned, maxsplit=1)[0].strip()
    parts = core.split(".")
    nums = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
        else:
            return None
    if not nums:
        return None
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


class Updater(QObject):
    """Secure, robust GitHub Releases based updater for Digital Wellbeing.

    - Non-blocking check_for_updates() queries GitHub Releases.
    - Accurately compares versions via semantic versioning.
    - Downloads installer to dedicated temporary update directory.
    - Verifies SHA-256 checksum against asset digest or .sha256 companion file.
    - Hands off execution to verified Inno Setup installer via detached wrapper.
    - Gracefully handles network failures without blocking normal app functionality.
    """

    update_available = Signal(object)  # dict with release and asset details
    no_update = Signal()
    error = Signal(str)
    download_progress = Signal(int)  # 0-100 percent
    download_complete = Signal(str)  # verified installer local path
    installing = Signal(str)  # target version string

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._sm = SettingsManager()
        self._checking = threading.Event()
        self._download_lock = threading.Lock()
        self._is_downloading = False
        self._download_thread: Optional[threading.Thread] = None
        self._current_version = APP_VERSION
        self._api_base = os.environ.get("GITHUB_API_BASE", GITHUB_API_BASE)
        token_env = os.environ.get("GITHUB_TOKEN")
        token_setting = self._sm.get("github_token", "")
        self._token = token_env or (token_setting if token_setting else None)

    @property
    def current_version(self) -> str:
        return self._current_version

    def _compare_versions(self, a: str, b: str) -> int:
        """Return -1 if a<b, 0 if equal, 1 if a>b. Numeric-semver compare.
        Non-numeric parts fall back to lexical compare.
        Treat empty/Unknown as older than any real version.
        """
        if not a or str(a).strip().lower() == "unknown":
            if not b or str(b).strip().lower() == "unknown":
                return 0
            return -1
        if not b or str(b).strip().lower() == "unknown":
            return 1

        def norm(v: str):
            clean = str(v).replace("v", "").replace("V", "").strip()
            # Separate prerelease suffix like -beta
            core = re.split(r"[-+]", clean, maxsplit=1)[0]
            return [int(x) if x.isdigit() else x for x in core.split(".") if x]

        try:
            na = norm(str(a))
            nb = norm(str(b))
            for x, y in zip(na, nb):
                if x == y:
                    continue
                try:
                    return 1 if x > y else -1
                except Exception:
                    return 1 if str(x) > str(y) else -1
            if len(na) == len(nb):
                return 0
            return 1 if len(na) > len(nb) else -1
        except Exception:
            try:
                if str(a) == str(b):
                    return 0
                return 1 if str(a) > str(b) else -1
            except Exception:
                return 0

    def check_for_updates(self, force: bool = False) -> None:
        """Initiate background update check if enabled or forced."""
        if not force and not self._sm.auto_update_enabled:
            logger.info("Updater: Automatic update checks disabled in user settings.")
            return

        if self._checking.is_set():
            logger.info("Updater: Check already in progress, skipping duplicate request.")
            return

        t = threading.Thread(target=self._check_thread, name="DW-Updater-Check", daemon=True)
        t.start()

    def _check_thread(self) -> None:
        self._checking.set()
        try:
            if not GITHUB_OWNER:
                logger.info("Updater: No remote update repository configured. Skipping update check.")
                self.no_update.emit()
                return

            logger.info("Updater: checking for updates... Current version: %s", self._current_version)
            headers = {"User-Agent": f"{APP_NAME}-Updater/{self._current_version}"}
            if self._token:
                headers["Authorization"] = f"token {self._token}"

            releases_url = f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
            req = Request(releases_url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.load(resp)

            # Handle both list (from /releases) and single object (from /releases/latest)
            releases_list = data if isinstance(data, list) else [data]

            best_release = None
            best_version = self._current_version

            for release in releases_list:
                if not isinstance(release, dict):
                    continue
                if release.get("draft") or release.get("prerelease"):
                    continue

                tag = str(release.get("tag_name") or release.get("name") or "").strip()
                if not tag:
                    continue

                if self._compare_versions(best_version, tag) < 0:
                    best_version = tag
                    best_release = release

            if not best_release or self._compare_versions(self._current_version, best_version) >= 0:
                logger.info("Updater: application is up to date (current: %s, latest: %s)", self._current_version, best_version)
                self.no_update.emit()
                return

            logger.info("Updater: newer version detected: %s (current: %s)", best_version, self._current_version)

            # Locate the Windows installer asset:
            #   1. DigitalWellbeingSetup-*.exe (current naming)
            #   2. any *Setup*.exe (covers installers published by older releases)
            #   3. any .exe asset
            assets = best_release.get("assets", []) or []
            chosen_installer = None

            for a in assets:
                name = a.get("name", "")
                if re.match(r"^DigitalWellbeingSetup.*\.exe$", name, re.IGNORECASE):
                    chosen_installer = a
                    break

            if not chosen_installer:
                for a in assets:
                    name = a.get("name", "")
                    if re.match(r"^.*Setup.*\.exe$", name, re.IGNORECASE):
                        chosen_installer = a
                        break

            if not chosen_installer:
                for a in assets:
                    if a.get("name", "").lower().endswith(".exe"):
                        chosen_installer = a
                        break

            if not chosen_installer:
                logger.warning("Updater: Release %s found but contains no executable installer asset.", best_version)
                self.error.emit("No suitable installer asset found in release")
                return

            installer_name = chosen_installer.get("name")
            installer_url = chosen_installer.get("browser_download_url")
            installer_id = chosen_installer.get("id")

            # Resolve expected SHA-256 checksum
            expected_sha256 = None
            checksum_url = None
            checksum_id = None

            # Option A: Asset companion file (e.g. DigitalWellbeingSetup-X.Y.Z.exe.sha256, *.sha256)
            for a in assets:
                a_name = a.get("name", "")
                if a_name.endswith(".sha256") or a_name in ("SHA256SUMS", "checksums.txt"):
                    if installer_name and installer_name in a_name:
                        checksum_url = a.get("browser_download_url")
                        checksum_id = a.get("id")
                        break
                    elif not checksum_url:
                        checksum_url = a.get("browser_download_url")
                        checksum_id = a.get("id")

            # Option B: Modern GitHub API asset 'digest' field (e.g. "sha256:123456...")
            digest_field = chosen_installer.get("digest")
            if digest_field and isinstance(digest_field, str) and digest_field.startswith("sha256:"):
                expected_sha256 = digest_field.split(":", 1)[1].strip().lower()

            # Option C: Check release body text for a 64-character SHA256 hex string
            body = best_release.get("body", "") or ""
            if not expected_sha256:
                # Match 64-hex string following sha256 or hash
                m = re.search(r"(?:sha-?256|hash)[:\s=]+([a-fA-F0-9]{64})", body, re.IGNORECASE)
                if m:
                    expected_sha256 = m.group(1).lower()

            payload = {
                "version": best_version,
                "clean_version": best_version.lstrip("vV"),
                "notes": body,
                "asset_name": installer_name,
                "asset_url": installer_url,
                "asset_id": installer_id,
                "checksum_url": checksum_url,
                "checksum_id": checksum_id,
                "expected_sha256": expected_sha256,
                "release_url": best_release.get("html_url", ""),
            }

            logger.info("Updater: update available! Version: %s, Asset: %s, URL: %s", payload["version"], installer_name, installer_url)
            self.update_available.emit(payload)

        except (HTTPError, URLError, TimeoutError, OSError) as e:
            logger.warning("Updater: network error while checking updates: %s", e)
            self.error.emit("Couldn't check for updates right now.")
        except Exception as e:
            logger.exception("Updater: unexpected error while checking updates: %s", e)
            self.error.emit("Couldn't check for updates right now.")
        finally:
            self._checking.clear()

    def download_installer(
        self,
        asset_url: str,
        asset_name: str,
        asset_id: Optional[int] = None,
        checksum_url: Optional[str] = None,
        checksum_id: Optional[int] = None,
        expected_sha256: Optional[str] = None,
        version: Optional[str] = None,
    ) -> None:
        """Download installer with duplicate prevention and SHA-256 checksum verification."""
        with self._download_lock:
            if self._is_downloading:
                logger.info("Updater: download already in progress; ignoring duplicate request.")
                return
            self._is_downloading = True

        self._download_thread = threading.Thread(
            target=self._download_thread_fn,
            args=(asset_url, asset_name, asset_id, checksum_url, checksum_id, expected_sha256, version),
            name="DW-Updater-Download",
            daemon=True,
        )
        self._download_thread.start()

    def _get_update_dir(self) -> Path:
        update_dir = Path(tempfile.gettempdir()) / "DigitalWellbeing_Updates"
        update_dir.mkdir(parents=True, exist_ok=True)
        return update_dir

    def _compute_file_sha256(self, file_path: Path) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest().lower()

    def _download_thread_fn(
        self,
        asset_url: str,
        asset_name: str,
        asset_id: Optional[int],
        checksum_url: Optional[str],
        checksum_id: Optional[int],
        expected_sha256: Optional[str],
        version: Optional[str],
    ) -> None:
        tmp_dir = self._get_update_dir()
        out_path = tmp_dir / asset_name

        try:
            logger.info("Updater: starting download for %s from %s", asset_name, asset_url)
            headers = {"User-Agent": f"{APP_NAME}-Updater/{self._current_version}"}

            # 1. Fetch expected checksum if provided via companion URL
            if not expected_sha256 and checksum_url:
                try:
                    logger.info("Updater: fetching checksum file from %s", checksum_url)
                    chk_req_url = checksum_url
                    chk_headers = dict(headers)
                    if self._token and checksum_id:
                        chk_req_url = f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{checksum_id}"
                        chk_headers["Accept"] = "application/octet-stream"
                        chk_headers["Authorization"] = f"token {self._token}"

                    req = Request(chk_req_url, headers=chk_headers)
                    with urlopen(req, timeout=15) as resp:
                        chk_content = resp.read().decode("utf-8", errors="replace").strip()
                        # Extract first 64-hex sequence found
                        m = re.search(r"([a-fA-F0-9]{64})", chk_content)
                        if m:
                            expected_sha256 = m.group(1).lower()
                            logger.info("Updater: resolved expected SHA-256: %s", expected_sha256)
                except Exception as exc:
                    logger.warning("Updater: could not fetch checksum file: %s", exc)

            # Check if file was already fully downloaded and matches checksum
            if out_path.exists() and expected_sha256:
                existing_hash = self._compute_file_sha256(out_path)
                if existing_hash == expected_sha256:
                    logger.info("Updater: verified installer already exists in cache: %s", out_path)
                    self.download_progress.emit(100)
                    self.download_complete.emit(str(out_path))
                    return
                else:
                    out_path.unlink(missing_ok=True)

            # Prepare download request
            req_url = asset_url
            if self._token and asset_id:
                req_url = f"{self._api_base}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/assets/{asset_id}"
                headers["Accept"] = "application/octet-stream"
                headers["Authorization"] = f"token {self._token}"

            req = Request(req_url, headers=headers)
            temp_download_file = out_path.with_suffix(".download")
            temp_download_file.unlink(missing_ok=True)

            sha256_hasher = hashlib.sha256()
            with urlopen(req, timeout=60) as resp:
                content_length = resp.getheader("Content-Length")
                total_bytes = int(content_length) if content_length and content_length.isdigit() else None
                written = 0
                chunk_size = 64 * 1024

                with open(temp_download_file, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha256_hasher.update(chunk)
                        written += len(chunk)
                        if total_bytes and total_bytes > 0:
                            percent = min(100, int((written * 100) / total_bytes))
                            self.download_progress.emit(percent)

                if total_bytes and written != total_bytes:
                    temp_download_file.unlink(missing_ok=True)
                    raise IOError(f"Incomplete download: received {written} of {total_bytes} bytes")

            actual_hash = sha256_hasher.hexdigest().lower()
            logger.info("Updater: download completed (%d bytes). Computed SHA-256: %s", written, actual_hash)

            # Security: Verify SHA-256 checksum
            if expected_sha256:
                if actual_hash != expected_sha256.lower():
                    temp_download_file.unlink(missing_ok=True)
                    logger.error("Updater: SHA-256 checksum mismatch! Expected: %s, Actual: %s", expected_sha256, actual_hash)
                    self.error.emit(f"Checksum verification failed. Expected: {expected_sha256[:12]}..., Got: {actual_hash[:12]}...")
                    return
                logger.info("Updater: SHA-256 checksum verification succeeded.")
            else:
                # Security rule: Do not execute an unverified installer.
                temp_download_file.unlink(missing_ok=True)
                logger.error("Updater: security abort — no SHA-256 checksum available to verify installer authenticity.")
                self.error.emit("Installer verification failed: no expected SHA-256 checksum available.")
                return

            # Replace target file with verified download
            if out_path.exists():
                out_path.unlink(missing_ok=True)
            temp_download_file.replace(out_path)

            self.download_progress.emit(100)
            self.download_complete.emit(str(out_path))

        except Exception as e:
            logger.exception("Updater: download or verification failed: %s", e)
            if out_path.exists():
                out_path.unlink(missing_ok=True)
            self.error.emit(f"Download failed: {e}")
        finally:
            with self._download_lock:
                self._is_downloading = False

    def launch_installer_and_exit(self, installer_path: str) -> None:
        """Launch Inno Setup installer via a detached PowerShell script that waits for
        the current app process to fully exit, executes the upgrade, cleans up
        temporary artifacts, and relaunches the app.
        """
        try:
            p = Path(installer_path)
            if not p.exists():
                raise FileNotFoundError(f"Installer not found at {installer_path}")

            if not p.suffix.lower() == ".exe":
                raise ValueError(f"Invalid installer executable: {installer_path}")

            # Determine path to relaunch the app
            import sys

            if getattr(sys, "frozen", False):
                app_exec = sys.executable
            else:
                # Look for installed app location first
                local_app = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "DigitalWellbeing" / "DigitalWellbeing.exe"
                prog_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "DigitalWellbeing" / "DigitalWellbeing.exe"
                if local_app.exists():
                    app_exec = str(local_app)
                elif prog_files.exists():
                    app_exec = str(prog_files)
                else:
                    app_exec = sys.executable

            tmp_dir = self._get_update_dir()
            ps1_path = tmp_dir / "run_dw_update.ps1"
            current_pid = os.getpid()

            # PowerShell wrapper script:
            # 1. Wait up to 7 seconds for the current app process to exit and release file locks
            # 2. Run Inno Setup installer with /SILENT /SUPPRESSMSGBOXES /NORESTART
            # 3. Wait for installer process to finish
            # 4. Remove temporary installer file and this script
            # 5. Relaunch the app executable
            ps_script = f"""# Digital Wellbeing In-App Update Wrapper
$ErrorActionPreference = 'Continue'
$dwPid = {current_pid}
$installerPath = '{str(p).replace("'", "''")}'
$appPath = '{str(app_exec).replace("'", "''")}'

# 1. Wait for the current app process to cleanly terminate
try {{
    $proc = Get-Process -Id $dwPid -ErrorAction SilentlyContinue
    if ($proc) {{
        $proc.WaitForExit(7000)
    }}
}} catch {{}}

# 2. Launch Inno Setup installer
$exitCode = 1
try {{
    $installProc = Start-Process -FilePath $installerPath -ArgumentList '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART' -Wait -PassThru
    $exitCode = $installProc.ExitCode
}} catch {{
    $exitCode = -1
}}

Start-Sleep -Seconds 1

# 3. Relaunch the app
if (Test-Path -LiteralPath $appPath) {{
    Start-Process -FilePath $appPath
}}

Start-Sleep -Seconds 1

# 4. Cleanup installer and script
try {{
    Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
}} catch {{}}

try {{
    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
}} catch {{}}
"""
            with open(ps1_path, "w", encoding="utf-8") as f:
                f.write(ps_script)

            logger.info("Updater: spawning detached update launcher (%s) for installer: %s", ps1_path, p)
            CREATE_NO_WINDOW = 0x08000000
            flags = CREATE_NO_WINDOW

            subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_path)],
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        except Exception as e:
            logger.exception("Updater: failed to launch installer: %s", e)
            self.error.emit(f"Failed to launch installer: {e}")
