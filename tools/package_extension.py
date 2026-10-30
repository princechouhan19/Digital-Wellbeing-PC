"""
package_extension.py — Validate and package the Digital Wellbeing companion browser extension.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path


def package() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    ext_dir = repo_root / "assets" / "browser_extension"
    dist_dir = repo_root / "dist"
    dist_dir.mkdir(exist_ok=True)

    manifest_path = ext_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.json at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    name = manifest.get("name", "extension")
    version = manifest.get("version", "1.0.0")
    print(f"[EXT] Validating {name} v{version}...")

    # Required files verification
    required_files = [
        "manifest.json",
        "background.js",
        "popup.html",
        "popup.js",
        "popup.css",
        "options.html",
        "options.js",
        "blocked.html",
        "blocked.js",
        "content/feed_shield.js",
    ]
    for rel in required_files:
        p = ext_dir / rel
        if not p.exists():
            raise FileNotFoundError(f"Required file missing from extension: {rel}")

    zip_path = dist_dir / f"digital-wellbeing-companion-v{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in ext_dir.rglob("*"):
            if file.is_file() and not file.name.endswith(".pyc") and not file.name.startswith("."):
                rel_path = file.relative_to(ext_dir)
                zf.write(file, rel_path)

    print(f"[EXT] Successfully packaged {zip_path.name} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


if __name__ == "__main__":
    package()
