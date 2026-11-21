/**
 * All visible copy and product facts for the marketing site live here.
 *
 * Sources (verified in the repository, not invented):
 *  - version / installer name: CHANGELOG.md + version.json (4.4.5)
 *  - installer size and asset names: GitHub release v4.4.5 (190,234,744 bytes)
 *  - database path, CSV export: PRIVACY.md, database/repository.py, utils/csv_exporter.py
 *  - hosts file path and managed block: protection/website_blocker.py
 *  - focus presets: protection/focus_manager.py
 *  - performance figures: docs/PERFORMANCE.md (section 1)
 *
 * Assumptions to confirm with the owner:
 *  - "Free and open source" reflects the MIT license in LICENSE.
 *  - The installer is not code signed (build.py skips signing without cert.pfx),
 *    so the copy warns about the Windows SmartScreen prompt instead of
 *    claiming a verified publisher. Replace this line if a certificate ships.
 *  - Performance numbers are copied from the owner's own benchmark document
 *    and are attributed on the page.
 */

export const site = {
  name: "Digital Wellbeing",
  fullName: "Digital Wellbeing for Windows",
  version: "4.4.5",
  releaseDate: "2 November 2026",
  installerSize: "181 MB",
  url: "https://digital-wellbeing-pc.vercel.app",
  description:
    "A local screen time tracker for Windows that acts on what it records: focus sessions, daily app quotas, biometric locks and a hosts-level web filter.",
  developer: "Prince Chouhan",
  license: "MIT",
  repository: "https://github.com/princechouhan19/Digital-Wellbeing-PC",
  releases: "https://github.com/princechouhan19/Digital-Wellbeing-PC/releases",
  issues: "https://github.com/princechouhan19/Digital-Wellbeing-PC/issues",
  checksums: "SHA256SUMS-4.4.5.txt",
} as const;

export const hero = {
  kicker: "Windows 10 and 11, 64-bit",
  title: ["Control your machine.", "Not the other way around."],
  standfirst:
    "A screen time tracker that also acts. Focus sessions cut the connection to distracting apps, daily quotas suspend them when the time is spent, and every byte stays on your own disk.",
  primaryCta: "Download for Windows",
  secondaryCta: "Read the source",
  installNote: `Version ${site.version} · ${site.installerSize} installer · Free and open source`,
};

/** The foreground ledger in the hero instrument. Times are a scripted sample day. */
export type Tick = {
  at: string;
  app: string;
  title: string;
  domain?: string;
  state: "active" | "idle" | "blocked";
  quota?: { used: number; limit: number; unit: string };
};

export const ledger: Tick[] = [
  { at: "14:02:10", app: "Code.exe", title: "machine.tsx · digital-wellbeing", state: "active" },
  { at: "14:03:44", app: "WindowsTerminal.exe", title: "npm run build", state: "active" },
  { at: "14:05:02", app: "chrome.exe", title: "docs · Next.js App Router", domain: "nextjs.org", state: "active" },
  { at: "14:07:31", app: "Discord.exe", title: "Discord · general", state: "blocked", quota: { used: 45, limit: 45, unit: "m" } },
  { at: "14:08:02", app: "Idle", title: "no foreground input for 4m 12s", state: "idle" },
  { at: "14:12:18", app: "Obsidian.exe", title: "reading queue", state: "active" },
  { at: "14:15:40", app: "chrome.exe", title: "Shorts", domain: "youtube.com", state: "blocked" },
  { at: "14:16:09", app: "Steam.exe", title: "Steam library", state: "blocked", quota: { used: 30, limit: 30, unit: "m" } },
  { at: "14:19:55", app: "Code.exe", title: "machine.tsx · digital-wellbeing", state: "active" },
];

export const quotas = [
  { app: "Discord.exe", used: 45, limit: 45, note: "quota spent, process suspended" },
  { app: "Steam.exe", used: 30, limit: 30, note: "quota spent, process suspended" },
  { app: "Spotify.exe", used: 42, limit: 90, note: "48 minutes left today" },
];

export const hostsBlock = `# >>> Digital Wellbeing focus >>>
0.0.0.0 youtube.com
0.0.0.0 www.youtube.com
0.0.0.0 x.com
0.0.0.0 reddit.com
0.0.0.0 www.reddit.com
0.0.0.0 tiktok.com
0.0.0.0 instagram.com
# <<< Digital Wellbeing focus <<<`;

