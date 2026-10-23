# Performance & Engine Optimization (v4.2)

Digital Wellbeing is designed to run permanently in the background. This
document records what changed in the v4.2 performance pass, how it was
measured, and which roadmap targets were deliberately re-scoped.

All numbers below were captured on the development machine (Windows 11,
Python 3.12, PySide6 6.12) with the project virtualenv. They are medians unless
stated otherwise. Reproduce them with:

```powershell
.\venv\Scripts\python.exe tools\benchmark_performance.py
.\venv\Scripts\python.exe tools\measure_idle_cpu.py --seconds 20
```

---

## 1. Results at a glance

| Metric | Before (v4.1) | After (v4.2) | Change |
|---|---:|---:|---:|
| `MainWindow` construction (cold) | 2522.8 ms | 185.2 ms | **13.6× faster** |
| Qt widgets created at startup | 1766 | 95 | **−95 %** |
| RSS at first paint | — | 74–75 MB | — |
| RSS with all 13 pages loaded | 178 MB (at startup) | 178 MB (after visiting all) | unchanged — pages are lazy |
| Tracker foreground queries | 2 / s | ≤ 0.2 / s | **10× fewer** |
| Tracker loop wakeups | 2 / s | 0.5 / s + events | **4× fewer** |
| Idle tracker CPU (service only) | ~0.2–0.3 % (estimated) | 0.00–0.16 %, typical ≈0.08 % | **≈2–3× lower** |
| `GetLastInputInfo` sample (cached) | 0.42 ms | 0.008 ms | **50× faster** |
| Browser title → domain (cached) | 0.013 ms | 0.0004 ms | **30× faster** |
| Adult-content classify (cached) | 0.34 ms | 0.0005 ms | **~680× faster** |
| UIA address-bar queries / 100 calls | up to 100 | 1 | **−99 %** |
| App-detail analytics (1-year, 120k rows) | 160.8 ms | 0.3 ms | **~500× faster** |
| SQLite year-range scan (top apps) | 191.1 ms | 154.9 ms | −19 % |

> **RAM reality check:** the roadmap's original “< 15 MB resident” goal for a
> PySide6 application is not physically achievable — the Qt runtime alone is
> tens of megabytes. Lazy page loading does cut the startup footprint from the
> full 178 MB (all pages) to ~75 MB (landing page only), which is the practical
> win.

---

## 2. A — Event-driven Win32 hooks

**Before:** a 500 ms loop called `GetForegroundWindow()` + `GetLastInputInfo()`
on every tick, even when nothing changed.

**After:** `tracker/win_events.py` installs two `SetWinEventHook` hooks on a
dedicated message-pump thread:

- `EVENT_SYSTEM_FOREGROUND` — active window changed.
- `EVENT_OBJECT_NAMECHANGE` — title/tab changed; filtered to the foreground
  window and throttled to 5 notifications/s so background apps that rewrite
  their captions cannot generate a wake storm.

Events coalesce into a generation-counted `Condition`, so N tab switches before
the loop wakes still require only one foreground re-read. The tracking loop:

- wakes immediately on a hook event;
- otherwise wakes every 2 s (`TRACKING_TICK_INTERVAL_S`);
- re-reads the foreground window at most every 5 s as a safety net
  (`FOREGROUND_SAFETY_INTERVAL_S`);
- falls back automatically to 500 ms polling when hooks cannot be installed
  (`DW_DISABLE_WINEVENT_HOOK=1`, non-Windows, or hook registration failure).

Accounting remains correct: the loop passes the real elapsed time to
`ProtectionManager.tick` (clamped to 5 s after hibernation) instead of a fixed
500 ms constant, and attributes that interval to the app that was active
*during* it, before applying a switch.

**Why not go fully event-only?** A pure event loop can silently miss a hook
under load or after an explorer restart. A bounded 5 s safety poll costs
~0.06 ms and guarantees the session cannot remain attached to the wrong window
indefinitely — a better reliability/CPU trade-off than “events or bust”.

---

## 3. B — Native extension: re-scoped, not built

The roadmap proposed compiling `dw_native.pyd` (C/Rust) for process enumeration
and UI Automation. After profiling, this was deliberately **not** pursued:

1. **The expensive Win32 calls are already native.** `GetForegroundWindow`,
   `QueryFullProcessImageNameW`, `GetLastInputInfo`, and `XInputGetState` are
   called directly through `ctypes`. `get_foreground_app()` measures 0.064 ms;
   the remaining cost is Python object construction, not the syscall.
2. **UI Automation cannot be meaningfully wrapped in a tiny extension.** The
   expensive part is COM/UIA tree traversal, which still runs through COM; a C
   shim would add marshalling, not remove it. The caching/work-queue work in
   section C attacks the actual cost.
3. **Packaging cost is high and recurring.** A CPython-ABI `.pyd` must be
   rebuilt for every Python minor version, signed, and added to PyInstaller's
   `binaries` list. This project ships a single Windows installer from GitHub
   Actions; adding a native toolchain to that path is a large reliability risk
   for a measured saving of microseconds.
