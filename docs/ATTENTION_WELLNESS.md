# Attention & Wellness Features (v4.2)

This document covers the Advanced Attention & Wellness work delivered in v4.2:
granular web rules, flow analytics, circadian display warm-up, strict lockout,
and the Focus page redesign.

Everything is local-first: there are no remote endpoints, no browsing-history
uploads, and no telemetry.

---

## 1. Sub-path web filtering

### Rule model

Rules live in `protection/url_rules.py` and are stored as JSON in the local
SQLite settings table (`focus_url_rules`). A rule is a **host + optional path
prefix** with an `allow` or `block` action:

| Rule | Action | Effect |
|---|---|---|
| `youtube.com/shorts` | block | Blocks Shorts while the rest of YouTube stays available (default allow). |
| `reddit.com/r/all` | block | Blocks r/all. |
| `reddit.com/r/programming` | allow | Allows the productive sub-reddit even when the mode blocks reddit.com (default block). |

Resolution rules:

1. Normalise the URL: strip scheme/`www.`/query/fragment, lowercase the host and path.
2. Match a rule when the host is equal or a subdomain, and the path is equal or a
   child of the rule path (`/r/programming` matches `/r/programming/comments/…`).
3. The **longest path** wins; then the most specific host; ties favour `block`.
4. If nothing matches, the Focus mode's domain default applies: block if the
   domain is in the mode's website list, otherwise allow.

### Enforcement paths

**Browser extension (primary, required for sub-paths).**
`protection/extension_bridge.py` runs a `ThreadingHTTPServer` bound to
`127.0.0.1` (default port 47823, ephemeral fallback). It requires a per-install
token stored in SQLite. Endpoints:

```text
GET  /v1/health   -> {ok, service, port}
POST /v1/check    -> {action, reason, rule, domain, mode, seconds_remaining}
```

The bundled extension in `assets/browser_extension/` sends the active tab URL
on navigation/activation (and once a minute), then redirects blocked tabs to a
local `blocked.html`. It fails open if the app is closed. URLs are evaluated in
memory and never logged or persisted by the bridge.

Install: `chrome://extensions` → Developer mode → **Load unpacked** →
`assets/browser_extension`, then paste the port/token shown in
**Focus → Guardrails → URL rules**.

**Desktop fallback (domain level).** The existing Focus foreground scan still
closes domain-blocked browser tabs via the hosts integration. When the bridge
has a recent URL for that browser and the host matches, the same scan uses the
full URL so sub-path rules work even if the extension missed an event.

### Extension support

Chromium MV3: Chrome, Edge, Brave, Opera, Vivaldi. Firefox uses a different
extension API and is not covered by this bundle. The extension is optional;
without it, the app retains domain-level blocking.

---

## 2. Flow analytics

Implemented in `analytics/engine.py`; rendered on **Insights → Attention
Quality**.

### Focus Fragmentation Index

- A **switch** is the start of a non-idle application session.
- Switches are grouped into 24 hourly buckets.
- Session time is split across hour boundaries so a long session does not
  inflate one hour.
- `fragmentation_index = switches / active_hours` (active hours from actual
  active seconds, floored at 0.25 to avoid division blow-ups).
- The card shows the index, total switches, peak hour, and an hourly bar chart.

### Flow Continuity Tracker

- Considers sessions in **Programming**, **Productivity**, and **Education**.
- Adjacent productive sessions merge when the gap is ≤ 120 seconds; any
  non-productive session, a larger gap, or idle time ends the block.
- Blocks of **45+ minutes** qualify as flow.
- Returns total flow time, the longest block, recent blocks, and today's flow.
- The card highlights the longest run (application + duration) and lists the
  most recent flow blocks.

No score is invented or normalised to a pseudo-psychology scale; the labels are
direct measurements from the local session log.

---

## 3. Circadian display warm-up

Implemented in `protection/circadian.py`; controls live on **SleepGuard →
Circadian display warm-up**.

### Schedule

- Bedtime and wake time come from the existing `bedtime_start` /
  `bedtime_end` SleepGuard settings.
- `circadian_lead_minutes` (default **90**) starts the ramp.
- Over the lead window, colour temperature interpolates linearly from **6500 K**
  to `circadian_target_kelvin` (default **3400 K**).
- During the bedtime window the target is held; at wake it returns to 6500 K.

