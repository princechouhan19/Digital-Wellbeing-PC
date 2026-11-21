import { Diagram } from "./figure"

/**
 * docs/ARCHITECTURE.md, section 3. Three threads and one process boundary.
 * Drawn left to right because the arrows are the argument: events flow in,
 * writes flow out, and the GUI thread never does either.
 */

const columns = [
  {
    title: "Event source",
    aside: "Win32",
    tone: "plain",
    items: [
      ["SetWinEventHook", "foreground and title changes"],
      ["GetLastInputInfo", "idle seconds, on demand"],
      ["5 s safety poll", "catches missed events"],
    ],
  },
  {
    title: "Foreground watcher",
    aside: "thread",
    tone: "accent",
    items: [
      ["Coalescing", "many events, one wakeup"],
      ["Session staging", "held in memory"],
    ],
  },
  {
    title: "Tracker daemon",
    aside: "thread",
    tone: "accent",
    items: [
      ["2.0 s accounting tick", "time credited to the app that held focus"],
      ["UI Automation", "browser tab, coalesced"],
      ["30 s heartbeat", "SQLite WAL write"],
    ],
  },
  {
    title: "Main thread",
    aside: "Qt",
    tone: "plain",
    items: [
      ["QApplication loop", "rendering, input"],
      ["Qt signals in", "no worker touches a widget"],
    ],
  },
  {
    title: "Disk",
    aside: "local",
    tone: "plain",
    items: [
      ["WAL mode", "reads never block the writer"],
      ["the database file", "digital_wellbeing.db, the only copy"],
    ],
  },
]

const ring = {
  accent: "border-accent/60 bg-accent/8",
  plain: "border-line bg-panel-2/60",
} as const

export function ThreadModel() {
  return (
    <Diagram
      id="diagram-threads"
      title="Threads and processes"
      source="docs/ARCHITECTURE.md, section 3"
      caption="The invariant the document states and the code keeps: widgets are modified on the main thread only, and worker threads report back through signals."
    >
      <div className="min-w-[40rem]">
        <div className="grid grid-cols-5 gap-1.5">
          {columns.map((column, index) => (
            <div key={column.title} className="relative">
              <div className={`h-full rounded-lg border px-2.5 py-2.5 ${ring[column.tone as "accent" | "plain"]}`}>
                <p className="font-mono text-[0.6875rem] leading-tight text-ink">{column.title}</p>
                <p className="mt-0.5 font-mono text-[0.625rem] uppercase tracking-[0.1em] text-muted">
                  {column.aside}
                </p>
                <ul className="mt-2 space-y-1.5 border-t border-line pt-2">
                  {column.items.map(([name, detail]) => (
                    <li key={name}>
                      <p className="font-mono text-[0.625rem] leading-tight text-ink">{name}</p>
                      <p className="mt-0.5 text-[0.625rem] leading-snug text-muted">{detail}</p>
                    </li>
                  ))}
                </ul>
              </div>
              {index < columns.length - 1 ? (
                <svg
                  aria-hidden="true"
                  viewBox="0 0 14 8"
                  className="absolute top-1/2 -right-[9px] h-2 w-[13px] -translate-y-1/2 text-line-strong"
                >
                  <path d="M0 4h10" stroke="currentColor" strokeWidth="1" />
                  <path d="M8.5 1.5 11.5 4 8.5 6.5" fill="none" stroke="currentColor" strokeWidth="1" />
                </svg>
              ) : null}
            </div>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-line pt-2.5 font-mono text-[0.625rem] text-muted">
          <span>One process, standard user privileges</span>
          <span>ThreadingHTTPServer on 127.0.0.1 for the extension bridge</span>
          <span>Watchdog in a separate process, waits for the lockout deadline</span>
        </div>
      </div>
    </Diagram>
  )
}
