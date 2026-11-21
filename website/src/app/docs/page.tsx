import type { Metadata } from "next"
import Link from "next/link"
import { docPages, docTopics, docsIndex, site } from "@/data/site"

export const metadata: Metadata = {
  title: "Documentation",
  description:
    "The user guide, troubleshooting, command line, architecture, performance notes, privacy policy and changelog for Digital Wellbeing for Windows.",
  alternates: { canonical: "/docs" },
}

export default function DocsIndex() {
  const byTopic = docTopics.map((topic) => ({
    ...topic,
    pages: docPages.filter((page) => page.topic === topic.id),
  }))

  return (
    <div className="border-b border-line">
      <div className="shell pt-12 pb-16 md:pt-16 md:pb-24">
        <nav aria-label="Breadcrumb" className="micro flex items-center">
          <Link href="/" className="tap hover:text-ink">
            Home
          </Link>
          <span aria-hidden="true"> / </span>
          <span className="tap text-ink">Docs</span>
        </nav>

        <div className="mt-8 grid gap-10 md:grid-cols-12 md:gap-8">
          <div className="md:col-span-8">
            <h1 className="max-w-[22ch] text-[clamp(2.25rem,6.4vw,4.25rem)] leading-[0.96] tracking-[-0.04em]">
              {docsIndex.title}
            </h1>
            <p className="mt-6 max-w-xl text-[1.0625rem] leading-relaxed text-muted">
              {docsIndex.lead}
            </p>
            <p className="mt-4 max-w-xl font-mono text-[0.75rem] leading-relaxed text-muted">
              {docsIndex.note}
            </p>
          </div>

          <div className="md:col-span-4 md:pt-2">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-4 border-t border-line pt-4 text-[0.8125rem]">
              <div>
                <dt className="micro">Documents</dt>
                <dd className="mt-1 font-mono text-ink">{docPages.length}</dd>
              </div>
              <div>
                <dt className="micro">Words</dt>
                <dd className="mt-1 font-mono text-ink">
                  {Math.round(docPages.reduce((n, p) => n + p.words, 0) / 100) / 10}k
                </dd>
              </div>
              <div>
                <dt className="micro">Version</dt>
                <dd className="mt-1 font-mono text-ink">{site.version}</dd>
              </div>
              <div>
                <dt className="micro">Licence</dt>
                <dd className="mt-1 font-mono text-ink">{site.license}</dd>
              </div>
            </dl>
          </div>
        </div>

        {/* Straight to the task, not to a chapter. */}
        <section aria-labelledby="quick" className="mt-14 border-t border-line pt-6">
          <h2 id="quick" className="micro">
            Jump straight in
          </h2>
          <ul className="mt-4 grid gap-x-8 gap-y-0 sm:grid-cols-2 lg:grid-cols-3">
            {docsIndex.quick.map((item) => (
              <li key={item.t}>
                <Link href={item.href} className="row-link group">
                  <span className="flex items-baseline justify-between gap-3">
                    <span className="text-[0.9375rem] font-semibold">{item.t}</span>
                    <span
                      aria-hidden="true"
                      className="font-mono text-[0.75rem] text-muted transition-colors group-hover:text-accent"
                    >
                      →
                    </span>
                  </span>
                  <span className="text-[0.8125rem] leading-relaxed text-muted">{item.d}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* The library, grouped by what the reader is trying to do. */}
        <div className="mt-16 grid gap-12 md:grid-cols-12 md:gap-8">
          <div className="md:col-span-8">
            {byTopic
              .filter((t) => t.pages.length > 0)
              .map((topic) => (
                <section key={topic.id} className="mb-12 last:mb-0">
                  <div className="flex items-baseline justify-between gap-4 border-b border-line-strong pb-2">
                    <h2 className="text-[1.0625rem] font-semibold">{topic.label}</h2>
                    <p className="text-[0.75rem] text-muted">{topic.note}</p>
                  </div>
                  <ul>
                    {topic.pages.map((page) => (
                      <li key={page.slug}>
                        <Link href={`/docs/${page.slug}`} className="row-link group">
                          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                            <span className="text-[1rem] font-semibold group-hover:text-accent">
                              {page.title}
                            </span>
                            <span className="font-mono text-[0.6875rem] text-muted">
                              {page.words.toLocaleString("en-US")} words · {page.file}
                            </span>
                          </div>
                          <p className="max-w-2xl text-[0.875rem] leading-relaxed text-muted">
                            {page.summary}
                          </p>
                          {page.stale ? (
                            <p className="max-w-2xl font-mono text-[0.6875rem] leading-relaxed text-alert">
                              {page.stale}
                            </p>
                          ) : null}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </section>
              ))}
          </div>

          <aside className="md:col-span-4">
            <div className="sticky top-24 space-y-8">
              <div className="rounded-xl border border-line bg-panel p-5">
                <p className="micro">Where these files live</p>
                <p className="mt-3 text-[0.875rem] leading-relaxed text-muted">
                  Every page is a Markdown file in the repository, copied into this site by{" "}
                  <span className="font-mono text-[0.8125rem] text-ink">tools/sync-docs.mjs</span>{" "}
                  at build time. Edit the Markdown, run the script, and the page changes.
                </p>
                <a
                  href={`${site.repository}/tree/main/docs`}
                  rel="noreferrer"
                  target="_blank"
                  className="btn btn--ghost mt-4 text-[0.8125rem]"
                  data-fill
                >
                  <span>Browse docs on GitHub</span>
                </a>
              </div>

              <div>
                <p className="micro">Canonical version</p>
                <p className="mt-3 text-[0.875rem] leading-relaxed text-muted">
                  This documentation matches v{site.version}. Where a file names an older build,
                  the page says so above the title instead of quietly showing the old number.
                </p>
              </div>

              <div className="border-t border-line pt-5">
                <p className="micro">Found something wrong</p>
                <p className="mt-3 text-[0.875rem] leading-relaxed text-muted">
                  Documentation bugs are real bugs. Open an issue with the file name and the
                  sentence that is wrong.
                </p>
                <a
                  href={site.issues}
                  rel="noreferrer"
                  target="_blank"
                  className="link-inline tap mt-2 inline-block text-[0.8125rem] text-ink"
                >
                  {site.issues.replace("https://", "")}
                </a>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
