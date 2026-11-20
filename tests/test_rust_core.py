from __future__ import annotations

import os
from pathlib import Path

import pytest

from core import rust_bridge
from tracker.browser_domain import _extract_domain_python, extract_domain_from_title


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
    / "domain_title_cases.tsv"
)


def _domain_cases():
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        title, expected = line.split("\t", 1)
        yield title, "" if expected == "-" else expected


def test_python_reference_matches_shared_rust_conformance_corpus():
    for title, expected in _domain_cases():
        assert _extract_domain_python(title) == expected, title


def test_selected_backend_matches_shared_conformance_corpus():
    # When a native library has been explicitly enabled, this also checks its
    # result against the same expected values; otherwise it exercises fallback.
    for title, expected in _domain_cases():
        assert extract_domain_from_title(title) == expected, title


def test_rust_backend_is_disabled_without_explicit_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DW_USE_RUST_CORE", "0")
    assert rust_bridge.rust_core_available() is False
    assert rust_bridge.extract_domain_from_title("GitHub - Google Chrome") is None


def test_opted_in_ci_loads_native_library():
    if os.environ.get("DW_REQUIRE_RUST_CORE", "").strip().lower() not in {"1", "true", "yes", "on"}:
        pytest.skip("native-load assertion is only required in the native Rust CI job")
    assert rust_bridge.rust_core_available()
