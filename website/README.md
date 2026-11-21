# Digital Wellbeing website

Landing page for Digital Wellbeing for Windows, the local-first screen time
tracker. Next.js App Router, TypeScript, Tailwind CSS v4, and two self-hosted
fonts. No analytics, no third-party client scripts, no cookies.

Live at [digitalwellbeing.vercel.app](https://digitalwellbeing.vercel.app).

---

## Run it

```bash
npm install
npm run dev                     # http://localhost:3000
npm run build && npm start      # production build, port 3000
npm test                        # download route, stats route, site config
```

## Where things live

| Path | What it is |
|---|---|
| `src/data/site.ts` | Every visible string, the four controls, the eight screens, the ledger sample, the install copy. |
| `src/config/site.ts` | Version, licence, canonical URL, and repository links. Read by the API routes and the tests. |
| `src/app/globals.css` | Design tokens (light and dark), the button fill, the letter roll, the meter, the ledger row. |
| `src/app/layout.tsx` | Metadata, JSON-LD, the pre-paint theme script, navbar and footer. |
| `src/app/page.tsx` | The page: hero, argument, register, controls, screens, readout, install, closing. |
| `src/components/home/` | The hero ledger, the control tabs, the screen inspector, and the section header. |
| `src/app/opengraph-image.tsx` | The 1200x630 share card, drawn in code so it never goes stale. |
| `src/fonts/` | Schibsted Grotesk and JetBrains Mono woff2 (SIL OFL), loaded with `next/font/local`. |
| `DESIGN.md` | The concept, palette, typography, and the list of placeholders to replace. |

## Editing the page

- Copy changes go in `src/data/site.ts`. Do not hard-code strings in components.
- The site's argument is: record only what matters, then act on the process
  table, the hosts file, and the timer. Keep new sections inside that metaphor.
- Two rules that are easy to break: no em dashes or en dashes in visible copy,
  and every quota number must come from a real source (the release asset, the
  benchmark document, or the version file).

## Version bumps

Update these together, then run `npm test`:

1. `src/config/site.ts` (`version`)
2. `src/data/site.ts` (`site.version`, `site.installerSize`, `site.releaseDate`)
3. `src/app/api/download/route.ts` (installer file name)
4. `src/app/api/stats/route.ts`
5. `src/__tests__/download.test.ts`

## Deploying

The repository root has a `vercel.json` that builds `website/` with
`@vercel/next`. Either keep that or set the Vercel project root to `website` and
let Vercel detect the build. No environment variables are required;
`DW_DOWNLOAD_URL` optionally overrides the GitHub release redirect.
