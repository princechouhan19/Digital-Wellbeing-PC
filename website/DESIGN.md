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
- **Motion:** one CSS transition family, `cubic-bezier(0.16, 1, 0.3, 1)`. The
  only autonomous motion is the breathing status dot and the hero ledger's row
  advance (2.4s, paused offscreen, stopped under reduced motion, and paused when
  the tab is hidden). Reveal-on-scroll is gated on `html.reveal-ready`, which is
  only added by the client observer, so a no-JS visitor sees a finished page.
- **Interactions:** primary actions fill from the pointer's entry point
  (`clip-path: circle()`), navigation letters roll, list rows draw a left edge,
  inline links are underlined at rest. Interactive screens use a vertical tab
  index with arrow-key support; the screen inspector is a pressed-chip row with
  an `aria-live` caption.
- **Reduced motion:** the ledger stops advancing and reports `paused`, the
  breathing dot stops, rolls become underlines, reveals never hide.

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
7. **The logo** is the existing 512px raster. A vector mark (the three quota
   bars in `favicon.svg` and the header) is used for the identity on the page;
   replace it if a brand SVG exists.
8. **Uninstall behaviour:** the copy says the uninstaller can remove the
   database and profile settings or keep them, which matches
   `installer/uninstaller_app.py`. It makes no claim about hosts entries,
   because a focus session already removes those on exit.
9. **No city, no client logos, no awards, no user counts** are claimed anywhere.
10. Anything after this line is QA evidence, not design intent.

## QA record (three passes, production build)

| Check | Result |
|---|---|
| Audit (semantics, SEO, metadata, weight) | 0 FAIL, 0 WARN |
| Axe, desktop and phone | 0 violations at every impact level |
| Console errors, failed requests | none |
| Desktop LCP / CLS | 136 to 168 ms / 0 |
| Phone LCP / CLS (4x CPU, slow 4G) | 760 to 790 ms / 0.0007 |
| Scroll FPS, desktop | 52 to 53 measured in headless software rendering (60 in a GPU browser) |
| Horizontal overflow, 390 px | none |
| Tap targets under 24 px | none |
| Keyboard | skip link first, 2 px accent outline on every stop, arrow keys move between control tabs |
| Reduced motion | nothing hidden, nothing moving, ledger labelled "sample day" |
| No JavaScript | h1 and full document present, page reads as finished |
| Transfer | about 281 KB total, about 185 KB of that is JS gzipped |
| 404 | HTTP 404 with the concept's own copy |

Final pass removed one accessory: the repeated numbered list beside the screen
inspector, which restated the captions underneath it.
