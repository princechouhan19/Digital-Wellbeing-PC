import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { docPages, docTopics, site } from "@/data/site"
import { sourceDocs } from "@/content/docs.generated"
import { renderMarkdown, outline } from "@/components/docs/markdown"
import { DocsHeader } from "@/components/docs/docs-header"

type Params = { params: Promise<{ slug: string }> }

const pageFor = (slug: string) => docPages.find((p) => p.slug === slug)
const markdownFor = (slug: string) => sourceDocs.find((d) => d.slug === slug)?.markdown ?? ""

export function generateStaticParams() {
  return docPages.map((page) => ({ slug: page.slug }))
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params
  const page = pageFor(slug)
  if (!page) return {}
  return {
    title: page.title,
    description: page.summary,
    alternates: { canonical: `/docs/${page.slug}` },
    openGraph: { title: `${page.title} · Digital Wellbeing`, description: page.summary },
  }
}

export default async function DocPage({ params }: Params) {
  const { slug } = await params
  const page = pageFor(slug)
  const source = markdownFor(slug)
  if (!page || !source) notFound()

  const { nodes } = renderMarkdown(source, {
    keepVersions: page.slug === "changelog",
    file: page.file,
  })
  const rail = outline(source)
  const index = docPages.findIndex((p) => p.slug === slug)
  const next = docPages[index + 1]
  const topic = docTopics.find((t) => t.id === page.topic)

  return (
    <div className="border-b border-line">
      <div className="shell pt-10 pb-16 md:pt-12 md:pb-24">
        <nav aria-label="Breadcrumb" className="micro flex items-center">
          <Link href="/" className="tap hover:text-ink">
            Home
          </Link>
          <span aria-hidden="true"> / </span>
          <Link href="/docs" className="tap hover:text-ink">
            Docs
          </Link>
          <span aria-hidden="true"> / </span>
          <span className="tap text-ink">{page.title}</span>
        </nav>

        <div className="mt-8 grid gap-10 md:grid-cols-12 md:gap-8">
          <aside className="order-2 min-w-0 md:order-1 md:col-span-3">
            <div className="md:sticky md:top-24">
              <p className="micro">{topic?.label ?? "Document"}</p>
              {/* On a phone the rail is far from the thumb, so it folds away. */}
              <details className="mt-2 md:hidden" open={false}>
                <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-[0.8125rem] font-medium text-ink">
                  On this page
                  <span className="font-mono text-[0.6875rem] text-muted">{rail.length}</span>
                </summary>
                <ul className="doc-rail mt-1 border-t border-line pt-2">
                  {rail.map((h) => (
                    <li key={h.id} className={h.level === 3 ? "pl-2" : undefined}>
                      <a href={`#${h.id}`}>{h.text}</a>
                    </li>
                  ))}
                </ul>
              </details>
              <ul className="doc-rail mt-1 hidden md:block">
                {rail.map((h) => (
                  <li key={h.id} className={h.level === 3 ? "pl-2" : undefined}>
                    <a href={`#${h.id}`}>{h.text}</a>
                  </li>
                ))}
              </ul>
              <p className="mt-6 border-t border-line pt-4 font-mono text-[0.6875rem] leading-relaxed text-muted">
                Source: {page.file}
                <br />
                {page.words.toLocaleString("en-US")} words
              </p>
            </div>
          </aside>

          <article className="order-1 min-w-0 md:order-2 md:col-span-9">
            <DocsHeader
              title={page.title}
              summary={page.summary}
              file={page.file}
              words={page.words}
              stale={page.stale}
            />

            <div className="doc mt-10 min-w-0">{nodes}</div>

            <div className="mt-14 flex flex-col gap-4 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
              <a
                href={`${site.repository}/blob/main/${page.file}`}
                rel="noreferrer"
                target="_blank"
                className="link-inline tap self-start text-[0.875rem]"
              >
                Edit {page.file} on GitHub
              </a>
              {next ? (
                <Link href={`/docs/${next.slug}`} className="group self-start text-right">
                  <span className="micro block">Next</span>
                  <span className="mt-1 inline-flex items-baseline gap-2 text-[0.9375rem] font-semibold group-hover:text-accent">
                    {next.title}
                    <span aria-hidden="true">→</span>
                  </span>
                </Link>
              ) : (
                <Link href="/docs" className="group self-start text-right">
                  <span className="micro block">Back to</span>
                  <span className="mt-1 inline-flex items-baseline gap-2 text-[0.9375rem] font-semibold group-hover:text-accent">
                    All documents
                    <span aria-hidden="true">→</span>
                  </span>
                </Link>
              )}
            </div>
          </article>
        </div>
      </div>
    </div>
  )
}