/** What the tracker writes, and what it deliberately ignores. PRIVACY.md, sections 1 to 3. */
export const register = {
  written: [
    {
      field: "sessions",
      text: "Process name, executable path, window title, and the moment the window took or lost focus.",
    },
    {
      field: "idle",
      text: "Seconds since your last keystroke or mouse movement, sampled from GetLastInputInfo.",
    },
    {
      field: "website_sessions",
      text: "Root domain of the foreground tab, read from the address bar. youtube.com, never the video id.",
    },
    {
      field: "system",
      text: "Lock, unlock, sleep, and resume transitions, so counted time matches the time you were there.",
    },
  ],
  never: [
    "Keystrokes, clipboard contents, or typed text",
    "Mouse coordinates, clicks, or pointer trails",
    "Page content, cookies, or search queries",
    "Camera, microphone, or screen capture",
    "Accounts, email addresses, or payments",
    "Cloud sync, analytics, or usage beacons",
  ],
  network: [
    {
      call: "Blocklist download",
      when: "Only when SafeBrowse is switched on, over HTTPS from an open hosts list.",
      sent: "A request for the list. Nothing about you.",
    },
    {
      call: "Opt-in heartbeat",
      when: "Off by default. You point it at an endpoint you choose.",
      sent: "OS version, app version, runtime state. No windows, no domains, no names.",
    },
  ],
  storage: "%LOCALAPPDATA%\\DigitalWellbeing\\digital_wellbeing.db",
  exportNote: "Every session can be exported to CSV from the app, and the SQLite file is yours to open.",
};

export type Control = {
  id: string;
  label: string;
  verb: string;
  headline: string;
  body: string;
  facts: string[];
  screen: string;
  alt: string;
  caption: string;
};

export const controls: Control[] = [
  {
    id: "focus",
    label: "Focus",
    verb: "Removes",
    headline: "The distracting process is not running, so there is nothing to negotiate.",
    body: "Focus sessions switch Windows into an allowlist. Presets for Study, Work, Movie and Deep Focus decide which executables may launch, and a managed block in the Windows hosts file takes the matching domains offline at the DNS level.",
    facts: [
      "Allowlist enforced per process, not per browser tab",
      "Hosts block is delimited and removed cleanly on exit",
      "explorer.exe and system services are never touched",
    ],
    screen: "/images/app/focus-dark.png",
    alt: "Focus page of the app, showing profile presets and the allowlist of permitted applications",
    caption: "Focus configuration, presets, and the process allowlist",
  },
  {
    id: "timer",
    label: "App Timer",
    verb: "Limits",
    headline: "A daily number instead of a vague intention.",
    body: "Give each distracting application an allowance. When the allowance runs out, the process is suspended gracefully, with a warning first, so an open document does not disappear mid-sentence.",
    facts: ["Presets at 15m, 30m, 1h and 2h", "Timers pause while you are idle or locked", "App Timer and App Locker stay isolated"],
    screen: "/images/app/app-timer-dark.png",
    alt: "App Timer page listing daily allowances per application with progress meters",
    caption: "Daily allowances per application",
  },
  {
    id: "locker",
    label: "App Locker",
    verb: "Locks",
    headline: "Windows Hello in front of the apps that hold your private life.",
    body: "Keep messaging, banking, and game clients behind face or fingerprint recognition, or a PIN hashed with PBKDF2 and a random salt. Launch attempts are intercepted before the window appears.",
    facts: ["Face, fingerprint, or local PIN", "Biometrics never reach the app", "Each app can be locked separately"],
    screen: "/images/app/app-locker-dark.png",
    alt: "App Locker page with locked applications and Windows Hello prompt",
    caption: "Per-app locks with Windows Hello",
  },
  {
    id: "sleepguard",
    label: "SleepGuard",
    verb: "Sleeps",
    headline: "The machine sleeps when you already have.",
    body: "Falling asleep with a video running used to cost a whole night of screen time. SleepGuard watches for genuine inactivity after your bedtime window, gives a single countdown dialog, then sleeps the PC. Media and lecture detection keeps it from interrupting a class.",
    facts: ["Bedtime window you define", "Sleep, lock, or hibernate", "Paused during calls and lectures"],
    screen: "/images/app/sleepguard-dark.png",
    alt: "SleepGuard page showing the bedtime schedule and the power action choices",
    caption: "Bedtime window and power action",
  },
];

export type Screen = { id: string; name: string; caption: string };

