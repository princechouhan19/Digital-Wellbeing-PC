# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.3.1] — 2026-10-26

### Added
- **UI density setting** — Appearance → Interface Density (Comfortable / Compact). Compact mode tightens page margins to `24/20` and section spacing to `18 px` across already-open and newly opened pages.
- **PageScaffold / Card / Button primitives** adopted by the recap and report surfaces.

### Fixed
- Responsive Focus layout now fits at 1024 px; geometry tests cover 1024/1280/1440.
- Release automation: `tools/bump_version.py`, optional `installer/sign_artifact.ps1`, and the GitHub Actions release workflow.

## [4.3.0] — 2026-10-26

The **Momentum** release — post-session recaps, recurring Focus blocks, weekly attention reporting, a safe lockout exit, live fragmentation nudges, rule packs, and a command palette.

### Added
- **Focus Session Recap** — every session now persists duration, blocked apps/sites, interruptions, fragmentation vs. a seven-day baseline, and the best next focus window. The recap dialog includes Today / Yesterday / Previous 7 days history.
- **Recurring Focus schedules** — weekday/time/mode blocks with automatic start, mid-window joining, and duplicate-run protection. Managed from Focus → Session Protection → Schedules.
- **Weekly Attention Report** — seven-day fragmentation heatmap, average index, flow time, current/best flow streaks, best/worst hours, plus CSV, PDF, and clipboard summary export. Available from Insights → Weekly report, `Ctrl+K`, or the command palette.
- **Safe Lockout emergency exit** — hold for 10 seconds, confirm the PIN, then wait through a 15-minute cooldown. Lockout now requires a configured PIN.
- **Real-time fragmentation nudge** — after 12 switches in 30 minutes, a non-intrusive one-click 10-minute Focus reset appears (90-minute cooldown, suppressed during Focus and idle).
- **Rule packs & portability** — Study / Deep Work / Evening URL-rule presets plus JSON import/export in the Web Rules editor.
- **Command palette & shortcuts** — `Ctrl+K` actions, `Ctrl+Shift+F` quick 25-minute Focus, `Ctrl+Shift+R` last session recap.
- **UI primitives** — `PageScaffold`, `Card`, and `Button` in `ui/primitives.py`, with a density-aware scaffold foundation.
- **Release automation** — `tools/bump_version.py`, optional code-signing hook (`installer/sign_artifact.ps1`), and a GitHub Actions workflow that builds/uploads the installer, uninstaller, portable zip, and checksums.

### Fixed
- **Unified page rhythm** — every main page now uses the same `32/28/32/28` content margins and `24 px` section gap. The Focus page no longer wraps its suite in a narrow, centered `maxWidth(1180)` container; it fills the same content column as Dashboard, Insights, Settings, and the other pages.
- **Focus card consistency** — mode, session, guardrails, and protection cards use the standard `14 px` corner radius and `20/18 px` inner padding; the Focus title now matches the `26 px` page-title scale.
- **Responsive Focus layout** — mode cards, the session dial, and guardrail tabs fit at 1024 px; geometry regression tests cover 1024/1280/1440.
- **Rounded controls** — standard Focus buttons/inputs/tabs now use the `10 px` radius token; primary CTAs and pills use the full pill radius. Mode cards are responsive and hide subtitles below `880 px` instead of overflowing.
- Added `docs/UX_GUIDELINES.md` and `tests/test_ux_consistency.py` to prevent page-rhythm drift.

## [4.2.0] — 2026-10-23

The **Attention** release — event-driven performance work, granular web rules, flow analytics, circadian display warm-up, strict lockout, and a redesigned Focus page.

