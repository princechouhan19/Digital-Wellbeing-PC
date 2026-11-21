"use client"

import { useEffect, useRef, useState, type CSSProperties } from "react"
import { useMotionAllowed, useTabHidden } from "@/components/system/browser-state"
import { ledger, quotas } from "@/data/site"

/** Deterministic pseudo-random so server and client agree while animating a scripted day. */
function nextIndex(prev: number) {
  return (prev + 3 + (prev % 2)) % ledger.length
}

export function LedgerPanel({ compact = false }: { compact?: boolean }) {
  const motionAllowed = useMotionAllowed()
  const tabHidden = useTabHidden()
  const [index, setIndex] = useState(0)
  const [offscreen, setOffscreen] = useState(false)
  const [booted, setBooted] = useState(false)
  const hostRef = useRef<HTMLDivElement>(null)
  const live = motionAllowed
  const paused = !motionAllowed || tabHidden || offscreen

  // The boot sequence is CSS; the timer only retires it so the 2.4s live row
  // advance never replays the entrance.
  useEffect(() => {
    const id = window.setTimeout(() => setBooted(true), 1600)
    return () => window.clearTimeout(id)
  }, [])

  useEffect(() => {
    const el = hostRef.current
    if (!el) return
    const io = new IntersectionObserver(([entry]) => setOffscreen(!entry.isIntersecting), {
      threshold: 0.15,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [])

  useEffect(() => {
    if (paused) return
    const id = window.setInterval(() => setIndex((i) => nextIndex(i)), 2400)
    return () => window.clearInterval(id)
  }, [paused])

  const rows = Array.from({ length: 5 }, (_, i) => ledger[(index + i) % ledger.length])

  return (
    <div
      ref={hostRef}
      data-boot={booted ? "off" : "on"}
      className="ledger-panel panel relative overflow-hidden shadow-[0_30px_60px_-40px_rgba(0,0,0,0.45)]"
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="micro flex items-center gap-2 text-ink">
          <span className={`dot ${paused || !live ? "opacity-40" : ""}`} aria-hidden="true" />
          Foreground ledger
        </p>
        <p className="font-mono text-[0.6875rem] text-muted">
          {!live ? "sample day" : paused ? "paused" : "live"} · 2.0 s tick
        </p>
      </div>

      <ul className="divide-y divide-line" aria-label="Recent foreground events, sample data">
        {rows.map((row, i) => (
          <li
            key={`${row.at}-${i}`}
            style={{ "--i": i } as CSSProperties}
            className="ledger-row grid grid-cols-[4.25rem_1fr] gap-x-3 gap-y-0.5 px-4 py-2.5 sm:grid-cols-[4.25rem_7.5rem_1fr]"
          >
            <span className="font-mono text-[0.6875rem] leading-5 text-muted tnum">{row.at}</span>
            <span className="col-start-2 flex items-center gap-2 text-[0.8125rem] font-medium leading-5 sm:col-start-auto">
              <StateDot state={row.state} />
              <span className="truncate">{row.app}</span>
            </span>
            <span className="col-span-2 truncate font-mono text-[0.6875rem] leading-5 text-muted sm:col-span-1">
              {row.state === "blocked" && row.quota ? (
                <span className="text-alert">
                  quota {row.quota.used} of {row.quota.limit} {row.quota.unit}, suspended
                </span>
              ) : row.state === "blocked" ? (
                <span className="text-alert">{row.domain ? `hosts block · ${row.domain}` : "hosts block"}</span>
              ) : (
                row.title
              )}
            </span>
          </li>
        ))}
      </ul>

      <div className="border-t border-line px-4 py-4">
        <div className="flex items-baseline justify-between">
          <p className="micro">Daily quotas</p>
          <p className="font-mono text-[0.6875rem] text-muted tnum">3 apps</p>
        </div>
        <ul className="mt-3 space-y-3" data-meter-group>
          {quotas.map((q, i) => {
            const pct = Math.min(100, Math.round((q.used / q.limit) * 100))
            return (
              <li
                key={q.app}
                data-over={pct >= 100}
                style={{ "--i": i } as CSSProperties}
                className="quota-row"
              >
                <div className="flex items-baseline justify-between gap-3 text-[0.75rem]">
                  <span className="quota-row__app font-mono">{q.app}</span>
                  <span className="quota-row__ratio font-mono tnum">
                    {q.used}/{q.limit} m
                  </span>
                </div>
                <div className="meter mt-1.5">
                  <span
                    className="meter__fill"
                    data-over={pct >= 100}
                    style={{ "--meter-value": `${pct}%` } as CSSProperties}
                  />
                </div>
                {!compact && <p className="mt-1 text-[0.6875rem] text-muted">{q.note}</p>}
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

function StateDot({ state }: { state: "active" | "idle" | "blocked" }) {
  if (state === "blocked") return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-alert" aria-hidden="true" />
  if (state === "idle")
    return <span className="h-1.5 w-1.5 shrink-0 rounded-full border border-muted" aria-hidden="true" />
  return <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
}
