import Image from "next/image"
import { site, hero, register, hostsBlock, readout, install } from "@/data/site"
import { LedgerPanel } from "@/components/home/ledger-panel"
import { Controls } from "@/components/home/controls"
import { Screens } from "@/components/home/screens"
import { Motion } from "@/components/system/motion"
import { SectionHead } from "@/components/home/section-head"
import { ButtonFill } from "@/components/system/button-fill"
import { CountUp } from "@/components/home/count-up"

export default function Home() {
  return (
    <>
      <Motion />
      <ButtonFill />

      {/* Hero. The page opens on the machine answering "where did today go". */}
      <section className="relative overflow-hidden border-b border-line">
        <div aria-hidden="true" className="grid-field absolute inset-0 -z-10" />
        <div className="shell grid items-start gap-12 pt-14 pb-16 lg:grid-cols-12 lg:gap-10 lg:pt-20 lg:pb-24">
          <div className="lg:col-span-7">
            <p className="micro flex items-center gap-2.5">
              <span className="dot" aria-hidden="true" />
              {hero.kicker}
            </p>

            <h1 className="mt-6 text-[clamp(2.25rem,7.4vw,5.5rem)] leading-[0.94] tracking-[-0.04em]">
              {hero.title[0]}
              <br />
              <span className="text-muted">{hero.title[1]}</span>
            </h1>

            <p className="mt-7 max-w-xl text-[1.0625rem] leading-relaxed text-ink/85 md:text-[1.125rem]">
              {hero.standfirst}
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
              <a href="/api/download" className="btn btn--primary" data-fill>
                <DownloadGlyph />
                <span>{hero.primaryCta}</span>
              </a>
              <a href={site.repository} rel="noreferrer" className="btn btn--ghost" data-fill>
                <GithubGlyph />
                <span>{hero.secondaryCta}</span>
              </a>
            </div>

            <dl className="mt-10 grid max-w-lg grid-cols-2 gap-x-6 gap-y-4 border-t border-line pt-5 text-[0.8125rem] sm:grid-cols-4">
              <div>
                <dt className="micro">Installer</dt>
                <dd className="mt-1 font-mono text-ink">{site.installerSize}</dd>
              </div>
              <div>
                <dt className="micro">Runtime</dt>
                <dd className="mt-1 font-mono text-ink">bundled</dd>
              </div>
              <div>
                <dt className="micro">Network</dt>
                <dd className="mt-1 font-mono text-ink">off by default</dd>
              </div>
              <div>
                <dt className="micro">Licence</dt>
                <dd className="mt-1 font-mono text-ink">{site.license}</dd>
              </div>
            </dl>
            <p className="mt-4 text-[0.75rem] text-muted">{hero.installNote}</p>
          </div>

          <div className="lg:col-span-5">
            <LedgerPanel />
            <p className="mt-3 font-mono text-[0.6875rem] leading-relaxed text-muted">
              A scripted sample day. The tracker writes this locally, one row per focus change.
            </p>
          </div>
        </div>
      </section>

      {/* The argument, set as a pull quote instead of a card grid. */}
      <section className="border-b border-line bg-panel/50">
        <div className="shell grid gap-8 py-16 md:grid-cols-12 md:py-24" data-stagger>
          <p className="reveal micro md:col-span-2">The problem</p>
          <div className="md:col-span-10" data-stagger>
            <blockquote className="reveal text-[clamp(1.375rem,3.4vw,2.25rem)] font-medium leading-[1.22] tracking-[-0.02em] text-balance">
              <p>
                A browser extension can be disabled in two clicks. A productivity score can be
                ignored in one glance.{" "}
                <span className="text-muted">Willpower is the wrong mechanism.</span> This one
                intervenes at the process table, the hosts file, and the timer that closes the
                window.
              </p>
            </blockquote>
            <div className="reveal mt-9 grid gap-6 border-t border-line pt-6 sm:grid-cols-3">
              {[
                ["Process level", "An app that is not running cannot be clicked back to."],
                ["Local only", "One SQLite file, in your own app data folder."],
                ["Reversible", "Every block and suspension is undone on exit."],
              ].map(([t, d]) => (
                <div key={t}>
                  <p className="text-[0.8125rem] font-semibold text-ink">{t}</p>
                  <p className="mt-1 text-[0.8125rem] leading-relaxed text-muted">{d}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Register. What is written, and what is never written. */}
      <section id="record" className="border-b border-line">
        <div className="shell py-16 md:py-24" data-stagger>
          <SectionHead
            index="01"
            label="What is recorded"
            title="A register, not a transcript."
            intro="Four things are written to the database, and all of them are about which window was in front and for how long. Nothing you type, read, or look at is stored."
          />

          <div className="mt-12 grid gap-8 md:grid-cols-12" data-stagger>
            <div className="md:col-span-5" data-stagger>
              <div className="reveal rounded-lg border border-line bg-panel px-4 py-3">
                <p className="micro">On disk</p>
                <p className="mt-1.5 break-all font-mono text-[0.75rem] text-ink">
                  {register.storage}
                </p>
                <p className="mt-2 text-[0.75rem] leading-relaxed text-muted">{register.exportNote}</p>
              </div>
              <div className="reveal mt-8 border-t border-line pt-4">
                <p className="micro">The two network calls that exist</p>
                <dl className="mt-3">
                  {register.network.map((n) => (
                    <div key={n.call} className="border-b border-line py-3 last:border-b-0">
                      <dt className="text-[0.8125rem] font-semibold">{n.call}</dt>
                      <dd className="mt-1 text-[0.75rem] leading-relaxed text-muted">{n.when}</dd>
                      <dd className="mt-1 font-mono text-[0.6875rem] leading-relaxed text-muted">
                        sends: {n.sent}
                      </dd>
                    </div>
                  ))}
                </dl>
                <p className="mt-3 text-[0.75rem] leading-relaxed text-muted">
                  Everything else happens on your disk. The privacy policy in the repository lists
                  each table and field.
                </p>
                <p className="mt-4 text-[0.75rem] leading-relaxed text-muted">
                  Tracking starts with Windows and stays in the tray. The uninstaller closes the app
                  and can remove the database and profile settings with it, or leave them for a
                  reinstall.
                </p>
                <a
                  href={`${site.repository}/blob/main/PRIVACY.md`}
                  rel="noreferrer"
                  className="link-inline tap mt-2 text-[0.8125rem] text-muted"
                >
                  Read the privacy policy
                </a>
              </div>
            </div>

            <div className="md:col-span-7" data-stagger>
              <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2" data-stagger>
                <div className="reveal">
                  <p className="flex items-center gap-2 border-b border-line pb-2 text-[0.8125rem] font-semibold">
                    <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden="true" />
                    Written
                  </p>
                  <dl data-stagger>
                    {register.written.map((r) => (
                      <div key={r.field} className="reveal rule-draw border-b border-line py-3 last:border-b-0">
                        <dt className="font-mono text-[0.6875rem] uppercase tracking-[0.1em] text-ink">
                          {r.field}
                        </dt>
                        <dd className="mt-1 text-[0.8125rem] leading-relaxed text-muted">{r.text}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className="reveal">
                  <p className="flex items-center gap-2 border-b border-line pb-2 text-[0.8125rem] font-semibold">
                    <span className="h-1.5 w-1.5 rounded-full bg-alert" aria-hidden="true" />
                    Never
                  </p>
                  <ul data-stagger>
                    {register.never.map((n) => (
                      <li
                        key={n}
                        className="reveal flex items-start gap-2 border-b border-line py-2.5 text-[0.8125rem] leading-relaxed text-muted last:border-b-0"
                      >
                        <span aria-hidden="true" className="mt-[0.65em] block h-px w-2 shrink-0 bg-alert/70" />
                        {n}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="reveal rule-draw rule-draw--alert">
                <figure className="mt-8 overflow-hidden rounded-lg border border-line bg-[#0b0f14] text-[#e6edf3]">
                  <figcaption className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-2 font-mono text-[0.625rem] uppercase tracking-[0.12em] text-white/60">
                    <span className="truncate">drivers\etc\hosts</span>
                    <span className="shrink-0 text-[#2ad59b]">focus block</span>
                  </figcaption>
                  <pre className="overflow-x-auto px-4 py-4 font-mono text-[0.6875rem] leading-[1.7] md:text-[0.75rem]">
                    <code>{hostsBlock}</code>
                  </pre>
                </figure>
                <p className="mt-3 text-[0.75rem] leading-relaxed text-muted">
                  Focus Mode writes a delimited section into the hosts file, flushes the DNS cache, and
                  removes the section when the session ends. The rest of the file is left alone.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Controls. An index of verbs, each answered with real app evidence. */}
      <section id="controls" className="border-b border-line bg-panel/50">
        <div className="shell py-16 md:py-24" data-stagger>
          <SectionHead
            index="02"
            label="Four controls"
            title="Recording is the easy half. These are the ones that act."
            intro="Choose a control to see the screen it lives on. All four run from the same tracker, so none of them can be talked past."
          />
          <div className="reveal mt-12">
            <Controls />
          </div>
        </div>
      </section>

      {/* Screens. The register of what the app actually looks like. */}
      <section id="screens" className="border-b border-line">
        <div className="shell py-16 md:py-24" data-stagger>
          <SectionHead
            index="03"
            label="Screens"
            title="Eight pages, one file."
            intro="Each page opens on a different question. The dashboard answers what today cost, usage answers when, insights answers whether it is getting worse."
          />

          <div className="mt-12 grid gap-8 md:grid-cols-12" data-stagger>
            <div className="reveal md:col-span-4">
              <p className="text-[0.8125rem] leading-relaxed text-muted">
                Everything below is the real interface, captured in dark mode at 1500 by 1000 pixels.
                Select a page to inspect it.
              </p>
              <p className="mt-6 border-t border-line pt-4 text-[0.8125rem] leading-relaxed text-muted">
                The dark theme is the app&apos;s default and the one shown here. A light theme ships with
                it, with the same charts and contrast.
              </p>
            </div>
            <div className="reveal md:col-span-8">
              <Screens />
            </div>
          </div>
        </div>
      </section>

      {/* Readout. Measured numbers, attributed to the owner's own benchmark. */}
      <section id="readout" className="border-b border-line bg-panel/50">
        <div className="shell py-16 md:py-24" data-stagger>
          <SectionHead
            index="04"
            label="Readout"
            title="What it costs to run."
            intro="A permanent background process earns its place only if it stays invisible. These are the numbers the project measures itself against."
          />
          <dl className="reveal mt-10 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
            {readout.map((r) => (
              <div key={r.label} className="bg-ground p-5">
                <dt className="text-[0.8125rem] font-medium">{r.label}</dt>
                <dd className="mt-2 flex items-baseline gap-1 font-mono text-[2rem] leading-none tracking-tight text-ink tnum">
                  <CountUp value={r.value} />
                  <span className="text-[0.875rem] text-muted">{r.unit}</span>
                </dd>
                <dd className="mt-1 text-[0.75rem] leading-relaxed text-muted">{r.note}</dd>
              </div>
            ))}
          </dl>
          <p className="reveal mt-4 max-w-2xl text-[0.75rem] leading-relaxed text-muted">
            Figures come from the project&apos;s own benchmark document, measured on Windows 11 with
            Python 3.12 and Qt 6.12. They are medians, not promises, and they will move with your
            hardware.
          </p>
        </div>
      </section>

      {/* Install. The real steps, including the uncomfortable one. */}
      <section id="install" className="border-b border-line">
        <div className="shell py-16 md:py-24" data-stagger>
          <SectionHead
            index="05"
            label="Install"
            title="Three steps, one of them awkward."
            intro="No account, no email, no subscription. The installer is the only thing between you and a running tracker."
          />
          <div className="mt-12 grid gap-10 md:grid-cols-12" data-stagger>
            <div className="md:col-span-7" data-stagger>
              <ol className="reveal">
                {install.steps.map((s) => (
                  <li key={s.k} className="ledger grid-cols-[2.5rem_1fr]">
                    <span className="ledger__n pt-0.5">{s.k}</span>
                    <div>
                      <p className="text-[0.9375rem] font-semibold">{s.t}</p>
                      <p className="mt-1 max-w-lg text-[0.8125rem] leading-relaxed text-muted">{s.d}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <div className="reveal mt-8 flex flex-col gap-3 sm:flex-row">
                <a href="/api/download" className="btn btn--primary" data-fill>
                  <DownloadGlyph />
                  <span>Download {site.version}</span>
                </a>
                <a
                  href={`${site.releases}/download/${site.checksums}`}
                  rel="noreferrer"
                  className="btn btn--ghost font-mono text-[0.8125rem]"
                  data-fill
                >
                  <span>{site.checksums}</span>
                </a>
              </div>
            </div>

            <div className="reveal md:col-span-5">
              <div className="rounded-xl border border-line">
                <div className="flex items-center gap-2.5 border-b border-line px-4 py-3">
                  <Image src="/logo.png" alt="" width={20} height={20} className="h-5 w-5" />
                  <p className="text-[0.8125rem] font-semibold">System requirements</p>
                </div>
                <dl className="divide-y divide-line">
                  {install.requirements.map(([k, v]) => (
                    <div key={k} className="flex items-baseline justify-between gap-4 px-4 py-2.5">
                      <dt className="text-[0.75rem] text-muted">{k}</dt>
                      <dd className="text-right font-mono text-[0.75rem] text-ink">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="border-t border-line px-4 py-3">
                  <p className="text-[0.75rem] leading-relaxed text-muted">
                    Verify a download by comparing its SHA-256 hash with the published file. The
                    release workflow generates it for every build.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Closing statement: the last page of the register. */}
      <section className="relative overflow-hidden border-b border-line bg-panel/50">
        <div aria-hidden="true" className="grid-field absolute inset-0 -z-10 opacity-60" />
        <div className="shell py-20 md:py-28" data-stagger>
          <p className="reveal micro">Ready when you are</p>
          <h2 className="reveal mt-6 max-w-[18ch] text-[clamp(2.25rem,7vw,5rem)] leading-[0.95] tracking-[-0.04em]">
            Install it once. Then let the machine hold the line.
          </h2>
          <div className="reveal mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="/api/download" className="btn btn--primary" data-fill>
              <DownloadGlyph />
              <span>Download for Windows</span>
            </a>
            <a href={site.repository} rel="noreferrer" className="btn btn--ghost" data-fill>
              <GithubGlyph />
              <span>Star on GitHub</span>
            </a>
          </div>
          <dl className="reveal mt-14 grid gap-6 border-t border-line pt-6 text-[0.75rem] sm:grid-cols-3">
            <div>
              <dt className="micro">Version</dt>
              <dd className="mt-1 font-mono text-ink">
                {site.version} · {site.releaseDate}
              </dd>
            </div>
            <div>
              <dt className="micro">Licence</dt>
              <dd className="mt-1 font-mono text-ink">{site.license}, source included</dd>
            </div>
            <div>
              <dt className="micro">Runs on</dt>
              <dd className="mt-1 font-mono text-ink">{hero.kicker}</dd>
            </div>
          </dl>
        </div>
      </section>
    </>
  )
}

function DownloadGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden="true" fill="none">
      <path
        d="M7.5 1v8M4 6l3.5 3.5L11 6M2 12.5h11"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function GithubGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor">
      <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.93-.89-1.18-.89-1.18-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.71 1.22 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.94.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
    </svg>
  )
}
