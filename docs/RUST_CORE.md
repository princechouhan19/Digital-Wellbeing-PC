# Experimental Rust core

`rust-core/` is a gradual, optional migration of deterministic logic—not a full Rust rewrite of Digital Wellbeing. The desktop UI, PySide6 runtime, Win32/WinRT and UI Automation access, SQLite persistence, URL parsing, rule storage, timestamps, and operating-system side effects remain in Python. Python remains the reference implementation and the default; native calls require explicit opt-in and fall back safely when the library is absent or incompatible. This build does not claim a performance improvement.

The Rust library currently covers browser-title/domain recognition, domain normalization for website limits, process categorization, tracking-session transition selection, and the final normalized host/path URL-rule selector. The URL-rule selector only chooses a rule: Python still parses/normalizes URLs, owns rule persistence and creates user-facing decision descriptions.

## Build and test

Install a stable Rust toolchain, then run from the repository root:

```bash
cargo test --manifest-path rust-core/Cargo.toml
cargo build --manifest-path rust-core/Cargo.toml --release
```

The crate has no third-party dependencies. Python and Rust share conformance fixtures for title parsing (`domain_title_cases.tsv`), domain normalization (`domain_normalization_cases.tsv`), categorization (`categorizer_cases.tsv`), tracking transitions (`tracking_transition_cases.tsv`), and URL-rule selection (`url_rule_cases.tsv`). The fixtures check precedence and boundary behavior, not just happy paths.

On Windows, test the real ctypes bridge and compare the measured call paths:

```powershell
$env:DW_USE_RUST_CORE = "1"
$env:DW_RUST_CORE_LIBRARY = (Resolve-Path rust-core/target/release/digital_wellbeing_core.dll)
python -m pytest -q tests/test_rust_core.py tests/test_categorizer_rust.py tests/test_tracking_transitions.py tests/test_url_rules_rust.py tests/test_website_limits_rust.py
python tools/benchmark_rust_core.py
```

`DW_USE_RUST_CORE=1` opts into native domain parsing/normalization, process categorization, tracking transition selection, and URL-rule selection. `DW_USE_RUST_CORE=0` forces the Python reference/fallback. `DW_RUST_CORE_LIBRARY` may point to a non-default library location. When the library is missing, fails to load, or has the wrong ABI, Python remains in control.

The benchmark verifies all shared corpora, reports Python baselines even without a native library, and includes ctypes overhead when timing native paths. Results from this sandbox or a microbenchmark do not establish a product-wide speedup. Compare full-app startup, RSS, idle CPU, tracking behavior, and crash rates on the same Windows workload before considering any default change.

## C ABI

The Python loader requires ABI **v4** exactly. This ABI adds URL-rule selection; v1–v3 libraries are rejected safely. Exports in `rust-core/src/lib.rs`:

- `dw_core_abi_version` — ABI handshake.
- `dw_extract_domain_from_title` — browser-title to domain parsing.
- `dw_normalize_domain` — domain input normalization.
- `dw_domain_matches` — exact host or subdomain match.
- `dw_categorize_process` — process/path categorization with compact reason descriptors. Category codes: `0` Other, `1` Browser, `2` Programming, `3` Gaming, `4` Communication, `5` Productivity, `6` Entertainment, `7` System, `8` Utilities, `9` Education, `10` Social. Reason kinds: `0` none, `1` path, `2` launcher, `3` game-rule match.
- `dw_capped_elapsed_ms` — saturating, bounded elapsed-time arithmetic helper.
- `dw_decide_tracking_transition` — deterministic session transition selection. Codes: `0` keep, `1` start, `2` app switch, `3` idle switch, `4` fullscreen-game title update, `5` title split, `6` in-place title update.
- `dw_select_url_rule` — choose the enabled matching URL rule by longest path, then longest host, then block-on-tie. It returns the action and writes the selected input index, or `-1` when the default action applies. Python owns URL parsing and normalization.

FFI functions validate inputs and catch Rust panics so they do not unwind across the C boundary. Keep signatures narrow and retain Python fallbacks for every native selector.

## Experimental download

The `Rust Experimental Build` GitHub workflow produces a Windows x64 portable ZIP and a self-contained setup `.exe`, each containing the existing Python/PySide6 app plus the optional Rust DLL. It is a prerelease for testing, not a replacement for the regular release. The setup adds a **Digital Wellbeing (Rust Experimental)** shortcut that sets `DW_USE_RUST_CORE=1`; the regular shortcut keeps the Python fallback. The ZIP can be extracted and launched with **`Run Digital Wellbeing (Rust Experimental).bat`**, while launching `DigitalWellbeing.exe` directly keeps the Python fallback. The package includes a test note, SHA-256 checksums, and a helper microbenchmark report from the GitHub-hosted Windows runner; those microbenchmark timings are not a full-app performance claim. The native library does not alter the database schema or migrate user data.

For a local build through `build.py`, set `DW_BUILD_RUST_CORE=1`; the script compiles the DLL and the spec bundles it. If invoking `installer/build_installer.ps1` directly, run the Cargo build first because that script only packages existing outputs. Bundling a DLL does not opt the regular app into Rust; the runtime opt-in remains separate.

See [Rust migration research and plan](RUST_MIGRATION_RESEARCH.md) for the scope and staged decisions. The Rust UI/runtime and database/protection side effects have not been migrated.
