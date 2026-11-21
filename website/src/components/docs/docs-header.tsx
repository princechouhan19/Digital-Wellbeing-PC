import { site } from "@/data/site"

/**
 * The document's masthead: title, one-line summary, and the provenance line a
 * reader needs to judge a page. Where the source file is older than the
 * release, that fact is stated before the title, not buried in a footnote.
 */
export function DocsHeader({
  title,
  summary,
  file,
  words,
  stale,
}: {
  title: string
  summary: string
  file: string
  words: number
  stale?: string
}) {
  return (
    <header>
      {stale ? (
        <p className="mb-5 flex max-w-2xl gap-2.5 rounded-lg border border-line bg-panel px-3.5 py-2.5 text-[0.8125rem] leading-relaxed text-ink">
          <span aria-hidden="true" className="mt-0.5 shrink-0 font-mono text-[0.6875rem] text-alert">
            note
          </span>
          <span>{stale}</span>
        </p>
      ) : null}

      <h1 className="text-[clamp(1.875rem,4.6vw,3rem)] leading-[1.02] tracking-[-0.035em]">
        {title}
      </h1>
      <p className="mt-4 max-w-2xl text-[1rem] leading-relaxed text-muted">{summary}</p>

      <dl className="mt-7 flex flex-wrap items-baseline gap-x-6 gap-y-2 border-t border-line pt-4 text-[0.75rem]">
        <div className="flex items-baseline gap-2">
          <dt className="micro">File</dt>
          <dd className="font-mono text-ink">{file}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="micro">Words</dt>
          <dd className="font-mono text-ink">{words.toLocaleString("en-US")}</dd>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="micro">Release</dt>
          <dd className="font-mono text-ink">{site.version}</dd>
        </div>
      </dl>
    </header>
  )
}
