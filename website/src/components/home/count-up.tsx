"use client"

import { useEffect, useRef, useState } from "react"
import { useMotionAllowed } from "@/components/system/browser-state"

/**
 * A measured figure that counts up once, when it enters the viewport, then
 * holds. The server renders the final digits, so a visitor without JavaScript
 * (or with reduced motion) reads the number immediately and nothing reflows:
 * the digits are tabular and the box is sized to the final string.
 */
export function CountUp({ value, className = "" }: { value: string; className?: string }) {
  const motionAllowed = useMotionAllowed()
  const ref = useRef<HTMLSpanElement>(null)
  const [frame, setFrame] = useState<string | null>(null)

  useEffect(() => {
    const el = ref.current
    if (!motionAllowed || !el) return
    if (!("IntersectionObserver" in window)) return

    const target = Number(value)
    if (!Number.isFinite(target)) return
    const decimals = value.split(".")[1]?.length ?? 0

    let raf = 0
    let started = false

    const io = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (!entry?.isIntersecting || started) return
        started = true
        io.disconnect()

        const start = performance.now()
        const duration = 900
        const step = (now: number) => {
          const progress = Math.min(1, (now - start) / duration)
          if (progress >= 1) {
            // Hand the final string back to the server-rendered markup.
            setFrame(null)
            return
          }
          const eased = 1 - Math.pow(1 - progress, 3)
          setFrame((target * eased).toFixed(decimals))
          raf = requestAnimationFrame(step)
        }
        raf = requestAnimationFrame(step)
      },
      { threshold: 0.5 },
    )

    io.observe(el)
    return () => {
      io.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [motionAllowed, value])

  return (
    <span
      ref={ref}
      className={`count tnum ${className}`}
      style={{ minInlineSize: `${value.length}ch` }}
    >
      {frame ?? value}
    </span>
  )
}
