# Rust migration research for Digital Wellbeing

**Research cut-off:** 20 November 2026
**Scope:** Discord engineering material and its current client rewrite; relevant community discussion and research on Rust performance. This is an engineering synthesis, not a claim that Discord's measurements transfer to this application.

## Executive summary

Discord's engineering posts support **targeted, measured migrations**, not “rewrite it in Rust and it will be faster.” Discord first chose small or clearly bounded hot paths, profiled the bottleneck, benchmarked realistic workloads, rolled changes out carefully, and retained higher-level systems where they were already a good fit. The 2026 client announcement is a larger, still-in-development product rewrite; the early memory/startup figures are not an independently reproduced benchmark for this project.

For Digital Wellbeing, replacing only a few string helpers with Rust cannot materially reduce the current GUI's baseline memory: the application is Python + PySide6, and its own performance report attributes tens of megabytes to the Qt runtime. The meaningful lightweight-client gain would require migrating the UI/runtime as well as core logic. That is a staged product rewrite, not a safe one-commit language swap. Existing Windows integrations (UI Automation/COM, Win32 hooks, Windows Hello, UAC/hosts-file protection) and the on-disk SQLite schema must remain compatible throughout.

## Discord engineering posts and primary statements

### 1. Rust for a measured hot path — Read States (4 February 2020)

