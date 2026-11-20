from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.rust_bridge import rust_core_available, select_url_rule
from protection.url_rules import UrlRule, UrlRuleEngine


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
    / "url_rule_cases.tsv"
)


def _cases():
    for line in FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        assert len(fields) == 6, f"malformed URL-rule fixture row: {line!r}"
        serialized_rules = [] if fields[3] == "-" else fields[3].split(";")
        rules = []
        native_rules = []
        for serialized in serialized_rules:
            action, enabled, host, path = serialized.split(",", 3)
            normalized_path = "" if path == "-" else path
            rules.append(
                UrlRule(
                    pattern=f"{host}{normalized_path}",
                    action=action,
                    enabled=enabled == "1",
                )
            )
            native_rules.append((host, normalized_path, action, enabled == "1"))
        yield (
            fields[0],
            fields[1],
            fields[2],
            rules,
            native_rules,
            fields[4],
            int(fields[5]),
        )


def _assert_engine_decision(host, path, default, rules, expected_action, expected_index):
    url = f"https://{host}{path}"
    decision = UrlRuleEngine.decide(url, default, rules)
    assert decision.action == expected_action, url
    expected_pattern = rules[expected_index].pattern if expected_index >= 0 else None
    assert decision.matched_rule == expected_pattern, url


def test_python_reference_matches_shared_url_rule_corpus(monkeypatch):
    import protection.url_rules as url_rules_module

    monkeypatch.setattr(url_rules_module, "_rust_select_url_rule", lambda *_args: None)
    for host, path, default, rules, _native_rules, expected_action, expected_index in _cases():
        _assert_engine_decision(host, path, default, rules, expected_action, expected_index)


def test_selected_engine_backend_matches_shared_url_rule_corpus():
    for host, path, default, rules, _native_rules, expected_action, expected_index in _cases():
        _assert_engine_decision(host, path, default, rules, expected_action, expected_index)


def test_native_selector_matches_shared_url_rule_corpus_when_available():
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

    for host, path, default, _rules, native_rules, expected_action, expected_index in _cases():
        assert select_url_rule(host, path, default, native_rules) == (
            expected_action,
            expected_index if expected_index >= 0 else None,
        ), (host, path)