### Changed
- **Event-driven tracking engine** — the 500 ms polling loop is replaced by `SetWinEventHook` notifications for foreground and title changes (`tracker/win_events.py`), with event coalescing, a 2 s accounting tick, a 5 s safety poll, and automatic 500 ms fallback when hooks are unavailable. Foreground re-reads drop from 2/s to ≤0.2/s.
- **Lazy Qt page instantiation** — `MainWindow` now builds only the landing page at startup and constructs the other twelve pages on first navigation (`_ensure_page`). Cold construction drops from 2522 ms to ~185 ms, and startup widgets from 1766 to 95. Legacy `window._settings_page`-style access still works through lazy properties.
- **Deferred dashboard analytics** — the first dashboard query/row build runs on the first event-loop turn, so the window shell paints first.
- **SQLite tuning** — adaptive `PRAGMA mmap_size` (32–256 MB by database size, disabled on 32-bit), `busy_timeout=5000`, `wal_autocheckpoint=1000`, and `PRAGMA optimize` on close.
- **Browser UIA fallback** — replaced per-call thread spawning with a single bounded worker, latest-request-wins coalescing, a 30 s positive TTL, 45 s stale-while-revalidate, negative-cache backoff (5–120 s), and a 256-entry LRU. 100 unresolved-title calls now produce one UIA query.
- **Hot-path caches** — browser title→domain parsing is memoised; adult-content keyword matching uses one compiled alternation and memoised `(title, domain)` classification; the settings lookup only runs after a positive match; XInput/joystick probing is throttled to 2 s.
- **Focus page redesign** — removed the single nested cockpit card. Mode selection, session/timer, a tabbed guardrails panel (Apps / Websites / URL rules), and Session Protection are now separate cards. The URL rules tab shows local bridge status; the active view hides the stop action during lockout.
- **SleepGuard** now includes the Circadian display card beneath its power configuration.

### Added
- Composite SQLite indexes: `app_sessions(process_name, start_time)`, `app_sessions(category, start_time)`, `website_sessions(domain, start_time)`, `website_sessions(browser_process, start_time)`.
- `TrackingManager.get_performance_stats()` for Dev Mode diagnostics (hook availability, event wakeups, ticks, foreground queries).
- `docs/PERFORMANCE.md` with methodology and before/after measurements, plus `tools/benchmark_performance.py` to reproduce them.
- `tests/test_performance_optimizations.py` covering the watcher, throttled polling, idle probe, UIA cache, classifier cache, SQLite tuning, and lazy pages.
- **Granular sub-path web filtering** — `protection/url_rules.py` (host + path allow/block with most-specific-match resolution), a token-protected loopback bridge (`protection/extension_bridge.py`), an optional MV3 extension (`assets/browser_extension/`), and a Focus → Guardrails → URL rules editor. 100 unresolved-title calls still leave the app fully local; URLs are never logged.
- **Focus Fragmentation Index** — hourly task-switch analytics (`AnalyticsEngine.get_focus_fragmentation`) with an Apple-style bar card on Insights.
- **Flow Continuity Tracker** — merges productive programming/writing/study sessions across ≤2-minute gaps and highlights 45+ minute flow blocks (`AnalyticsEngine.get_flow_analytics`).
- **Circadian display warm-up** — reversible per-monitor gamma ramps driven by the SleepGuard bedtime (`protection/circadian.py`), with bedtime/lead/warmth controls on the SleepGuard page.
- **Strict Lockout mode** — optional non-cancelable Focus session with persisted deadline, close/minimize/tray-quit guards, and a best-effort relaunch watchdog (`protection/focus_watchdog.py`). The UI explicitly states that administrator/Safe Mode termination cannot be prevented.
- `docs/ATTENTION_WELLNESS.md` describing rule semantics, bridge endpoints, flow definitions, circadian schedule, lockout guarantees/limits, and the Focus layout.
- `tests/test_attention_wellness_features.py` covering URL rules, bridge round-trip, fragmentation/flow, circadian phases, lockout persistence, and the redesigned Focus page.

### Re-scoped
- The planned `dw_native.pyd` extension was not built: the hot Win32 calls are already native `ctypes` calls, COM/UIA traversal would not be removed by a C shim, and a per-Python-ABI binary adds significant packaging risk. The `< 15 MB` resident-RAM target is not achievable for a PySide6 application; lazy loading instead cuts first-paint RSS from ~178 MB to ~75 MB. See `docs/PERFORMANCE.md` for details.

## [4.1.0] — 2026-10-22

The **Digital Wellbeing** release — full rebrand to the product's real name, a first-run onboarding experience, the SafeBrowse content filter, and a batch of reliability fixes.

### Added
- **First-run onboarding** (`ui/onboarding.py`) — a five-step Apple-style welcome (greeting & name, live theme preview, personal goals, SafeBrowse opt-in, summary) with animated step transitions and progress dots. Replaces the old single name-prompt dialog; users who completed the v3 prompt migrate automatically.
- **SafeBrowse content filter** (`protection/content_blocker.py`) — system-wide adult content blocking:
  - Open-source blocklists (StevenBlack/hosts, MIT) with three coverage presets plus any custom hosts-format URL.
  - Curated offline seed list so filtering is active immediately, before the first sync.
  - Weekly background auto-refresh; lists cached in AppData for fully offline blocking.
  - Dedicated hosts-file section (`# DW-SAFEBROWSE`) that coexists safely with Focus Mode blocks; atomic backup + DNS flush; crash recovery on startup.
  - Settings card (`ui/widgets/safebrowse_section.py`) with live status, source picker, and manual sync.