export const screens: Screen[] = [
  { id: "home", name: "Dashboard", caption: "Today's total, the category ring, and the hourly curve." },
  { id: "usage", name: "Usage", caption: "Hour by hour, active time separated from idle." },
  { id: "insights", name: "Insights", caption: "Week and month comparisons, without a wellness score." },
  { id: "focus", name: "Focus", caption: "Presets, allowlist, and the running session." },
  { id: "app-timer", name: "App Timer", caption: "Allowances and what happens when they run out." },
  { id: "app-locker", name: "App Locker", caption: "Per-app authentication through Windows Hello." },
  { id: "sleepguard", name: "SleepGuard", caption: "Bedtime behaviour and the countdown." },
  { id: "settings", name: "Settings", caption: "Database location, export, and personalisation." },
];

/** docs/PERFORMANCE.md, section 1. Attributed on the page. */
export const readout = [
  { value: "74", unit: "MB", label: "Resident memory at first paint", note: "Lazy page loading, measured with the dashboard only" },
  { value: "0.08", unit: "%", label: "Idle CPU, typical", note: "Event-driven foreground hooks instead of a 500 ms poll" },
  { value: "0.5", unit: "/s", label: "Tracker wakeups", note: "Four times fewer than v4.1" },
  { value: "2.0", unit: "s", label: "Accounting tick", note: "Real elapsed time is credited to the app that held focus" },
];

export const install = {
  steps: [
    { k: "01", t: "Download the installer", d: `${site.installerSize}, Inno Setup, version ${site.version}.` },
    { k: "02", t: "Confirm the publisher prompt", d: "Builds are not code signed yet, so Windows shows a SmartScreen warning. Choose More info, then Run anyway." },
    { k: "03", t: "Leave it running", d: "Tracking starts with Windows. The database is created on first launch in your local app data folder." },
  ],
  requirements: [
    ["Operating system", "Windows 10 or 11, 64-bit"],
    ["Runtime", "None. The installer bundles Python and Qt"],
    ["Installer size", `${site.installerSize} (190,234,744 bytes)`],
    ["Code signing", "Not signed. Verify the SHA-256 sum"],
    ["License", "MIT"],
    ["Network", "Only for optional blocklist downloads"],
  ],
};

export const footerNote = `© ${new Date().getFullYear()} ${site.developer}. Source under the MIT license.`;

export const colophon = [
  "Type: Schibsted Grotesk and JetBrains Mono, self-hosted, SIL Open Font License.",
  "No analytics, no cookies, no third-party scripts on this page.",
];

/* ==========================================================================
   Documentation library
   Source files: /docs/*.md in the repository root are copied into
   src/content/docs at build time (see README). Everything here that is not a
   topic label comes from the repository. Where a source page is stale, the
   page notes the current release instead of repeating the old number.
   ========================================================================== */

export type DocTopic = "start" | "use" | "protect" | "build" | "fix" | "source";

export const docTopics: { id: DocTopic; label: string; note: string }[] = [
  { id: "start", label: "Start here", note: "Install, first run, what the app writes" },
  { id: "use", label: "Every day", note: "Focus, quotas, locks, bedtime" },
  { id: "protect", label: "Protections", note: "Hosts filtering, locks, parental guards" },
  { id: "build", label: "Build from source", note: "Python, PySide6, installer" },
  { id: "fix", label: "Fix a problem", note: "Hosts, biometrics, browser domains" },
  { id: "source", label: "Read the source", note: "Architecture, CLI, releases" },
];

export const docsIndex = {
  title: "Documentation",
  lead:
    "Thirteen documents from the repository, rendered here unchanged in substance. The application ships no account system, so everything that matters is in these files.",
  note: `Written against version ${site.version}. Where a document still names an older build, the page says so in a note and points the version at the current release. The changelog keeps every number exactly as it shipped.`,
  quick: [
    { t: "Install it", d: "Installer, SmartScreen prompt, first-run wizard.", href: "/docs/user-guide" },
    { t: "Set a quota", d: "Daily limits on an app or a domain.", href: "/docs/user-guide#10-app-website-timers" },
    { t: "Stop the network call", d: "The two requests that leave your machine.", href: "/docs/user-guide#12-safebrowse-content-shield" },
    { t: "Restore the hosts file", d: "Backup file and the two commands.", href: "/docs/troubleshooting#1-hosts-file-safebrowse-issues" },
    { t: "Run from source", d: "Python 3.11 and newer, pip, python main.py.", href: "/docs/developer-guide" },
    { t: "See how it fits together", d: "Four layers, one elevated helper.", href: "/docs/architecture#diagram-architecture" },
    { t: "Cut a release", d: "Version bump, build script, checksums.", href: "/docs/releasing" },
  ],
};