Example (23:00 bedtime, 06:00 wake, 90-minute lead):

| Time | Phase | Kelvin |
|---|---|---|
| 12:00 | day | 6500 |
| 21:30 | winding down starts | 6500 |
| 22:30 | winding down | ≈4400 |
| 23:30 | night | 3400 |
| 06:30 | day | 6500 |

### Implementation

- Uses per-monitor `GetDeviceGammaRamp` / `SetDeviceGammaRamp`.
- Captures each display's original ramp before the first change and scales it
  by the colour-temperature channel factors (strongest channel remains 1.0).
- Restores every display on disable, schedule stop, and normal process exit.
- Deliberately does **not** write the undocumented Windows Night Light
  registry blob; gamma ramps are reversible and need no elevation.

A timer checks once a minute and only touches the display when the computed
state changes. If the process is force-killed, the display may stay warm until
Windows resets the ramp (logoff/reboot); this is documented rather than hidden.

---

## 4. Strict Lockout ("Hardcore Mode")

### What it does

- Optional per-session flag in the Focus setup card.
- Once started:
  - the stop button is hidden and `stop_focus()` returns `False`;
  - the PIN escape hatch is disabled (`stop_focus_after_pin_dialog()` also returns `False`);
  - closing the main window is ignored; minimizing is immediately undone;
  - tray **Quit** is denied;
  - the active session (mode, total, deadline, lockout flag) is persisted to
    `focus_active_session` in SQLite;
  - a normal unprivileged watchdog process is spawned.
- If the app is killed before the deadline, the watchdog relaunches the app
  once. The new process restores the persisted session and continues the
  countdown. If the deadline already passed, the setting is cleared and any
  hosts blocks are removed.

### Honest limitations

This is **best-effort tamper resistance**, not a security boundary:

- An administrator can kill the app and the watchdog, or reboot the machine.
- Safe Mode is not intercepted (deliberately: the app does not install a
  service/driver, modify boot configuration, or disable Task Manager).
- If autostart is disabled, a reboot will not resume the session.
- Changing the system clock can affect the persisted deadline.

The confirmation dialog states these limitations before a session starts. We
consider that preferable to shipping permission-escalating persistence.

---

## 5. Focus page redesign

The previous page nested mode cards, timer controls, app lists, website lists,
and toggles inside one large card. The redesign separates concerns:

```text
┌ Focus ───────────────────────────────────────────────────────────┐
│  FOCUS MODE   [Deep] [Work] [Study] [Media] [Custom]             │
├──────────────────────────────┬───────────────────────────────────┤
│  SESSION                     │  GUARDRAILS   [Apps|Websites|Rules]│
│  circular timer              │  one curated list per tab         │
│  duration presets + start    │  sub-path rules + bridge status   │
├──────────────────────────────┴───────────────────────────────────┤
│  SESSION PROTECTION   Strict [toggle]   Lockout [toggle]         │
└──────────────────────────────────────────────────────────────────┘
```

Key changes:

- `FocusTimerWidget` is now a transparent root; the giant nested card is gone.
- Mode selection is its own card.
- Timer + start action is its own card.
- Guardrails use a three-tab segmented panel (Apps / Websites / URL rules) so
  only one list is visible at a time.
- Strict and Lockout are grouped in a separate Session Protection card with
  plain-language caveats.
- Active sessions become a calm, centered cockpit; lockout hides the stop
  action and labels the state as locked.

The host `WellbeingPage` keeps a single header and status capsule, with a wider
content column. It no longer wraps every control in one visual container.

![Redesigned Focus page](screenshots/dark_focus.png)

---

## 6. Key files

| Area | File |
|---|---|
| URL rules engine | `protection/url_rules.py` |
| Loopback bridge | `protection/extension_bridge.py` |
| Browser extension | `assets/browser_extension/` |
| Rules editor | `ui/widgets/url_rules_dialog.py` |
| Flow analytics | `analytics/engine.py` |
| Attention cards | `ui/widgets/attention_cards.py` |
| Circadian engine | `protection/circadian.py` |
| Circadian UI | `ui/widgets/circadian_section.py` |
| Lockout watchdog | `protection/focus_watchdog.py` |
| Focus widget | `ui/widgets/focus_timer.py` |
| Focus page | `ui/pages/wellbeing.py` |
| Tests | `tests/test_attention_wellness_features.py` |
