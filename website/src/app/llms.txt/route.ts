import { docPages, site } from "@/data/site"

/**
 * /llms.txt: the same library as /docs, in plain text, for tools that read a
 * site rather than browse it. Generated from data/site.ts so it cannot drift.
 */
export function GET() {
  const lines = [
    `# ${site.fullName}`,
    "",
    `> ${site.description}`,
    "",
    `${site.fullName} is a local-first screen time tracker for Windows 10 and 11 that also acts on what it records: focus sessions, daily app quotas, a biometric app locker and a hosts-level web filter. All data lives in one SQLite file at %LOCALAPPDATA%\\DigitalWellbeing\\digital_wellbeing.db. There is no account system, no cloud sync and no analytics.`,
    "",
    `Version: ${site.version} (${site.releaseDate})`,
    `Licence: ${site.license}`,
    `Source: ${site.repository}`,
    `Installer: ${site.url}/api/download (${site.installerSize}, not code signed yet)`,
    "",
    "## Documentation",
    "",
    ...docPages.map((page) => `- [${page.title}](${site.url}/docs/${page.slug}): ${page.summary}`),
    "",
    "## Pages",
    "",
    `- [Home](${site.url}/): what the tracker records, the four controls, the eight screens, measured figures and install steps`,
    `- [Documentation index](${site.url}/docs): every document in the repository, grouped by task`,
    "",
    "## Notes",
    "",
    "- Performance figures are from docs/PERFORMANCE.md, measured on v4.2.",
    "- The app writes exactly four kinds of row: app sessions, website sessions, daily totals, and event log entries.",
    "- Two network calls can leave the machine: an optional blocklist download and an opt-in heartbeat. Both are off by default.",
    "",
  ]

  return new Response(lines.join("\n"), {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  })
}