[Why Discord is switching from Go to Rust](https://discord.com/blog/why-discord-is-switching-from-go-to-rust) describes a Read States service in a latency-sensitive path. Discord traced periodic latency/CPU spikes to garbage-collector scanning over a very large LRU cache; it did not start with a blanket rewrite. The service was relatively self-contained, so they ported it, load-tested it, canaried one node, and then rolled it out. Profiling then informed concrete changes: a `BTreeMap` for the cache, a more suitable metrics library, and fewer memory copies. The post explicitly cautions against rewriting everything in Rust just because.

**Application here:** retain the existing Python/Qt app as the compatibility baseline; choose a Rust seam only when a reproducible profile says the seam is worth crossing. Include the interop cost in the benchmark, not just a native microbenchmark.

### 2. Rust beside a higher-level runtime — SortedSet (17 May 2019)

[Using Rust to Scale Elixir for 11 Million Concurrent Users](https://discord.com/blog/using-rust-to-scale-elixir-for-11-million-concurrent-users) keeps Discord's core real-time logic in Elixir and moves a mutation-heavy ordered-set data structure into a Rust NIF. The post reports benchmarking several data structures and set sizes up to one million entries before shipping. This is a concrete example of preserving a productive host architecture while using Rust at a narrow CPU/data-structure boundary.

**Application here:** first move deterministic, platform-independent logic; leave Windows/Qt/SQLite boundaries behind adapters until behavior is proven equivalent.

### 3. Incremental shared app logic (3 June 2025)

[Discord Patch Notes: June 3, 2025](https://discord.com/blog/discord-patch-notes-june-3-2025) says Discord was migrating some core stores and API interfaces to a shared multi-platform Rust implementation. It reports incremental performance/reliability KPI gains after migrating one store, including memory/CPU and crashes—not an immediate replacement of every app layer.

**Application here:** preserve the current database and settings formats, migrate one subsystem at a time, and track correctness, crashes, CPU, memory and responsiveness at each step.

### 4. Architecture matters beyond language (6 March 2023)

[How Discord Stores Trillions of Messages](https://discord.com/blog/how-discord-stores-trillions-of-messages) discusses Rust data services, but also the database and traffic-shaping architecture around them. It describes intermediary data services reducing traffic spikes against hot partitions. It is backend-scale engineering, not evidence that translating a desktop application line-for-line lowers its memory footprint.

### 5. Discord's 2026 native-client announcement

The primary statement is Discord CTO Stanislav Vishnevskiy's [4 November 2026 X post](https://x.com/svishnevskiy/status/2118081920194203799): Discord plans a Rust client core, GPUI for desktop, and native mobile UI sharing application code with desktop; the post says user testing is forthcoming. His [follow-up about responsiveness and boot time](https://x.com/svishnevskiy/status/2118398632236073156) is a product demonstration, not a published benchmark suite.

[InfoQ's 19 November 2026 report](https://www.infoq.com/news/2026/11/discord-rust-rewrite-gpui-zed/) relays early internal measurements (including an approximately 290 MB desktop snapshot with two accounts and a startup comparison). Treat these as **early reported observations**, not a target or an apples-to-apples result for Digital Wellbeing. InfoQ also calls out costs of replacing browser UI infrastructure: text layout, input-method integration, screen-reader hooks and right-to-left support need deliberate handling.

**Application here:** a native UI/runtime is necessary to change the Qt memory floor, but it comes with accessibility, DPI, text input, tray, and platform-integration work. Evaluate a UI toolkit against those requirements and measured release builds; do not select GPUI solely because Discord did.

## Community discussion (anecdotal, not a benchmark)

- [r/discordapp: “Discord announces a full rust rewrite … using GPUI”](https://www.reddit.com/r/discordapp/comments/1xnzmug/discord_announces_a_full_rust_rewrite_across/) includes questions about GPUI maturity, feature parity, and how much code is actually shared across desktop/mobile.
- [r/rust: “Discord is getting GPUI rewrite”](https://www.reddit.com/r/rust/comments/1xnzn48/discord_is_getting_gpui_rewrite/) includes optimism about the native UI and discussion of accessibility/upstreaming and framework maturity.

These threads are useful as a checklist of migration risks, not evidence of performance. Reddit blocked direct page retrieval in this environment, so this review used the indexed discussion extracts and does not treat vote counts or individual claims as verified facts.

## Research papers

1. Y. Zhang, Y. Zhang, G. Portokalidis and J. Xu, [“Towards Understanding the Runtime Performance of Rust,” ASE 2022](https://doi.org/10.1145/3551349.3559494). The paper compares manually checked Rust/C microbenchmarks with identical functionality/algorithms. Its abstract reports that results varied by workload and attributes observed overhead mainly to runtime checks and language restrictions. This is a reminder that safety and performance need workload-specific measurement; it is not a Rust-versus-Python desktop benchmark.
2. [“Finding Performance Issues in Rust Projects,” ASE 2024](https://doi.org/10.1145/3691620.3695368). The ACM abstract reports an analysis of 100 GitHub projects and 122 performance bugs, including problems related to dynamic checks and memory-management patterns. Rust code can still contain performance bugs; review clones, allocations, checks and data structures rather than assuming the language fixes them.

Only publisher abstracts/metadata were available for these papers during this pass; no paper result is used as a numeric target for this product.

## Project-specific baseline and decision

The repository is a Windows-first Python 3.11+ / PySide6 application, with an event-driven tracker, UI Automation fallback, local SQLite/WAL storage, and native Win32/WinRT features. [`docs/PERFORMANCE.md`](PERFORMANCE.md) records prior measurements: roughly 185 ms for warm `MainWindow` construction, about 74–75 MB RSS at first paint, around 0.08% typical idle tracker CPU, and large wins already delivered by event-driven tracking, caching, indexes and lazy pages. Those are historical measurements from the documented Windows development machine, not measurements from this Linux sandbox.

Therefore the migration starts as a **non-breaking, optional Rust core**, behind a C ABI and Python fallback. The portable-core slices handle browser-title/domain recognition, website-limit domain normalization, process categorization, and selection over Python-normalized URL-rule data. The tracking slice moves only the deterministic foreground-sample-to-session-action decision into Rust; Win32 collection, URL parsing, timestamps, session billing, SQLite, callbacks, rule persistence, and side effects remain Python. All migrated selectors use shared behavior fixtures. Native use remains disabled by default and must pass Windows parity tests and representative end-to-end measurements before release adoption. The work does not replace the GUI, tracker coordinator, database, or broader protection system.

## Staged migration plan

1. **Baseline and safeguards:** preserve current behavior and local data; keep existing Python tests; add shared Rust/Python conformance cases and release-build benchmarks for startup, idle CPU, RSS, tracker tick, database analytics and crashes.
2. **Portable Rust core (started):** add pure Rust domain helpers and process categorization behind a versioned C ABI; keep Python as the default/fallback and make native use explicitly opt-in until measured.
3. **Tracking engine (underway):** the first seam is a pure transition selector with shared cases. Next, port deterministic accounting/state transitions behind the existing Win32/UIA adapters; compare complete emitted sessions and durations against Python on recorded/synthetic event traces before switching. The Python coordinator and its side effects remain in place for now.
4. **Persistence and protection:** a narrow URL-rule selection function now accepts Python-normalized host/path pairs and chooses a rule in Rust; URL parsing, rule storage/import/export, decision descriptions, and focus/protection side effects remain Python. Migrate SQLite access or broader focus/protection behavior only with schema compatibility, import/rollback tests, and a security review. Keep Windows Hello/UAC/hosts-file operations isolated and least-privileged.
5. **Native UI/runtime:** only after core parity, prototype a Rust UI and evaluate memory, startup, accessibility, text input, DPI, tray behavior and Windows integration. Remove Python/PySide6 only when all shipped features and data migrations have parity.

The current work is a narrow step-2 core, the first isolated step-3 transition-policy seam, and a selector-only slice of step 4. It is not a claim that the whole product, tracking coordinator, database, protection layer, or UI has been rewritten. The staged migration boundary keeps Python as the shipped application/runtime and safe fallback; a literal all-files rewrite would require a separate product project with feature, data, accessibility, and platform-parity milestones.