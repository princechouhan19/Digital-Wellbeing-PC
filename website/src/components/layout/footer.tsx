import Link from "next/link"
import { site, colophon, footerNote } from "@/data/site"
import { AppMark } from "@/components/layout/navbar"

export function Footer() {
  return (
    <footer className="border-t border-line bg-panel/40">
      <div className="shell grid gap-10 py-14 md:grid-cols-12 md:py-16">
        <div className="md:col-span-5">
          <div className="flex items-center gap-2.5">
            <AppMark size={22} />
            <span className="text-[0.9375rem] font-semibold tracking-tight">{site.name}</span>
          </div>
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
            A screen time tracker for Windows that also acts on what it records. Written, measured,
            and maintained by one developer.
          </p>
          <a
            href="/api/download"
            className="btn btn--ghost mt-6 text-[0.8125rem]"
          >
            <span>Download v{site.version}</span>
          </a>
        </div>

        <nav aria-label="Product" className="md:col-span-2">
          <p className="micro">Sections</p>
          <ul className="mt-2 space-y-0 text-sm text-muted">
            <li><Link className="link-inline tap" href="/#record">Record</Link></li>
            <li><Link className="link-inline tap" href="/#controls">Controls</Link></li>
            <li><Link className="link-inline tap" href="/#screens">Screens</Link></li>
            <li><Link className="link-inline tap" href="/#readout">Readout</Link></li>
            <li><Link className="link-inline tap" href="/#install">Install</Link></li>
            <li><Link className="link-inline tap" href="/docs">Docs</Link></li>
          </ul>
        </nav>

        <nav aria-label="Source and support" className="md:col-span-2">
          <p className="micro">Source</p>
          <ul className="mt-2 space-y-0 text-sm text-muted">
            <li><a className="link-inline tap" href={site.repository} rel="noreferrer" target="_blank">Repository</a></li>
            <li><a className="link-inline tap" href={site.releases} rel="noreferrer" target="_blank">Releases</a></li>
            <li><a className="link-inline tap" href={`${site.releases}/download/${site.checksums}`} rel="noreferrer" target="_blank">Checksums</a></li>
            <li><a className="link-inline tap" href={site.issues} rel="noreferrer" target="_blank">Report a bug</a></li>
          </ul>
        </nav>

        <div className="md:col-span-3">
          <p className="micro">This page</p>
          <ul className="mt-2 space-y-1 text-[0.8125rem] leading-relaxed text-muted">
            {colophon.map((c) => (
              <li key={c}>{c}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-line">
        <div className="shell flex flex-col gap-2 py-5 text-[0.75rem] text-muted sm:flex-row sm:items-center sm:justify-between">
          <p>{footerNote}</p>
          <p className="font-mono">
            <Link className="link-inline tap" href="/">
              digitalwellbeing.vercel.app
            </Link>
          </p>
        </div>
      </div>
    </footer>
  )
}