4. **The < 15 MB RAM target is unattainable for this stack** (see above).

Instead, the same goals were met with zero build-system risk: cached process
lookups, memoised title parsing, throttled controller probes, and a single
coalescing UIA worker. If a native helper is ever justified, it should be a
separate opt-in package with an ABI-free IPC boundary, not a required `.pyd`.

---

## 4. C — UI Automation caching

`tracker/browser_domain.py` previously spawned a new daemon thread for every
unresolved title. Rapid tab switching in Chromium could create dozens of
threads, each starting COM and walking the accessibility tree.

Now there is **one** resolver thread with a bounded queue:

- **Latest request wins per window** — a newer title replaces the pending one
  instead of queueing another COM traversal.
- **Positive TTL 30 s** — a resolved domain is served without another query.
- **Stale-while-revalidate up to 45 s** — the last known domain is returned
  immediately while a refresh runs in the background.
- **Negative TTL + exponential backoff (5 s → 120 s)** — browsers whose address
  bar the resolver cannot read no longer trigger a query every tick.
- **Bounded LRU (256 windows)** — no unbounded memory growth.
- **Title-keyed entries** — a new tab never inherits the previous tab's domain.

Measured: 100 consecutive calls with an unresolvable title produced **1** UIA
query (99 cache hits), versus up to 100 before.

---

## 5. D — SQLite engine tuning

`database/repository.py`:

- `PRAGMA mmap_size` — adaptive: `min(256 MB, max(32 MB, database size))`,
  disabled on 32-bit interpreters. Avoids mapping 256 MB for a fresh database
  while still giving multi-year installs a large window.
- `PRAGMA busy_timeout=5000` — UI analytics no longer fail during a tracker
  commit.
- `PRAGMA wal_autocheckpoint=1000`, existing `synchronous=NORMAL`,
  `cache_size=-8000`, `temp_store=MEMORY`.
- `PRAGMA optimize` before a connection closes, so index statistics stay fresh.

`database/schema.py` adds composite indexes:

- `app_sessions(process_name, start_time)`
- `app_sessions(category, start_time)`
- `website_sessions(domain, start_time)`
- `website_sessions(browser_process, start_time)`

The per-app detail path drops from **160.8 ms → 0.3 ms** because SQLite now
seeks directly into `(process_name, start_time)` instead of scanning every row
in the date range. Whole-range aggregates (top apps, daily totals) improve
modestly because they still have to visit every matching row; the composite
index keeps the more selective per-app and per-domain queries fast.

---

## 6. E — Lazy UI instantiation

`MainWindow` used to build all 13 pages (and import every page module) in
`__init__`: 1766 widgets, 2.5 s. Now:

- 13 lightweight placeholder widgets reserve the stable page indices.
- On first navigation, `_ensure_page(index)` imports and constructs the real
  page, replaces its placeholder, wires its signals, and refreshes it.
- The dashboard's analytics refresh is deferred to the first event-loop turn,
  so the window shell paints before the first query + row building.
- `refresh_all_pages()` only touches instantiated pages; unvisited pages load
  fresh data when opened.
- App Locker/Focus Manager wiring is warmed 300 ms after startup, keeping their
  imports off the cold-start critical path.
- Legacy attribute access (`window._settings_page`, etc.) still works through
  lazy properties; updater callbacks use `get_loaded_page()` so a background
  update check never forces the Settings page to be built.

**Cost:** the first visit to a page now pays its construction time (Settings
≈425 ms cold, mostly imports). That work used to block startup unconditionally.

---

## 7. Additional hot-path fixes

These were not in the original roadmap but dominated real idle CPU:

1. **Adult-content classification was recompiling ~55 regexes per tick**
   (0.34 ms at 2 Hz). The keyword list is now one compiled alternation, and
   classification is memoised per `(title, domain)`. Non-adult pages are
   ~0.0005 ms after the first evaluation.
2. **The settings lookup ran before classification**, opening a SQLite cursor
   on every browser tick. Classification now runs first; the DB read happens
   only when a title actually matches.
3. **The XInput/joystick probe ran six Win32 calls on every idle sample.**
   `_check_controller_activity()` now probes at most once every 2 s; SleepGuard
   thresholds are measured in minutes, so this is imperceptible.
4. **Repeated title→domain regex parsing** is memoised (1024-entry LRU).

---

## 8. Measurement notes

- CPU percentages come from `psutil.Process().cpu_times()` deltas over a 20 s
  idle window; Windows reports at ~15.6 ms granularity, hence the 0.00–0.16 %
  spread. The tracker service excludes the Qt UI; the full app adds UI idle
  cost that is not part of the “tracker CPU” claim.
- Startup timing is the `MainWindow` constructor with a warm Python module
  cache; cold first-run timings vary with disk and font cache state.
- The SQLite benchmark inserts 120,000 app sessions and 60,000 website
  sessions into a temporary database (~43 MB), then timings are medians of
  three runs.
- The benchmark disables real Win32 hooks (`DW_DISABLE_WINEVENT_HOOK=1`) to
  keep runs deterministic; hook availability is exercised by the unit tests.
