"use client"

import { useState } from "react"
import Image from "next/image"
import { screens } from "@/data/site"

export function Screens() {
  const [active, setActive] = useState(screens[0].id)
  const current = screens.find((s) => s.id === active) ?? screens[0]

  return (
    <div>
      <div className="overflow-hidden rounded-xl border border-line bg-panel">
        <div className="flex items-center justify-between gap-3 border-b border-line px-3 py-2">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-line-strong" aria-hidden="true" />
            <span className="h-2 w-2 rounded-full bg-line-strong" aria-hidden="true" />
            <span className="h-2 w-2 rounded-full bg-line-strong" aria-hidden="true" />
          </div>
          <p className="font-mono text-[0.625rem] uppercase tracking-[0.12em] text-muted">
            {current.name} · 1500 × 1000
          </p>
        </div>

        <div className="relative aspect-[3/2] bg-[#0b0f14]">
          {screens.map((s) => {
            const name = s.id === "app-timer" || s.id === "app-locker" ? s.id : s.id
            const isActive = s.id === active
            return (
              <Image
                key={s.id}
                src={`/images/app/${name}-dark.png`}
                alt={`${s.name} page: ${s.caption}`}
                fill
                sizes="(max-width: 768px) 100vw, 720px"
                loading={isActive ? "eager" : "lazy"}
                aria-hidden={!isActive}
                className={`object-cover object-top transition-opacity duration-300 ${
                  isActive ? "opacity-100" : "opacity-0"
                }`}
              />
            )
          })}
        </div>
      </div>

      <div className="mt-3 flex items-start justify-between gap-4">
        <p className="text-[0.8125rem] leading-relaxed text-muted">{current.caption}</p>
        <p className="shrink-0 font-mono text-[0.6875rem] text-muted tnum">
          {String(screens.indexOf(current) + 1).padStart(2, "0")}/{String(screens.length).padStart(2, "0")}
        </p>
      </div>

      <div className="mt-5 flex flex-wrap gap-1.5">
        {screens.map((s) => {
          const isActive = s.id === active
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => setActive(s.id)}
              aria-pressed={isActive}
              className={`rounded-full border px-3 py-1.5 text-[0.75rem] font-medium transition-colors ${
                isActive
                  ? "border-ink bg-ink text-ground"
                  : "border-line text-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              {s.name}
            </button>
          )
        })}
      </div>
      <p className="sr-only" aria-live="polite">
        {current.name} page selected. {current.caption}
      </p>
    </div>
  )
}
