"use client"

import Image from "next/image"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useState } from "react"
import { useTheme } from "@/components/system/browser-state"
import { site } from "@/data/site"

const links = [
  { href: "/#record", label: "Record" },
  { href: "/#controls", label: "Controls" },
  { href: "/#screens", label: "Screens" },
  { href: "/docs", label: "Docs" },
]

/** Below 640px the nav collapses into one row of text links, still 40px tall. */
const mobileLinks = [...links, { href: "/#install", label: "Install" }]

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
  const pathname = usePathname()
  const onDocs = pathname?.startsWith("/docs") ?? false
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-ground/85 backdrop-blur-md">
      <div className="shell flex h-14 items-center justify-between gap-4">
        <Link href="/" className="-ml-1 flex min-w-0 items-center gap-2.5 py-2">
          <Image
            src="/images/mark.png"
            alt=""
            width={128}
            height={128}
            className="h-7 w-auto shrink-0"
            priority
          />
          <span className="truncate text-[0.875rem] font-semibold tracking-tight sm:text-[0.9375rem]">
            Digital Wellbeing
          </span>
          <span className="micro hidden md:inline">v{site.version}</span>
        </Link>

        <nav aria-label="Sections" className="hidden items-center gap-6 text-[0.8125rem] font-medium md:flex">
          {links.map((l) => {
            const current = l.href === "/docs" && onDocs
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={current ? "page" : undefined}
                className={`px-1 py-2.5 transition-colors hover:text-ink ${current ? "text-ink" : "text-muted"}`}
              >
                <span className="roll">
                  <span>{l.label}</span>
                  <span aria-hidden="true">{l.label}</span>
                </span>
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <a
            href="/api/download"
            aria-label="Download for Windows"
            className="btn btn--primary h-9 min-h-0 px-4 py-0 text-[0.8125rem] max-sm:h-10 max-sm:w-10 max-sm:justify-center max-sm:px-0"
          >
            <span className="max-sm:hidden">Download</span>
            <svg className="btn__arrow" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" fill="none">
              <path d="M6 1v10M2 7l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="nav-small"
            aria-label={open ? "Close menu" : "Open menu"}
            className="-mr-2 inline-flex h-10 w-10 items-center justify-center rounded-full text-muted transition-colors hover:text-ink md:hidden"
          >
            <span aria-hidden="true" className="relative block h-3 w-4">
              <span
                className="absolute inset-x-0 top-0 h-px bg-current transition-transform duration-300 ease-[var(--ease-out)]"
                style={{ transform: open ? "translateY(6px) rotate(45deg)" : undefined }}
              />
              <span
                className="absolute inset-x-0 top-1.5 h-px bg-current transition-opacity duration-200"
                style={{ opacity: open ? 0 : 1 }}
              />
              <span
                className="absolute inset-x-0 top-3 h-px bg-current transition-transform duration-300 ease-[var(--ease-out)]"
                style={{ transform: open ? "translateY(-6px) rotate(-45deg)" : undefined }}
              />
            </span>
          </button>
        </div>
      </div>

      {/* Small screens: the same five destinations, in one ruled row. */}
      <div
        id="nav-small"
        hidden={!open}
        className="border-t border-line bg-panel md:hidden"
      >
        <nav aria-label="Sections" className="shell grid grid-cols-2 gap-x-4 py-2">
          {mobileLinks.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="flex min-h-11 items-center justify-between border-b border-line text-[0.875rem] text-muted last:border-b-0"
            >
              {l.label}
              <span aria-hidden="true" className="font-mono text-[0.6875rem]">
                →
              </span>
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}

/** The product's real app mark, used at footer scale. */
export function AppMark({ size = 20 }: { size?: number }) {
  return (
    <Image
      src="/images/mark.png"
      alt=""
      width={128}
      height={128}
      style={{ height: size, width: "auto" }}
      className="shrink-0"
    />
  )
}