- **Elevation infrastructure** (`utils/elevation.py`, `protection/elevated_helper.py`) — single-action UAC elevated helper for hosts operations with a JSON status handshake; Focus Mode now falls back to elevation when a direct hosts write is denied.
- **Opt-in anonymous stats** (`tracker/telemetry.py` rewrite) — the heartbeat is now off by default behind a Settings toggle, uses stdlib `urllib`, and requires an explicitly configured endpoint.

### Changed
- **Product renamed to "Digital Wellbeing"** across every surface: window titles, sidebar wordmark (DIGITAL / WELLBEING lockup), tray menu, dialogs, installer metadata, executable version info, website copy, and documentation. Legacy brand-named assets removed (`/logo.png` now canonical).
- **Settings copy** rewritten in Apple HIG tone: sentence-case section headers with a calmer eyebrow style, refined privacy architecture copy, removed emoji from status text.
- **Installer** produces `DigitalWellbeingSetup-<version>.exe`; Start Menu / Startup / desktop shortcuts and registry DisplayName now read "Digital Wellbeing".
- **Website** design tokens renamed from legacy `nyw-*` to neutral `dw-*`; support links route through GitHub Issues; SEO/canonical metadata updated.

### Fixed
- **Empty allowlist fail-open** — starting Focus in an allowlist mode (Study/Work/Movie/Deep) with no configured apps no longer blocks every user-facing application.
- **Duplicate browser registry** — `tracker/foreground.py` defined `BROWSER_PROCESSES` twice (the second silently shadowed the first); merged into one canonical 16-browser frozenset.
- **Broken `--elevated-helper`** — `main.py` referenced a non-existent `FocusManager.run_elevated_action`; now wired to the real `protection.elevated_helper` with an action allow-list.
- **Telemetry crash & drift** — the heartbeat used an unimported `requests` module and a dead endpoint; rewritten as opt-in with `urllib` and no hard-coded endpoint.
- **Missing WinRT dependencies** — `winrt-Windows.UI.Notifications` and `winrt-Windows.Data.Xml.Dom` added to requirements so toast notifications have their declared imports.
- **Hosts-file legacy migration** — managed blocks written by any older release format are now detected generically and migrated to the current delimiters on next write.

## [4.0.0] — 2026-10-21

The **Aurora** release — a ground-up Apple design system for Digital Wellbeing, replacing the v3 "NYW Deep Obsidian" language.

### Added
- **Aurora design system** (`ui/design_system.py`) — single source of truth for the new visual language: Apple system palette (light + dark), SF-metric type scale, radius scale (6/8/10/14/18/20), spacing scale, motion timing, and font bootstrap.
- **Bundled Inter & Inter Display fonts** (`assets/fonts/`) — SF Pro-metric typography, loaded at app startup (no longer dependent on Segoe UI Variable).
- **Haptics-lite** (`ui/feedback.py`) — semantic system sounds (tap / success / warning / error) via the native Windows sound scheme, plus a soft visual pulse for touch feedback. Toggle added to Settings → Appearance ("Interaction Sounds", on by default, `sound_feedback` setting).
- **SegmentedControl** widget — Apple-style segmented control with sliding selection (used for tabs and mode pickers).
- **Apple-style chart renderer** (`ui/widgets/charts.py`) — custom rounded-top gradient bars with a spring-out entrance animation replacing flat pyqtgraph rectangles; Inter axis ticks; hairline axes.
- **Donut sweep-in animation** — the category ring now draws itself clockwise on data refresh (Apple-activity-ring style) with theme-aware category colors.
- **Aurora page transitions** — pages rise 14px while fading in (260ms, quintic-out) instead of the old plain cross-fade.

