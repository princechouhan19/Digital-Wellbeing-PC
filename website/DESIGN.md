# Digital Wellbeing website: design record

This file is the builder's record. It is not part of the shipped page and it is
not shown to a blind critic. The page itself is the deliverable.

## Brief

- **Subject:** Digital Wellbeing, a local-first screen time tracker and
  attention control app for Windows 10 and 11, maintained by Prince Chouhan.
- **Audience:** people who already suspect their PC is eating their day:
  students, developers, freelancers, parents. They are sceptical of
  "productivity score" apps.
- **Job of the site:** get a download, and explain in under a minute why this
  one is different from a browser extension.
- **Language:** English.
- **Constraints:** keep the Next.js App Router stack and the existing API
  routes. No analytics, no third-party scripts, no invented metrics, no
  invented clients. The build must work offline (the previous `next/font/google`
  import failed in a sandbox with no route to fonts.googleapis.com).

## Concept

```
Idea:        The website is the app's own foreground ledger, printed large.
Metaphor:    A local system monitor: process names, quotas, a register of what
             is written to disk, a hosts file, a storage path.
Signature:   The hero instrument (src/components/home/ledger-panel.tsx): a live
             ledger of foreground events where blocked rows turn red with their
             spent quota, plus vertical quota meters. It is the product's own
             data model, not a decorative mockup.
Emotion:     "Someone finally built the grown-up version of this."
Motion verb: Record. Rows arrive, meters fill, one dot breathes. Nothing floats,
             nothing fades up on every card, nothing follows the cursor.
Screenshot:  The hero at 1440: huge two-tone claim on the left, ledger on paper
             with a red "quota 45 of 45 m, suspended" line on the right.
Anchor:      Digital Wellbeing writes exactly four kinds of row to a local
             SQLite file. The site is built out of those rows, so it cannot be
             moved to another brand without becoming a different site.
```

### Concepts considered

1. **Ledger / register (chosen).** Anchor: the app's own database tables.
   Layout rule: everything is a ruled row or a measured column. Motion verb:
   record. Palette source: graphite paper and monitor phosphor. Signature: the
   live ledger. Risk: can read as "admin dashboard" if type craft is weak.
2. **Hosts file as the visual system.** Anchor: Focus Mode's delimited block in
   `drivers\etc\hosts`. Strong and specific, but it only explains one of four
   controls, so it was demoted to one figure inside section 01.
3. **Bedtime / night watch.** Anchor: SleepGuard. Warm, emotional, and
   wrong for a product whose main claim is mechanical control. Rejected.

Scores (originality, fit, feasibility, portability, lower is better): 1) 4/5/5/1
= winner. 2) 4/4/5/2. 3) 3/3/4/3.

## Art direction

| Role | Light | Dark |
|---|---|---|
| ground | `#f4f4f1` (paper, not white) | `#080a0d` (monitor black) |
| panel | `#ffffff` | `#0d1116` |
| panel-2 | `#ecece7` | `#12181f` |
| ink | `#101418` | `#eef2f5` |
| muted | `#4d5854` (5.9:1 on ground) | `#9aa7b4` |
| line | ink at 12% | white at 9% |
| accent | `#067a58` (quota OK, 4.6:1 on ground) | `#2ad59b` |
| alert | `#c2371a` (quota spent) | `#ff7a59` |

Accent and alert carry meaning: green is a quota with time left, red is a quota
that is spent or a domain the hosts file rejected. They are never used as
decoration.

- **Type:** Schibsted Grotesk for everything (display, text, UI) and JetBrains
  Mono for time stamps, file paths, quota numbers, and labels. Both are
  self-hosted woff2 (SIL OFL) in `src/fonts`, loaded through `next/font/local`,
  so the build has no network dependency and no layout shift.
- **Grid:** 12 column fluid grid, `max-width: 84rem`, gutters equal to the outer
  margin. Hero is 7/5. Register is 5/7. Controls is 5/7. Screens is 4/8. Install
  is 7/5. Every section has a different layout family: instrument, pull quote,
  register with code figure, verb index with evidence, screen inspector,
  measured readout, numbered steps plus spec table.
