import { Diagram } from "./figure"

/**
 * ROADMAP.md, drawn. The milestones are kept as the document states them and
 * marked with what actually shipped, because a roadmap read in 2026 should not
 * pretend 2027 is still ahead of it.
 */

const milestones = [
  {
    tag: "v4.1",
    title: "Aurora foundation",
    state: "shipped",
    items: ["SafeBrowse shield", "Windows Hello lock", "SQLite WAL engine", "Twelve pages"],
  },
  {
    tag: "v4.2",
    title: "Engine work",
    state: "shipped",
    items: ["Event-driven WinEvent hooks", "Lazy UI loading", "SQLite tuning", "0.5 wakeups per second"],
  },
  {
    tag: "v4.3 to v4.4",
    title: "Momentum",
    state: "shipped",
    items: ["Session recap", "Focus schedules", "Sub-path URL rules", "Liquid Glass pass"],
  },
  {
    tag: "Next",
    title: "Phone companion",
    state: "planned",
    items: ["Local LAN pairing", "Mobile companion", "One combined ring", "Focus sync"],
  },
  {
    tag: "Later",
    title: "Wellness context",
    state: "planned",
    items: ["Sub-path URL rules", "Flow state metrics", "Strict lockout", "On-device context"],
  },
]

const tone = {
  shipped: "border-accent/60 bg-accent/8",
  planned: "border-dashed border-line-strong bg-transparent",
} as const

export function RoadmapMilestones() {
  return (
    <Diagram
      id="diagram-roadmap"
      title="Milestones"
      source="ROADMAP.md"
      caption="The first three columns have shipped. The last two are the direction the roadmap describes, and nothing on this page promises a date for them."
    >
      <div className="min-w-[34rem]">
        <ol className="grid grid-cols-5 gap-2">
          {milestones.map((m) => (
            <li key={m.tag} className={`rounded-lg border p-2.5 ${tone[m.state as "shipped" | "planned"]}`}>
              <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">{m.tag}</p>
              <p className="mt-1 text-[0.8125rem] font-semibold leading-tight text-ink">{m.title}</p>
              <ul className="mt-2 space-y-1 border-t border-line pt-2">
                {m.items.map((item) => (
                  <li key={item} className="text-[0.6875rem] leading-snug text-muted">
                    {item}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
        <div className="mt-3 flex items-center gap-2 border-t border-line pt-2.5">
          <span className="h-2 w-6 rounded-full border border-accent/60 bg-accent/15" aria-hidden="true" />
          <p className="font-mono text-[0.625rem] text-muted">shipped</p>
          <span className="ml-3 h-2 w-6 rounded-full border border-dashed border-line-strong" aria-hidden="true" />
          <p className="font-mono text-[0.625rem] text-muted">described in the roadmap, not scheduled here</p>
        </div>
      </div>
    </Diagram>
  )
}
