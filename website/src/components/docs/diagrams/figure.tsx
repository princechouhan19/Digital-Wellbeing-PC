/**
 * Shared furniture for diagrams.
 *
 * Every diagram is drawn in the site's own tokens (ink, panel, line, accent,
 * alert), so it inherits the light and dark theme instead of shipping a
 * picture of one. Text stays real text: selectable, searchable, readable by a
 * screen reader, and at native resolution on any display.
 */

/** A caption that says what the figure shows and where it came from. */
export function Diagram({
  id,
  title,
  caption,
  source,
  children,
  wide = false,
}: {
  id: string
  title: string
  caption: string
  source?: string
  children: React.ReactNode
  /** Full-bleed in the article column for diagrams that need the width. */
  wide?: boolean
}) {
  return (
    <figure
      id={id}
      className={`my-8 scroll-mt-28 ${wide ? "" : ""}`}
      aria-labelledby={`${id}-caption`}
    >
      <div className="overflow-hidden rounded-xl border border-line bg-panel">
        <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line px-4 py-2.5">
          <p className="micro">{title}</p>
          {source ? <p className="font-mono text-[0.625rem] text-muted">{source}</p> : null}
        </div>
        {/* Wide diagrams scroll on a phone, so the box takes focus and says so. */}
        <div
          className="overflow-x-auto p-4 md:p-5"
          tabIndex={0}
          role="region"
          aria-label={`${title}, scrollable diagram`}
        >
          {children}
        </div>
      </div>
      <figcaption id={`${id}-caption`} className="mt-2 text-[0.75rem] leading-relaxed text-muted">
        {caption}
      </figcaption>
    </figure>
  )
}

/** Layer heading inside a diagram: a rule, a name, and an optional count. */
export function LayerLabel({ children, aside }: { children: React.ReactNode; aside?: string }) {
  return (
    <div className="mb-2 flex items-baseline justify-between gap-3 border-b border-line pb-1.5">
      <p className="font-mono text-[0.625rem] uppercase tracking-[0.14em] text-muted">{children}</p>
      {aside ? <p className="font-mono text-[0.625rem] text-muted">{aside}</p> : null}
    </div>
  )
}

/** One box in a flow diagram. Accent means "this is where the acting happens". */
export function Node({
  name,
  detail,
  tone = "plain",
}: {
  name: string
  detail?: string
  tone?: "plain" | "accent" | "alert"
}) {
  const ring =
    tone === "accent"
      ? "border-accent/60 bg-accent/8"
      : tone === "alert"
        ? "border-alert/50 bg-alert/6"
        : "border-line bg-panel-2/60"
  return (
    <div className={`rounded-lg border px-3 py-2 ${ring}`}>
      <p className="break-words font-mono text-[0.75rem] leading-tight text-ink">{name}</p>
      {detail ? (
        <p className="mt-1 text-[0.6875rem] leading-snug text-muted">{detail}</p>
      ) : null}
    </div>
  )
}

/** Downward connector with a label, used between layers. */
export function Drop({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-2 pl-4" aria-hidden="true">
      <svg width="10" height="26" viewBox="0 0 10 26" className="shrink-0 text-line-strong">
        <path d="M5 0v22" stroke="currentColor" strokeWidth="1" />
        <path d="M1.5 18.5 5 23l3.5-4.5" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
      {label ? (
        <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">{label}</p>
      ) : null}
    </div>
  )
}