- **Rhythm:** sections alternate between `ground` and `panel` at 50% so the page
  reads as ruled bands, the way a ledger page does.
- **Shape:** one radius family (8px for small, 12px for panels, pill for
  actions). Hairlines at 1px everywhere.
- **Motion:** one CSS transition family, `cubic-bezier(0.16, 1, 0.3, 1)`, and
  the choreography in the section below. The only autonomous motion is the
  breathing status dot and the hero ledger's row advance (2.4s, paused
  offscreen, stopped under reduced motion, and paused when the tab is hidden).
  Every entrance is gated on `html.motion` and `html.reveal-ready`, both added
  by client code, so a no-JS visitor sees a finished page.
- **Interactions:** primary actions fill from the pointer's entry point
  (`clip-path: circle()`), navigation letters roll, list rows draw a left edge,
  inline links are underlined at rest. Interactive screens use a vertical tab
  index with arrow-key support; the screen inspector is a pressed-chip row with
  an `aria-live` caption.
- **Reduced motion:** the ledger stops advancing and reports `paused`, the
  breathing dot stops, rolls become underlines, reveals never hide.

## Motion system

The metaphor is record, so motion shows a state change a system monitor would
log: a row appears, a bar fills, a limit is crossed, a rule is written. Nothing
floats, nothing loops on scroll, nothing follows the cursor. There is no scroll
listener: one `IntersectionObserver` (`src/components/system/motion.tsx`) adds
`is-in` once per element and unobserves it. Everything it drives is a CSS
transition or keyframe.

Progress is carried in custom properties (`--meter-progress`, `--reveal-delay`,
`--i`), resolved into `transform`, `opacity` and `translate`. That keeps the
animated properties compositor-friendly and out of the scroll thread. No
animation library is installed; the page still ships zero third-party client
JavaScript.

| Set piece | What moves | Trigger | Timing |
|---|---|---|---|
| Hero boot: ledger rows | opacity 0 to 1, settle up 10px | first paint, CSS keyframes under `html.motion` | 500ms per row, 60ms apart |
| Hero boot: daily quotas | bar `scaleX` 0 to value, left to right | the quota group enters the viewport | 750ms per bar, 90ms apart, 140ms in |
| Quota limit crossed | row label and ratio to `--alert`, ratio struck through, spent bar to `--alert` | fixed delay after that bar is full | starts at 920ms plus 90ms per row, 300ms to land |
| Section reveals | opacity 0 to 1, settle up 20px | `is-in` from the observer | 700ms, 70ms stagger, capped at six steps |
| Rule lines | 2px left rule scales from 0 to 1 in Y | the block's `is-in` | 550ms, 120ms after the block |
| Screen inspector | outgoing screen fades, incoming fades and settles 8px | chip press | 380ms |
| Readout figures | 0 to value, digits only | the figure enters the viewport | 900ms cubic ease-out, then the exact server string |

Why it suits the subject: the hero sequence is the product's promise in about a
second. Rows arrive one at a time, the meters fill in reading order, and the
first bar that passes its limit turns its row red with the quota line struck
through. A visitor who does nothing sees a working monitor, not a slideshow.

States:

- **Reduced motion:** `html.motion` is never added, so no rule below applies.
  Every element renders in its finished state: all 35 reveals visible, meters
  full, spent quotas red and struck, no running animation. The boot sequence is
  skipped rather than shortened.
- **No JavaScript:** `html.js` and `html.motion` are both absent. Nothing is
  hidden, the boot keyframes never start, and the full page reads as finished.
- **Runtime change:** if the OS reduced-motion setting flips after load, media
  queries inside `globals.css` resolve the reveals, rules and meters to their
  finished state even though the class on `<html>` is stale.
- **Tab hidden:** the live ledger pause is unchanged; entrance animations are
  not tied to visibility.