export type DocPage = {
  slug: string
  title: string
  summary: string
  topic: DocTopic
  file: string
  /** Words in the repository file, rounded down to the nearest ten. */
  words: number
  /** Set when the source document names an older version than the release. */
  stale?: string
  /** Extra page-level facts kept next to the prose. */
  aside?: { k: string; v: string }[]
};

export const docPages: DocPage[] = [
  {
    slug: "roadmap",
    title: "Roadmap",
    summary: "What has shipped, what the phone companion needs, and what is not scheduled.",
    topic: "source",
    file: "ROADMAP.md",
    words: 1500,
    aside: [
      { k: "Shipped", v: `up to ${site.version}` },
      { k: "Format", v: "Milestones, then feature detail" },
    ],
  },
  {
    slug: "privacy",
    title: "Privacy policy",
    summary: "What is stored, where it lives, and the two requests that can leave the machine.",
    topic: "protect",
    file: "PRIVACY.md",
    words: 890,
    stale: "The header names v4.3.2 and later; the current release is v4.4.5.",
  },
  {
    slug: "changelog",
    title: "Changelog",
    summary: "Every release from 4.0.0 to 4.4.5, in the order it shipped.",
    topic: "source",
    file: "CHANGELOG.md",
    words: 3900,
    aside: [
      { k: "Current release", v: `${site.version}` },
      { k: "Released", v: "2 November 2026" },
      { k: "Format", v: "Keep a Changelog" },
      { k: "Versions in file", v: "4.0.0 to 4.4.5" },
    ],
  },
  {
    slug: "user-guide",
    title: "User guide",
    summary: "The whole interface, page by page, plus exports, backups and the FAQ.",
    topic: "start",
    file: "docs/USER_GUIDE.md",
    words: 2120,
    stale: "The source file still says v4.4.0 and names the 4.4.1 installer. The current release is v4.4.5.",
  },
  {
    slug: "troubleshooting",
    title: "Troubleshooting",
    summary: "Hosts file access, Windows Hello, browser domains, autostart, updates.",
    topic: "fix",
    file: "docs/TROUBLESHOOTING.md",
    words: 620,
  },
  {
    slug: "cli-reference",
    title: "Command line",
    summary: "Six flags: tray mode, headless service, and the elevated helper.",
    topic: "source",
    file: "docs/CLI_REFERENCE.md",
    words: 440,
  },
  {
    slug: "developer-guide",
    title: "Developer guide",
    summary: "Python, dependencies, the Aurora design system, page checklist, packaging.",
    topic: "build",
    file: "docs/DEVELOPER_GUIDE.md",
    words: 710,
  },
  {
    slug: "architecture",
    title: "Architecture",
    summary: "Tracking threads, the repository layer, the elevated helper, the schema.",
    topic: "source",
    file: "docs/ARCHITECTURE.md",
    words: 1960,
  },
  {
    slug: "performance",
    title: "Performance",
    summary: "Benchmarks for start-up, memory, idle CPU and tracker wakeups.",
    topic: "source",
    file: "docs/PERFORMANCE.md",
    words: 1520,
    stale: "Measured on v4.2. The figures on the home page are the ones this document reports.",
  },
  {
    slug: "attention-wellness",
    title: "Attention and wellness",
    summary: "Sub-path filters, fragmentation index, circadian warm-up, strict lockout.",
    topic: "use",
    file: "docs/ATTENTION_WELLNESS.md",
    words: 1760,
  },
  {
    slug: "releasing",
    title: "Releasing",
    summary: "Bump the version, build the installer, publish checksums.",
    topic: "build",
    file: "docs/RELEASING.md",
    words: 360,
    stale: "The bump example in this document uses 4.3.1. The last line of the file is the source of truth for the current version.",
  },
  {
    slug: "ux-guidelines",
    title: "Interface rules",
    summary: "Spacing, colour, motion and copy rules the desktop app follows.",
    topic: "build",
    file: "docs/UX_GUIDELINES.md",
    words: 430,
  },
  {
    slug: "qa-app-locker",
    title: "App Locker QA",
    summary: "The test matrix behind the biometric and PIN lock.",
    topic: "protect",
    file: "docs/QA_APP_LOCKER.md",
    words: 1120,
    stale: "This checklist still names the 4.3.2 installer. It describes behaviour, so the steps hold, but the build it was written against is older than the current release.",
  },
];
