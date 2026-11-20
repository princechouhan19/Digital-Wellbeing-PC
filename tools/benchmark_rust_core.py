"""Compare Python domain/categorizer/tracking/URL policies with the optional Rust C ABI.

Run after building the Rust library, for example on Windows:
    cargo build --manifest-path rust-core/Cargo.toml --release
    $env:DW_USE_RUST_CORE = "1"
    $env:DW_RUST_CORE_LIBRARY = (Resolve-Path rust-core/target/release/digital_wellbeing_core.dll)
    python tools/benchmark_rust_core.py

The Rust measurement includes ctypes/FFI overhead. This is a microbenchmark,
not a claim about full-app startup, idle CPU, or memory. Keep Python enabled if
native code does not improve the actual workload.
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

# The bridge reads the opt-in setting when a call is made. Set it before the
# imports below so this tool can explicitly compare both implementations.
os.environ["DW_USE_RUST_CORE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.name != "nt":
    # The Python reference modules import Win32 APIs at module load time. Reuse
    # the repository's no-op cross-platform test stubs for fallback benchmarks.
    import tests.conftest  # noqa: F401

from core.rust_bridge import categorize_process as rust_categorize_process
from core.rust_bridge import decide_tracking_transition as rust_transition
from core.rust_bridge import extract_domain_from_title as rust_extract_domain
from core.rust_bridge import rust_core_available
from core.rust_bridge import normalize_domain as rust_normalize_domain
from core.rust_bridge import select_url_rule as rust_select_url_rule
from protection import url_rules as url_rules_module
from protection.url_rules import UrlRule, UrlRuleEngine
from protection.website_limits import WebsiteLimitManager, _normalize_domain_python
from tracker import browser_domain, categorizer as categorizer_module
from tracker.browser_domain import _extract_domain_python
from tracker.categorizer import _categorize_with_reason_python
from tracker.transitions import _select_transition_python

FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "rust-core"
    / "tests"
    / "fixtures"
)
DOMAIN_FIXTURE = FIXTURE_ROOT / "domain_title_cases.tsv"
DOMAIN_NORMALIZATION_FIXTURE = FIXTURE_ROOT / "domain_normalization_cases.tsv"
CATEGORIZER_FIXTURE = FIXTURE_ROOT / "categorizer_cases.tsv"
TRACKING_FIXTURE = FIXTURE_ROOT / "tracking_transition_cases.tsv"
URL_RULE_FIXTURE = FIXTURE_ROOT / "url_rule_cases.tsv"


def _cases() -> list[tuple[str, str]]:
    cases = []
    for line in DOMAIN_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        title, expected = line.split("\t", 1)
        cases.append((title, "" if expected == "-" else expected))
    return cases


def _normalization_cases() -> list[tuple[str, str]]:
    cases = []
    for line in DOMAIN_NORMALIZATION_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        raw, expected = line.split("\t", 1)
        cases.append(("" if raw == "-" else raw, "" if expected == "-" else expected))
    return cases


def _categorizer_cases() -> list[tuple[str, str, str, str, str]]:
    cases = []
    for line in CATEGORIZER_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 5:
            raise ValueError(f"Malformed categorizer fixture row: {line!r}")
        reason_value = "" if fields[4] == "-" else fields[4]
        cases.append((fields[0], fields[1], fields[2], fields[3], reason_value))
    return cases


def _reason_descriptor(result) -> tuple[str, str]:
    _category, game_reason, launcher_reason = result
    if game_reason.startswith("Path match: "):
        return "path", game_reason[len("Path match: ") :]
    if launcher_reason.startswith("Launcher regex match (") and launcher_reason.endswith(")"):
        return "launcher", launcher_reason[len("Launcher regex match (") : -1]
    if game_reason.startswith("Game regex match ("):
        return "game", ""
    return "none", ""


def _tracking_cases() -> list[tuple[tuple[bool, ...], int, int]]:
    cases = []
    for line in TRACKING_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            raise ValueError(f"Malformed tracking fixture row: {line!r}")
        flags = tuple(field == "1" for field in fields[:5])
        cases.append((flags, int(fields[5]), int(fields[6])))
    return cases


def _url_rule_cases():
    cases = []
    for line in URL_RULE_FIXTURE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 6:
            raise ValueError(f"Malformed URL-rule fixture row: {line!r}")
        rules = []
        native_rules = []
        if fields[3] != "-":
            for serialized in fields[3].split(";"):
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
        cases.append(
            (
                fields[0],
                fields[1],
                fields[2],
                rules,
                native_rules,
                fields[4],
                int(fields[5]),
            )
        )
    return cases


def _url_decision_matches(case, decision) -> bool:
    _host, _path, _default, rules, _native_rules, action, index = case
    expected_rule = rules[index].pattern if index >= 0 else None
    return decision.action == action and decision.matched_rule == expected_rule


def _run_url_rule_case(case):
    host, path, default_action, rules, *_expected = case
    return UrlRuleEngine.decide(f"https://{host}{path}", default_action, rules)


def _percentile(sorted_values: list[int], percentile: int) -> int:
    index = min(len(sorted_values) - 1, ((len(sorted_values) - 1) * percentile) // 100)
    return sorted_values[index]


def _measure_transitions(
    label: str,
    function: Callable[[tuple[bool, ...], int], object],
    cases: list[tuple[tuple[bool, ...], int, int]],
    iterations_per_case: int = 5000,
) -> None:
    for flags, duration_ms, _expected in cases:
        function(flags, duration_ms)

    samples: list[int] = []
    for index in range(iterations_per_case * len(cases)):
        flags, duration_ms, _expected = cases[index % len(cases)]
        started = time.perf_counter_ns()
        function(flags, duration_ms)
        samples.append(time.perf_counter_ns() - started)

    samples.sort()
    print(
        f"{label:24s} p50={_percentile(samples, 50):7d} ns  "
        f"p95={_percentile(samples, 95):7d} ns  "
        f"p99={_percentile(samples, 99):7d} ns  "
        f"mean={statistics.fmean(samples):7.0f} ns"
    )


def _measure_url_rules(
    label: str,
    function: Callable[[tuple], object],
    cases: list[tuple],
    iterations_per_case: int = 5000,
) -> None:
    for case in cases:
        function(case)

    samples: list[int] = []
    for index in range(iterations_per_case * len(cases)):
        case = cases[index % len(cases)]
        started = time.perf_counter_ns()
        function(case)
        samples.append(time.perf_counter_ns() - started)

    samples.sort()
    print(
        f"{label:24s} p50={_percentile(samples, 50):7d} ns  "
        f"p95={_percentile(samples, 95):7d} ns  "
        f"p99={_percentile(samples, 99):7d} ns  "
        f"mean={statistics.fmean(samples):7.0f} ns"
    )


def _measure_categorizer(
    label: str,
    function: Callable[[str, str], object],
    cases: list[tuple[str, str, str, str, str]],
    iterations_per_case: int = 5000,
) -> None:
    for process_name, exe_path, _category, _kind, _value in cases:
        function(process_name, exe_path)

    samples: list[int] = []
    for index in range(iterations_per_case * len(cases)):
        process_name, exe_path, _category, _kind, _value = cases[index % len(cases)]
        started = time.perf_counter_ns()
        function(process_name, exe_path)
        samples.append(time.perf_counter_ns() - started)

    samples.sort()
    print(
        f"{label:24s} p50={_percentile(samples, 50):7d} ns  "
        f"p95={_percentile(samples, 95):7d} ns  "
        f"p99={_percentile(samples, 99):7d} ns  "
        f"mean={statistics.fmean(samples):7.0f} ns"
    )


def _measure(
    label: str,
    function: Callable[[str], object],
    cases: list[tuple[str, str]],
    iterations_per_case: int = 5000,
) -> None:
    for index in range(100):
        function(cases[index % len(cases)][0])

    samples: list[int] = []
    for index in range(iterations_per_case * len(cases)):
        title = cases[index % len(cases)][0]
        started = time.perf_counter_ns()
        function(title)
        samples.append(time.perf_counter_ns() - started)

    samples.sort()
    print(
        f"{label:24s} p50={_percentile(samples, 50):7d} ns  "
        f"p95={_percentile(samples, 95):7d} ns  "
        f"p99={_percentile(samples, 99):7d} ns  "
        f"mean={statistics.fmean(samples):7.0f} ns"
    )


def main() -> int:
    cases = _cases()
    for title, expected in cases:
        actual = _extract_domain_python(title)
        if actual != expected:
            print(
                f"Python baseline mismatch: {title!r}: "
                f"Python={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1

    print(
        f"Validated {len(cases)} shared domain cases against the Python fallback; "
        f"{len(cases) * 5000:,} timed calls per path."
    )
    _measure("Python uncached", _extract_domain_python, cases)

    # Measure the app's real memoized dispatcher while forcing its Python
    # fallback, so this remains a Python baseline even when the Rust library
    # is installed and enabled for the direct native measurement below.
    native_parser = browser_domain._rust_extract_domain_from_title
    try:
        browser_domain._rust_extract_domain_from_title = lambda _title: None
        browser_domain._extract_domain_cached.cache_clear()
        _measure("Python cached fallback", browser_domain.extract_domain_from_title, cases)
    finally:
        browser_domain._rust_extract_domain_from_title = native_parser
        browser_domain._extract_domain_cached.cache_clear()

    normalization_cases = _normalization_cases()
    for raw, expected in normalization_cases:
        actual = _normalize_domain_python(raw)
        if actual != expected:
            print(
                f"Python domain-normalization mismatch: {raw!r}: "
                f"Python={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1
    print(
        f"Validated {len(normalization_cases)} shared domain-normalization cases "
        f"against Python; {len(normalization_cases) * 5000:,} timed calls per path."
    )
    _measure("Python domain normalize", _normalize_domain_python, normalization_cases)

    categorizer_cases = _categorizer_cases()
    python_uncached_categorizer = _categorize_with_reason_python
    for process_name, exe_path, expected_category, expected_kind, expected_value in categorizer_cases:
        actual = python_uncached_categorizer(process_name, exe_path)
        descriptor = _reason_descriptor(actual)
        if actual[0].value != expected_category or descriptor != (expected_kind, expected_value):
            print(
                f"Python categorizer baseline mismatch: {process_name!r}, {exe_path!r}: "
                f"Python={actual!r}, expected={(expected_category, expected_kind, expected_value)!r}",
                file=sys.stderr,
            )
            return 1
    print(
        f"Validated {len(categorizer_cases)} categorizer cases against Python; "
        f"{len(categorizer_cases) * 5000:,} timed calls per path."
    )
    _measure_categorizer(
        "Python uncached category",
        python_uncached_categorizer,
        categorizer_cases,
    )

    native_categorizer = categorizer_module._rust_categorize_process
    try:
        categorizer_module._rust_categorize_process = lambda _name, _path="": None
        categorizer_module.categorize_with_reason.cache_clear()
        _measure_categorizer(
            "Python cached category",
            categorizer_module.categorize_with_reason,
            categorizer_cases,
        )
    finally:
        categorizer_module._rust_categorize_process = native_categorizer
        categorizer_module.categorize_with_reason.cache_clear()

    tracking_cases = _tracking_cases()
    for flags, duration_ms, expected in tracking_cases:
        actual = int(
            _select_transition_python(
                *flags,
                session_duration_s=duration_ms / 1000.0,
            )
        )
        if actual != expected:
            print(
                f"Python transition baseline mismatch: ({flags!r}, {duration_ms}): "
                f"Python={actual}, expected={expected}",
                file=sys.stderr,
            )
            return 1
    print(
        f"Validated {len(tracking_cases)} tracking transition cases against the "
        f"Python fallback; {len(tracking_cases) * 5000:,} timed calls per path."
    )
    _measure_transitions(
        "Python transition policy",
        lambda flags, duration_ms: _select_transition_python(
            *flags,
            session_duration_s=duration_ms / 1000.0,
        ),
        tracking_cases,
    )

    url_rule_cases = _url_rule_cases()
    python_url_selector = url_rules_module._rust_select_url_rule
    try:
        url_rules_module._rust_select_url_rule = lambda *_args: None
        for case in url_rule_cases:
            decision = _run_url_rule_case(case)
            if not _url_decision_matches(case, decision):
                print(
                    f"Python URL-rule baseline mismatch: {case!r}: {decision!r}",
                    file=sys.stderr,
                )
                return 1
        print(
            f"Validated {len(url_rule_cases)} URL-rule cases against Python; "
            f"{len(url_rule_cases) * 5000:,} timed calls per path."
        )
        _measure_url_rules("Python URL-rule policy", _run_url_rule_case, url_rule_cases)
    finally:
        url_rules_module._rust_select_url_rule = python_url_selector

    if not rust_core_available():
        print(
            "Rust core not found; native parser/normalizer/categorizer/transition/URL-rule "
            "parity and timing were skipped. Build it with cargo and set "
            "DW_RUST_CORE_LIBRARY to compare against these Python baselines "
            "(see docs/RUST_CORE.md).",
            file=sys.stderr,
        )
        return 0

    for title, expected in cases:
        actual = rust_extract_domain(title)
        if actual != expected:
            print(
                f"Rust parity failure: {title!r}: Rust={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1

    _measure("Rust C ABI / ctypes", rust_extract_domain, cases)

    for raw, expected in normalization_cases:
        actual = rust_normalize_domain(raw)
        if actual != expected:
            print(
                f"Rust domain-normalization parity failure: {raw!r}: "
                f"Rust={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1
    _measure("Rust normalize C ABI", rust_normalize_domain, normalization_cases)
    _measure("Rust normalize app path", WebsiteLimitManager.normalize_domain, normalization_cases)

    category_codes = {
        "Other": 0,
        "Browser": 1,
        "Programming": 2,
        "Gaming": 3,
        "Communication": 4,
        "Productivity": 5,
        "Entertainment": 6,
        "System": 7,
        "Utilities": 8,
        "Education": 9,
        "Social": 10,
    }
    reason_codes = {"none": 0, "path": 1, "launcher": 2, "game": 3}
    for process_name, exe_path, expected_category, expected_kind, expected_value in categorizer_cases:
        actual = rust_categorize_process(process_name, exe_path)
        expected = (
            category_codes[expected_category],
            reason_codes[expected_kind],
            expected_value,
        )
        if actual != expected:
            print(
                f"Rust categorizer parity failure: {process_name!r}, {exe_path!r}: "
                f"Rust={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1
    _measure_categorizer(
        "Rust categorizer C ABI",
        rust_categorize_process,
        categorizer_cases,
    )

    for flags, duration_ms, expected in tracking_cases:
        actual = rust_transition(*flags, session_duration_ms=duration_ms)
        if actual != expected:
            print(
                f"Rust transition parity failure: ({flags!r}, {duration_ms}): "
                f"Rust={actual!r}, expected={expected}",
                file=sys.stderr,
            )
            return 1

    _measure_transitions(
        "Rust transition C ABI",
        lambda flags, duration_ms: rust_transition(
            *flags,
            session_duration_ms=duration_ms,
        ),
        tracking_cases,
    )

    for case in url_rule_cases:
        host, path, default_action, _rules, native_rules, expected_action, expected_index = case
        actual = rust_select_url_rule(host, path, default_action, native_rules)
        expected = (expected_action, expected_index if expected_index >= 0 else None)
        if actual != expected:
            print(
                f"Rust URL-rule parity failure: {host!r}{path!r}: "
                f"Rust={actual!r}, expected={expected!r}",
                file=sys.stderr,
            )
            return 1
    _measure_url_rules("Rust URL-rule C ABI", _run_url_rule_case, url_rule_cases)
    print("Run the full app benchmark separately before making the Rust path the default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
