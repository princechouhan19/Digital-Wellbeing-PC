import { Diagram } from "./figure"

/**
 * docs/ATTENTION_WELLNESS.md, section 5. The document draws this page in box
 * characters; this is the same grid, drawn, because the point of the section
 * is proportions.
 */
export function FocusPageLayout() {
  return (
    <Diagram
      id="diagram-focus-page"
      title="Focus page layout"
      source="docs/ATTENTION_WELLNESS.md, section 5"
      caption="The redesign removed the card inside a card inside a card. Mode selection is a single row, the cockpit is two columns, and protection has its own footer instead of another nested panel."
    >
      <div className="min-w-[30rem] overflow-hidden rounded-lg border border-line">
        <div className="flex flex-wrap items-center gap-1.5 border-b border-line bg-panel-2/70 px-3 py-2">
          <p className="mr-2 font-mono text-[0.6875rem] text-ink">Focus</p>
          {["Deep", "Work", "Study", "Media", "Custom"].map((mode, i) => (
            <span
              key={mode}
              className={`rounded-full border px-2 py-0.5 font-mono text-[0.625rem] ${
                i === 0 ? "border-accent/60 bg-accent/12 text-ink" : "border-line text-muted"
              }`}
            >
              {mode}
            </span>
          ))}
        </div>

        <div className="grid gap-px bg-line sm:grid-cols-[1fr_1.25fr]">
          <div className="bg-panel px-3 py-3">
            <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">Session</p>
            <div className="mt-2 flex items-center gap-3">
              <div
                aria-hidden="true"
                className="relative h-12 w-12 shrink-0 rounded-full"
                style={{
                  background: "conic-gradient(var(--accent) 0 62%, color-mix(in oklab, var(--ink) 12%, transparent) 62% 100%)",
                }}
              >
                <span className="absolute inset-1.5 rounded-full bg-panel" />
              </div>
              <div>
                <p className="font-mono text-[0.75rem] text-ink">25:00</p>
                <p className="text-[0.625rem] text-muted">circular timer, presets plus custom</p>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <span className="rounded-full bg-ink px-3 py-1 text-[0.625rem] font-semibold text-ground">
                Start focus
              </span>
              <span className="font-mono text-[0.625rem] text-muted">25 · 50 · custom</span>
            </div>
          </div>

          <div className="bg-panel px-3 py-3">
            <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">
              Guardrails
            </p>
            <div className="mt-1.5 flex gap-1.5">
              {["Apps", "Websites", "Rules"].map((tab, i) => (
                <span
                  key={tab}
                  className={`rounded border px-1.5 py-0.5 font-mono text-[0.625rem] ${
                    i === 0 ? "border-line-strong text-ink" : "border-transparent text-muted"
                  }`}
                >
                  {tab}
                </span>
              ))}
            </div>
            <ul className="mt-2 space-y-1 border-t border-line pt-2 text-[0.6875rem] text-muted">
              <li>one curated list per tab</li>
              <li>sub-path rules, most specific first</li>
              <li>extension bridge status</li>
            </ul>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-panel-2/70 px-3 py-1.5">
          <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">
            Session protection
          </p>
          <div className="flex gap-3 font-mono text-[0.625rem] text-muted">
            <span>Strict</span>
            <span className="rounded-full border border-line px-1.5">off</span>
            <span>Lockout</span>
            <span className="rounded-full border border-line px-1.5">off</span>
          </div>
        </div>
      </div>
    </Diagram>
  )
}