## What was removed from the previous site, and why

- The 1,537-line interactive sandbox app ("click through the product inside the
  marketing page"). It was the page's centre of gravity and it described the
  app's UI rather than its claim, while making the first screen feel like a demo
  booth. The hero now spends that space on the concept.
- Framer Motion, lucide-react, `@vercel/analytics`, `@vercel/speed-insights`,
  `next/font/google`, and four unused component files. The page ships zero
  third-party client JavaScript.
- The centred hero over a blurred gradient, the three equal feature cards, the
  "SYSTEM ARCHITECTURE" eyebrow over every heading, and the duplicated
  navbar/footer link lists.

## Running it

```bash
cd website
npm install
npm run dev        # http://localhost:3000
npm run build && npx next start -p 3000
npm test           # API and config tests
```

## Placeholders and assumptions the owner must confirm

1. **No code signing.** `build.py` skips signing when `cert.pfx` is absent, so
   the install section says Windows will show a SmartScreen prompt. Delete that
   step if a certificate ships.
2. **Sample data.** The hero ledger, quota meters and "3h 20m" style figures are
   scripted samples, labelled as such on the page. Real numbers never appear
   here.
3. **Performance figures** (74 MB, 0.08%, 0.5/s, 2.0s) are copied from
   `docs/PERFORMANCE.md` and attributed on the page. Re-measure before launch
   and update `readout` in `src/data/site.ts` if they drift.
4. **Installer size** is the GitHub release asset size for v4.4.5
   (190,234,744 bytes = 181 MB), and the download route now points at the
   `DigitalWellbeingSetup-4.4.5.exe` asset.
5. **Version** is taken from `version.json` (4.4.5). Update `site.version`,
   the download route, `src/config/site.ts`, and the test file together.
6. **App screenshots** in `public/images/app` come from the repository, are
   dark mode only, and still show the v4.1.0 build label in the window. Recapture
   them from 4.4.5 before launch.
7. **The logo** is now the product's own app icon from `assets/icons/app_logo.png`
   (copied to `src/app/icon.png`, `public/logo.png`, `public/images/mark.png`),
   with `assets/icon.ico` as the favicon. It is a raster with a white matte, so
   it sits on a white rounded tile in the header in both themes. A vector
   version of the same heart would let the mark sit directly on the ground.
8. **Uninstall behaviour:** the copy says the uninstaller can remove the
   database and profile settings or keep them, which matches
   `installer/uninstaller_app.py`. It makes no claim about hosts entries,
   because a focus session already removes those on exit.
9. **No city, no client logos, no awards, no user counts** are claimed anywhere.
10. Anything after this line is QA evidence, not design intent.

## Documentation section

`/docs` renders the repository's Markdown directly: twelve documents, ~16k
words, one page each, grouped by what the reader is trying to do rather than by
file name. The layout reuses the site's grid (contents rail in the first three
columns, prose in the last nine, capped at 42rem), and prose uses two type
sizes only: 16/1.72 body and monospace for code, file names and figures.

### Diagrams

Five figures are drawn as components in `src/components/docs/diagrams/`, in
the site's own tokens, so they follow the light and dark theme and stay sharp
at any size. Text stays real text: selectable, searchable, and read by a screen
reader in document order.

- `ARCHITECTURE.md` section 1: the four layers, with the privilege boundary in
  alert tone. Section 2B: one unlock, as three outcomes. Section 3: the three
  threads and the process boundary.
- `ATTENTION_WELLNESS.md` section 5: the Focus page layout. `ROADMAP.md`:
  milestones, marked shipped or not yet scheduled.
- The renderer swaps a ```mermaid fence for the figure registered to the H2 it
  sits under, and drops a ```text block that is only terminal art. Neither
  original is shown as source: a reader cannot use graph syntax, and the
  loaded fonts would not line up box characters. Unknown blocks are dropped,
  never dumped.
- A figure is not a screenshot. Nothing here claims to be a captured render of
  the running app; the screenshot section already carries those.

