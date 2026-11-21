"use client"

import { useState } from "react"
import Image from "next/image"
import { controls } from "@/data/site"

export function Controls() {
  const [active, setActive] = useState(controls[0].id)
  const current = controls.find((c) => c.id === active) ?? controls[0]

  return (
    <div className="grid gap-8 lg:grid-cols-12 lg:gap-10">
      {/* The index: each control is a verb the machine performs. */}
      <div className="lg:col-span-5">
        <div role="tablist" aria-label="Controls" aria-orientation="vertical" className="border-b border-line">
          {controls.map((c, i) => {
            const isActive = c.id === active
            return (
                <button
                  key={c.id}
                  role="tab"
                  type="button"
                  id={`tab-${c.id}`}
                  aria-selected={isActive}
                  aria-controls={`panel-${c.id}`}
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => setActive(c.id)}
                  onKeyDown={(e) => {
                    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return
                    e.preventDefault()
                    const dir = e.key === "ArrowDown" ? 1 : -1
                    const next = controls[(i + dir + controls.length) % controls.length]
                    setActive(next.id)
                    document.getElementById(`tab-${next.id}`)?.focus()
                  }}
                  className="group flex w-full items-baseline gap-4 border-t border-line py-4 text-left"
                >
                  <span className="font-mono text-[0.6875rem] text-muted tnum">
                    0{i + 1}
                  </span>
                  <span className="flex-1">
                    <span
                      className={`block text-[1.375rem] font-semibold tracking-tight transition-colors md:text-2xl ${
                        isActive ? "text-ink" : "text-muted group-hover:text-ink"
                      }`}
                    >
                      {c.label}
                    </span>
                    <span
                      className={`mt-1 block font-mono text-[0.6875rem] uppercase tracking-[0.12em] ${
                        isActive ? "text-accent" : "text-muted"
                      }`}
                    >
                      {c.verb}
                    </span>
                  </span>
                  <span
                    aria-hidden="true"
                    className={`h-px w-8 self-center transition-all duration-300 ease-[var(--ease-out)] ${
                      isActive ? "w-12 bg-accent" : "bg-line-strong group-hover:w-12"
                    }`}
                  />
                </button>
            )
          })}
        </div>
      </div>

      {/* The evidence for the selected control. */}
      <div className="lg:col-span-7">
        {controls.map((c) => (
          <div
            key={c.id}
            role="tabpanel"
            id={`panel-${c.id}`}
            aria-labelledby={`tab-${c.id}`}
            hidden={c.id !== current.id}
            
          >
            <div className="overflow-hidden rounded-xl border border-line bg-panel">
              <div className="flex items-center gap-2 border-b border-line px-3 py-2">
                <span className="h-2 w-2 rounded-full bg-line-strong" />
                <span className="h-2 w-2 rounded-full bg-line-strong" />
                <span className="h-2 w-2 rounded-full bg-line-strong" />
                <span className="ml-2 font-mono text-[0.625rem] tracking-wider text-muted uppercase">
                  Digital Wellbeing · {c.label}
                </span>
              </div>
              <Image
                src={c.screen}
                alt={c.alt}
                width={1500}
                height={1000}
                sizes="(max-width: 1024px) 100vw, 660px"
                className="h-auto w-full"
              />
            </div>

            <h3 className="mt-6 max-w-lg text-[1.25rem] font-semibold leading-snug tracking-tight text-balance">
              {c.headline}
            </h3>
            <p className="mt-3 max-w-xl text-[0.9375rem] leading-relaxed text-muted">{c.body}</p>
            <ul className="mt-5 space-y-1.5">
              {c.facts.map((f) => (
                <li key={f} className="flex gap-2.5 text-[0.8125rem] text-muted">
                  <span aria-hidden="true" className="mt-[0.55em] h-1 w-1 shrink-0 rounded-full bg-accent" />
                  {f}
                </li>
              ))}
            </ul>
            <p className="mt-4 font-mono text-[0.6875rem] text-muted">Screen: {c.caption}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
