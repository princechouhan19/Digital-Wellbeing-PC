from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.rust_bridge import normalize_domain as rust_normalize_domain
from core.rust_bridge import rust_core_available
from protection.website_limits import WebsiteLimitManager, _normalize_domain_python


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
    / "domain_normalization_cases.tsv"
)


def _cases():
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        raw, expected = line.split("\t", 1)
        yield "" if raw == "-" else raw, "" if expected == "-" else expected


def test_python_domain_normalizer_matches_shared_corpus():
    for raw, expected in _cases():
        assert _normalize_domain_python(raw) == expected, raw


def test_selected_website_limit_normalizer_matches_shared_corpus():
    for raw, expected in _cases():
        assert WebsiteLimitManager.normalize_domain(raw) == expected, raw


def test_website_limit_normalizer_falls_back_to_python(monkeypatch):
    import protection.website_limits as website_limits_module

    monkeypatch.setattr(website_limits_module, "_rust_normalize_domain", lambda _raw: None)
    for raw, expected in _cases():
        assert WebsiteLimitManager.normalize_domain(raw) == expected, raw


def test_native_domain_normalizer_matches_shared_corpus_when_available():
    require_native = os.environ.get("DW_REQUIRE_RUST_CORE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not rust_core_available():
        if require_native:
            pytest.fail("DW_REQUIRE_RUST_CORE=1 but the Rust library is unavailable")
        pytest.skip("optional Rust library is not built")

    for raw, expected in _cases():
        assert rust_normalize_domain(raw) == expected, raw