Three decisions worth keeping in a redesign:

- The page states provenance above the title. Where a source document names an
  older build, a note says so and the version references in the body are
  pointed at the current release; the changelog is the one exception, because
  there the old numbers are the content.
- A paragraph-level renderer, not a Markdown library. The files use headings,
  lists, tables, fenced code, blockquotes and four kinds of inline span. That
  is 300 lines of local code and no dependencies.
- Mermaid diagram sources are collapsed into a disclosure. A reader cannot use
  53 lines of graph syntax, and an expanded block pushes the prose away.

## QA record (three passes, production build)

| Check | Result |
|---|---|
| Audit (semantics, SEO, metadata, weight) | 0 FAIL, 0 WARN |
| Axe, desktop and phone, / and two doc pages | 0 violations at every impact level |
| Console errors, failed requests | none |
| Desktop LCP / CLS | 200 ms / 0.0001 |
| Phone LCP / CLS (4x CPU, slow 4G) | 760 to 792 ms / 0 |
| Scroll FPS, desktop | 60 measured in headless Chromium, p95 frame 16.7 ms |
| Horizontal overflow, 390 px | none |
| Tap targets under 24 px | none |
| Keyboard | skip link first, 2 px accent outline on every stop, arrow keys move between control tabs |
| Reduced motion | nothing hidden, nothing moving, meters full, spent quotas struck, ledger labelled "sample day" |
| No JavaScript | h1 and full document present, 0 of 35 reveals hidden, final figures, page reads as finished |
| Transfer | about 297 KB total measured in CDP encoded bytes, against 295 KB for the base commit with the same method |
| 404 | HTTP 404 with the concept's own copy |

Final pass removed one accessory: the repeated numbered list beside the screen
inspector, which restated the captions underneath it.

Documentation pass, added after the first three:

| Check | Result |
|---|---|
| Axe on six doc pages, desktop and phone | 0 violations |
| h1 per page | one, on every doc page |
| Horizontal overflow, 390 px, doc pages | none |
| Tap targets under 24 px, doc pages | none |
| Contents rail on a phone | folded into a disclosure; 30 anchors would push the article 2,000 px down |
| Home page after the icon and nav change | unchanged: 0 FAIL, 796 ms phone LCP, CLS 0, no console errors |
| Diagrams, 16 page and viewport combinations | 0 axe violations in both themes; wide figures take focus and scroll on a phone instead of shrinking below legible size |

Motion pass, production build, measured after the choreography landed. Base
commit numbers were taken from the same build and the same harness:

| Check | Result |
|---|---|
| Hero boot | rows reach full opacity one at a time, 60 ms apart, from 180 to 780 ms |
| Quota fill | three bars animate from 0 to their value left to right after the group enters view |
| Limit crossed | the spent row turns `--alert` and the quota line is struck through as its bar finishes, 300 ms to land, and it stays that way |
| Section reveals | 35 of 35 `.reveal` elements reach `is-in`; delays resolve to 0 to 350 ms in 70 ms steps |
| Rule lines | 5 rules finish at `scaleY(1)`, four in accent and the hosts figure in alert |
| Screen inspector | mid-swap measured at opacity 0.29 with a 5.6 px settle on the incoming screen; settles at 1 / 0 |
| Count-up | ends on 74, 0.08, 0.5 and 2.0, the exact strings in `site.ts` |
| Reduced motion | 0 of 35 reveals hidden, 0 animations running, meters full, spent quotas struck |
| No JavaScript | 8 sections, 7,255 characters of copy, 0 of 35 reveals hidden, final figures |
| Console errors | none on /, /docs, /docs/architecture in any state |
| Horizontal overflow, 390 px | none after the rule lines and the 8 px screen settle |
| Tap targets under 24 px | none |
| Transfer delta | +2 KB against the base commit, no new dependencies |
| npm test / tsc / eslint | 8 passing / clean / clean |

The third QA table, documentation pass, above is unchanged.
