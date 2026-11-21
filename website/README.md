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
| `src/app/docs/` | The documentation section: an index and one page per document. |
| `src/content/docs.generated.ts` | Generated copy of the Markdown. Never edit by hand. |
| `src/components/docs/markdown.tsx` | The Markdown to JSX renderer used by the doc pages. |
| `tools/sync-docs.mjs` | Copies `docs/*.md`, `PRIVACY.md` and `CHANGELOG.md` into the site. |
| `src/app/llms.txt/route.ts` | Plain-text index of the product and the docs for tools that read sites. |
| `src/fonts/` | Schibsted Grotesk and JetBrains Mono woff2 (SIL OFL), loaded with `next/font/local`. |
| `DESIGN.md` | The concept, palette, typography, and the list of placeholders to replace. |

## Editing the page

- Copy changes go in `src/data/site.ts`. Do not hard-code strings in components.
- The site's argument is: record only what matters, then act on the process
  table, the hosts file, and the timer. Keep new sections inside that metaphor.
- Two rules that are easy to break: no em dashes or en dashes in visible copy,
  and every quota number must come from a real source (the release asset, the
  benchmark document, or the version file).

## Documentation pages

The `/docs` section renders the repository's own Markdown, so there is one
source of truth:

1. Edit the file in `docs/`, `PRIVACY.md` or `CHANGELOG.md` as usual.
2. Run `npm run docs`, which rewrites `src/content/docs.generated.ts`.
   `npm run build` runs it for you; `npm run docs:check` fails when it is stale.
3. Titles, summaries, topic grouping and the "written against an older build"
   notes live in `docPages` in `src/data/site.ts`.

Version references inside the rendered documents are pointed at the current
release, except on the changelog, where every old number is the point. Icons
come from `assets/icons/app_logo.png`, copied to `src/app/icon.png`,
`public/logo.png` and `public/images/mark.png`; the favicon is
`assets/icon.ico`.

## Version bumps

Update these together, then run `npm test`:

1. `src/config/site.ts` (`version`)
2. `src/data/site.ts` (`site.version`, `site.installerSize`, `site.releaseDate`)
3. `src/app/api/download/route.ts` (installer file name)
4. `src/app/api/stats/route.ts`
5. `src/__tests__/download.test.ts`
6. `npm run docs` if a document names the version

## Deploying

The repository root has a `vercel.json` that builds `website/` with
`@vercel/next`. Either keep that or set the Vercel project root to `website` and
let Vercel detect the build. No environment variables are required;
`DW_DOWNLOAD_URL` optionally overrides the GitHub release redirect.
