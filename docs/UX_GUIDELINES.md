# UI Consistency Guidelines

These are the canonical page-level rules for Digital Wellbeing. They live in
`ui/design_system.py` as `PAGE_MARGINS`, `PAGE_SECTION_SPACING`, `CARD_RADIUS`,
`CARD_MARGINS`, `BUTTON_RADIUS`, and `BUTTON_RADIUS_PILL`.

## Page scaffold

Every routed page uses the same content column:

| Token | Value |
|---|---|
| Page margins | `32 px` left / `28 px` top / `32 px` right / `28 px` bottom |
| Section gap | `24 px` |
| Content width | Fill the available column — no fixed max-width or `AlignHCenter` wrapper |
| Page title | `26 px / 700`, `-0.5 px` tracking |
| Page subtitle | `13 px / 500`, muted |

The Focus page previously wrapped its suite in a `maxWidth(1180)` container and
centered it. That made every card narrower than the headers and every other
page. It now uses the same page scaffold as Dashboard, Insights, Settings,
SleepGuard, App Timer, App Locker, History, and the detail pages.

## Cards

| Token | Value |
|---|---|
| Card radius | `14 px` (`RADIUS["lg"]`) |
| Card padding | `20 px` horizontal / `18 px` vertical |
| Card border | `1 px` theme border |
| Card surface | `surface` (standard) or `surface_secondary` (inset) |

Avoid nesting a card inside another card solely for grouping. On the Focus page
mode selection, session, guardrails, and protection are separate top-level
cards; guardrail content is switched with tabs rather than stacked lists.

## Buttons and inputs

| Variant | Radius |
|---|---|
| Standard button / input | `10 px` (`RADIUS["md"]`) |
| Primary CTA / pill | `999 px` |
| Segmented item | `10 px` |
| Tag / badge | `6–8 px` |

All interactive controls keep a visible border or filled background; text-only
links are reserved for low-emphasis actions such as "Reset to 25m".

## Focus page rules

- The focus suite fills the page column; mode cards stretch evenly.
- Mode-card subtitles are shown when the suite is at least `880 px` wide and
  hidden below that to prevent horizontal overflow.
- Section order: **Focus Mode → Session + Guardrails → Session Protection**.
- Active lockout hides the stop action and states the limitation clearly.

## Checklist for new pages

- [ ] Uses `PAGE_MARGINS` and `PAGE_SECTION_SPACING`.
- [ ] Fills the content column; no arbitrary max-width/centering.
- [ ] Cards use `CARD_RADIUS` and `CARD_MARGINS`.
- [ ] Standard buttons use `BUTTON_RADIUS`; CTAs use `BUTTON_RADIUS_PILL`.
- [ ] No third level of nested cards for layout.
- [ ] Hover, focus, checked, and disabled states are defined.
- [ ] Verified at 1024, 1280, and 1440 px window widths.
