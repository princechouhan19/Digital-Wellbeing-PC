from __future__ import annotations

from pathlib import Path

from core.constants import AppCategory
from tracker.categorizer import (
    _categorize_with_reason_python,
    categorize_with_reason,
)


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
    / "categorizer_cases.tsv"
)


def _cases():
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        assert len(fields) == 5, f"malformed categorizer fixture row: {line!r}"
        reason_value = "" if fields[4] == "-" else fields[4]
        yield fields[0], fields[1], fields[2], fields[3], reason_value


def _reason_descriptor(game_reason: str, launcher_reason: str) -> tuple[str, str]:
    if game_reason.startswith("Path match: "):
        return "path", game_reason[len("Path match: ") :]
    if launcher_reason.startswith("Launcher regex match (") and launcher_reason.endswith(")"):
        return "launcher", launcher_reason[len("Launcher regex match (") : -1]
    if game_reason.startswith("Game regex match ("):
        return "game", ""
    return "none", ""


def test_python_reference_matches_shared_categorizer_corpus():
    for process_name, exe_path, expected_category, expected_kind, expected_value in _cases():
        category, game_reason, launcher_reason = _categorize_with_reason_python(
            process_name, exe_path
        )
        assert category.value == expected_category, process_name
        assert _reason_descriptor(game_reason, launcher_reason) == (
            expected_kind,
            expected_value,
        ), process_name


def test_selected_categorizer_matches_python_reference():
    # In native CI this compares Rust against the Python behavior; locally, if
    # the cdylib is absent, the public API safely falls back to that reference.
    for process_name, exe_path, *_expected in _cases():
        assert categorize_with_reason(process_name, exe_path) == (
            _categorize_with_reason_python(process_name, exe_path)
        )


def test_native_reason_descriptors_decode_to_python_format(monkeypatch):
    import tracker.categorizer as categorizer_module

    cases = (
        ("steam.exe", "", (3, 2, "steam")),
        ("unknown.exe", r"C:\Games\Indie\unknown.exe", (3, 1, "games")),
        ("eldenring.exe", "", (3, 3, "")),
        ("chrome.exe", "", (1, 0, "")),
    )
    try:
        for process_name, exe_path, native_result in cases:
            monkeypatch.setattr(
                categorizer_module,
                "_rust_categorize_process",
                lambda _name, _path, result=native_result: result,
            )
            categorizer_module.categorize_with_reason.cache_clear()
            assert categorizer_module.categorize_with_reason(process_name, exe_path) == (
                _categorize_with_reason_python(process_name, exe_path)
            )
    finally:
        categorizer_module.categorize_with_reason.cache_clear()


def test_every_category_fixture_uses_an_app_category():
    valid = {category.value for category in AppCategory}
    assert all(expected in valid for _, _, expected, _, _ in _cases())
