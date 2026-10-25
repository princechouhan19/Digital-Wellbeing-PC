"""
bump_version.py — Update every source version reference in one command.

Usage:
    python tools/bump_version.py --set 4.3.0
    python tools/bump_version.py --check

The release build (installer, app resources, website download route/tests, and
docs) reads from these locations; keeping them in sync by hand caused several
mismatches in the 4.2.0 release.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def current_version() -> str:
    return json.loads((ROOT / "version.json").read_text(encoding="utf-8"))["version"]


def _replace(path: Path, patterns: list[tuple[str, str]]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    updated = text
    for old, new in patterns:
        updated = updated.replace(old, new)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8", newline="")
    return True


def bump(new_version: str) -> list[str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", new_version):
        raise SystemExit("Version must look like MAJOR.MINOR.PATCH")
    old = current_version()
    if old == new_version:
        return []
    old_parts = old.split(".")
    while len(old_parts) < 4:
        old_parts.append("0")
    parts = new_version.split(".")
    while len(parts) < 4:
        parts.append("0")
    changed = []

    def do(rel: str, pairs: list[tuple[str, str]]) -> None:
        if _replace(ROOT / rel, pairs):
            changed.append(rel)

    def do_regex(rel: str, pattern: str, replacement: str) -> None:
        path = ROOT / rel
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        updated = re.sub(pattern, replacement, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8", newline="")
            changed.append(rel)

    do("version.json", [(f'"version": "{old}"', f'"version": "{new_version}"')])
    do(
        "file_version_info.txt",
        [
            ("'FileVersion', '" + old + "'", "'FileVersion', '" + new_version + "'"),
            ("'ProductVersion', '" + old + "'", "'ProductVersion', '" + new_version + "'"),
        ],
    )
    do_regex(
        "file_version_info.txt",
        r"filevers=\([^)]*\)",
        f"filevers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})",
    )
    do_regex(
        "file_version_info.txt",
        r"prodvers=\([^)]*\)",
        f"prodvers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})",
    )
    do_regex(
        "app.manifest",
        r'(assemblyIdentity[^>]+version=")[^"]+(")',
        rf"\g<1>{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}\g<2>",
    )
    do(
        "installer/installer_app.py",
        [
            (f'"Digital Wellbeing", "{old}"', f'"Digital Wellbeing", "{new_version}"'),
            (f"Setup.{old}", f"Setup.{new_version}"),
        ],
    )
    do("installer/uninstaller_app.py", [(f"Uninstaller.{old}", f"Uninstaller.{new_version}")])
    for rel in ("installer/installer_version_info.txt", "installer/uninstaller_version_info.txt"):
        do(
            rel,
            [
                (f"'FileVersion', '{old}'", f"'FileVersion', '{new_version}'"),
                (f"'ProductVersion', '{old}'", f"'ProductVersion', '{new_version}'"),
            ],
        )
        do_regex(rel, r"filevers=\([^)]*\)", f"filevers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})")
        do_regex(rel, r"prodvers=\([^)]*\)", f"prodvers=({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})")
    do(
        "README.md",
        [
            (f"Release-v{old}", f"Release-v{new_version}"),
            (f"Download Installer (v{old})", f"Download Installer (v{new_version})"),
            (f"DigitalWellbeingSetup-{old}.exe", f"DigitalWellbeingSetup-{new_version}.exe"),
        ],
    )
    do("PRIVACY.md", [(f"Digital Wellbeing v{old}", f"Digital Wellbeing v{new_version}")])
    do(
        "docs/USER_GUIDE.md",
        [(f"DigitalWellbeingSetup-{old}.exe", f"DigitalWellbeingSetup-{new_version}.exe")],
    )
    do(
        "docs/QA_APP_LOCKER.md",
        [(f"DigitalWellbeingSetup-{old}.exe", f"DigitalWellbeingSetup-{new_version}.exe")],
    )
    do("website/src/config/site.ts", [(f'version: "{old}"', f'version: "{new_version}"')])
    do(
        "website/src/app/api/download/route.ts",
        [(f"DigitalWellbeingSetup-{old}.exe", f"DigitalWellbeingSetup-{new_version}.exe")],
    )
    do("website/src/app/api/stats/route.ts", [(f"version: '{old}'", f"version: '{new_version}'")])
    do(
        "website/src/components/interactive/software-demo.tsx",
        [(f"Digital Wellbeing v{old}", f"Digital Wellbeing v{new_version}")],
    )
    do(
        "website/src/__tests__/download.test.ts",
        [
            (f"DigitalWellbeingSetup-{old}.exe", f"DigitalWellbeingSetup-{new_version}.exe"),
            (f"data.version, '{old}'", f"data.version, '{new_version}'"),
            (f"siteConfig.version, '{old}'", f"siteConfig.version, '{new_version}'"),
            (f"Public Release v{old}", f"Public Release v{new_version}"),
        ],
    )
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", dest="new_version")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        print(current_version())
        return 0
    if not args.new_version:
        parser.error("--set VERSION or --check is required")
    changed = bump(args.new_version)
    for rel in changed:
        print("updated", rel)
    print(f"Version: {current_version()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
