"use client"

import { useTheme } from "@/components/system/browser-state"
import Link from "next/link"
import { site } from "@/data/site"

const links = [
  { href: "#record", label: "Record" },
  { href: "#controls", label: "Controls" },
  { href: "#screens", label: "Screens" },
  { href: "#install", label: "Install" },
]

function ThemeToggle() {
  const [theme, setTheme] = useTheme()

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label={`${theme === "dark" ? "Night" : "Day"}, switch appearance`}
      className="group inline-flex h-9 items-center gap-2 rounded-full border border-line px-3 text-[0.75rem] font-medium text-muted transition-colors hover:border-line-strong hover:text-ink max-sm:h-10 max-sm:px-3.5"
    >
      <span aria-hidden="true" className="relative block h-3 w-3">
        <span
          className="absolute inset-0 rounded-full border border-current transition-transform duration-500 ease-[var(--ease-out)] group-hover:rotate-90"
          style={{ background: theme === "dark" ? "currentColor" : "transparent" }}
        />
      </span>
      <span className="hidden tnum sm:inline">{theme === "dark" ? "Night" : "Day"}</span>
    </button>
  )
}

export function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ground/85 backdrop-blur-md">
      <div className="shell flex h-14 items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2.5 py-2">
          <MeterMark />
          <span className="text-[0.9375rem] font-semibold tracking-tight">Digital Wellbeing</span>
          <span className="micro hidden md:inline">v{site.version}</span>
        </Link>

        <nav aria-label="Sections" className="hidden items-center gap-6 text-[0.8125rem] font-medium md:flex">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="px-1 text-muted transition-colors hover:text-ink"
            >
              <span className="roll">
                <span>{l.label}</span>
                <span aria-hidden="true">{l.label}</span>
              </span>
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <a
            href="/api/download"
            className="btn btn--primary h-9 min-h-0 px-4 py-0 text-[0.8125rem] max-sm:h-10"
          >
            <span>Download</span>
            <svg className="btn__arrow" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" fill="none">
              <path d="M6 1v10M2 7l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
        </div>
      </div>
    </header>
  )
}

/** The mark is the concept in miniature: three quota bars, one spent. */
export function MeterMark({ dark = false }: { dark?: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" className="shrink-0">
      <rect x="1" y="3" width="18" height="3.2" rx="1.6" fill="currentColor" opacity={dark ? 0.9 : 0.85} />
      <rect x="1" y="8.4" width="11" height="3.2" rx="1.6" fill="currentColor" opacity={dark ? 0.55 : 0.5} />
      <rect x="1" y="13.8" width="18" height="3.2" rx="1.6" fill="var(--accent)" />
    </svg>
  )
}
