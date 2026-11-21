import { Diagram } from "./figure"

/**
 * docs/ARCHITECTURE.md, section 2B, drawn as a sequence.
 *
 * The three outcomes are drawn as three stacked lanes rather than a branching
 * diagram, because that is the part a reader needs: success, fallback, and what
 * happens when neither succeeds.
 */

type Lane = {
  label: string
  tone: "accent" | "alert" | "plain"
  steps: string[]
  outcome: string
}

const lanes: Lane[] = [
  {
    label: "Windows Hello",
    tone: "accent",
    steps: [
      "Lock modal appears over the app",
      "User scans face or fingerprint",
      "WinRT consent verifier returns granted",
    ],
    outcome: "Grant issued, modal dismissed",
  },
  {
    label: "Local PIN",
    tone: "plain",
    steps: [
      "Hello unavailable or declined",
      "User enters the PIN, 4 to 8 digits",
      "PBKDF2 hash compared with the stored salt",
    ],
    outcome: "Grant issued, modal dismissed",
  },
  {
    label: "Neither",
    tone: "alert",
    steps: [
      "Window dismissed or attempt failed",
      "No grant is recorded for the process",
      "Focus is pulled away from the app",
    ],
    outcome: "App minimized or blocked",
  },
]

const toneRing = {
  accent: "border-accent/60",
  plain: "border-line-strong",
  alert: "border-alert/60",
} as const

export function LockerSequence() {
  return (
    <Diagram
      id="diagram-app-locker"
      title="App Locker, one unlock"
      source="docs/ARCHITECTURE.md, section 2B"
      caption="A grant is per process and expires. Every Launch, 5 minutes, or 15 minutes are the three durations the app ships with, plus Until Application Closes."
    >
      <div className="min-w-[30rem]">
        <div className="flex items-center gap-2 pb-3">
          <span className="h-2 w-2 shrink-0 rounded-full border border-line-strong" aria-hidden="true" />
          <p className="font-mono text-[0.6875rem] text-ink">Foreground match</p>
          <p className="text-[0.6875rem] text-muted">
            AppLocker sees a locked executable take focus, with no live grant
          </p>
        </div>

        <ol className="grid gap-2.5">
          {lanes.map((lane, index) => (
            <li key={lane.label} className={`rounded-lg border ${toneRing[lane.tone]} bg-panel-2/50`}>
              <div className="flex items-baseline justify-between gap-3 border-b border-line px-3 py-1.5">
                <p className="font-mono text-[0.6875rem] uppercase tracking-[0.1em] text-ink">
                  {index + 1}. {lane.label}
                </p>
                <p className="font-mono text-[0.625rem] text-muted">{lane.outcome}</p>
              </div>
              <div className="grid gap-1.5 px-3 py-2.5 sm:grid-cols-3">
                {lane.steps.map((step, i) => (
                  <div key={step} className="flex gap-1.5">
                    <span
                      aria-hidden="true"
                      className="mt-0.5 font-mono text-[0.625rem] text-muted"
                    >
                      {i + 1}
                    </span>
                    <p className="text-[0.75rem] leading-snug text-ink">{step}</p>
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ol>

        <p className="mt-3 font-mono text-[0.625rem] leading-relaxed text-muted">
          The modal sits above the protected window, so the app under it keeps running but cannot
          be reached until the attempt resolves.
        </p>
      </div>
    </Diagram>
  )
}