### Changed
- **Accent color**: Tailwind Emerald `#10B981` → **Apple systemBlue** (`#0A84FF` dark / `#007AFF` light), applied app-wide via the token hub; ~280 hardcoded legacy hex/rgba values migrated to the Apple palette across 25+ files.
- **Category colors** now use the Apple system palette with dedicated light/dark variants (`CATEGORY_COLORS` / `CATEGORY_COLORS_LIGHT` / `get_category_colors()`).
- **Typography** normalized to the Apple hierarchy: Bold (700) display numerals in Inter Display with tight tracking, Semibold (600) emphasis, Regular (400) body; removed 800/900 weights and oddball sizes.
- **Radius scale** normalized (15 ad-hoc values → 6-step scale); cards 14px, hero cards 18px, controls 10px.
- **Surfaces**: soft-translucent Apple layering — opaque `#232326` cards on a `#1A1A1C` backdrop (dark) and white cards on `#F5F5F7` (light); hairline separators; iOS-style toggle (51×31, squish animation).
- **Sidebar** restyled as an Apple source list: tinted selection pill without borders, micro uppercase section headers, hairline separator.
- **Icons**: emoji/glyph buttons replaced with the SVG icon set (🧘/▶/■/↻/↺/← removed); new back/chevron/pause/download/trash/edit/zap icons.
- **Window/chrome**: tray menu, tooltips, menus, scrollbars, inputs, checkboxes and combo popups restyled to Apple patterns; Mica kept as a subtle backdrop under the solid base coat.
- Version metadata (version.json, file_version_info.txt) bumped to 4.0.0.

### Removed
- **Dead stylesheets**: `ui/theme/styles.qss`, `assets/styles/dark_theme.qss`, `assets/styles/light_theme.qss` — three fossilized design languages that no code loaded.

### Fixed
- PIN input in Settings was styled with a gradient string as `background-color` (invalid QSS) — now uses the proper input token.
- Debug `print()` on every app-row click removed.
- `test_theme_system.py` re-pinned to Aurora token values; new `test_aurora_design_system` test guards the palette/scales/category maps.

## [3.1.5] — 2026-08-30
### Added
- **Insights & Analytics** — Substantially improved data visualization, usage metrics, and historical reporting pages.
- **Settings UI** — Cleaned up the settings architecture to be premium, responsive, and functional.
- **SleepGuard** — Enhanced stability and shutdown warning presentation.

### Changed
- **Focus Mode** — Focus Mode is currently an Application-Only blocker. Website blocking has been temporarily disabled while the enforcement architecture undergoes refinement.

### Fixed
- **App Locker** — General stability and reliability improvements for native Windows Hello authentication integration.
- **Installer & Startup** — Stable and robust installer with automatic process termination on updates and clean application lifecycle management.
### Fixed
- Fixed App Locker UI obscuring the native Windows Hello authentication prompt by intelligently dropping topmost window privileges and presenting a minimal status surface while OS verification is active.

## [3.1.0] — 2026-08-23
### Added
- **App Locker** — Persistent per-application protection using Windows Hello (face, fingerprint, PIN) with NYW PIN as fallback.
- **Windows Hello integration** — Native WinRT `UserConsentVerifier` API via async QThread bridge; never blocks UI.
- **Authentication dialog** — Premium lock dialog with Windows Hello button, PIN fallback toggle, all result states handled gracefully.
- **Process picker** — Running-process browser + .exe file picker to add applications to the lock list.
- **App Locker page** — Dedicated sidebar navigation item (🔒 App Locker) with full settings (method, duration, locked app list).
- **Temporary access grants** — Once / 5 min / 15 min (default) / Until app closes. Grants are in-memory only (cleared on restart for safety).
- **Security guards** — Disabling App Locker, removing apps, or changing settings all require authentication.
- **SYSTEM_SAFE list** — explorer.exe, dwm.exe, csrss.exe, lsass.exe, NYW itself, and other critical Windows processes cannot be locked.
- App Locker configuration persists in SQLite (`app_locker_apps` table) and survives crashes/restarts.

### Fixed
- **Strict Focus Mode PIN unlock** — Correct PIN now properly stops Focus Mode. Fixed double-verification bug where `stop_focus()` re-checked PIN after dialog already validated it.

### Changed
- Navigation sidebar renumbered: App Locker = page 3, Settings = page 4, Dev = page 5.
- `requirements.txt` — Added `winrt-Windows.Security.Credentials.UI>=3.2.1`.

## [Unreleased]
### Added
- Initial project structure for Digital Wellbeing.
- PySide6 UI and Win32 tracking services.
- Local SQLite database implementation for crash-safe analytics.
