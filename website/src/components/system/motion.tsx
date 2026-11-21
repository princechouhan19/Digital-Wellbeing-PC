"use client"

import { useEffect } from "react"

/**
 * The site has exactly one idle behaviour: reveal-on-enter, driven by a single
 * IntersectionObserver. Everything else stays still. There is no parallax, no
 * cursor follower, no scroll listener, and nothing to clean up between states.
 */
export function Motion() {
  useEffect(() => {
    const root = document.documentElement
    if (!root.classList.contains("motion")) return

    const targets = Array.from(document.querySelectorAll<HTMLElement>(".reveal"))
    if (!targets.length) return
    root.classList.add("reveal-ready")

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          entry.target.classList.add("is-in")
          io.unobserve(entry.target)
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    )

    for (const el of targets) io.observe(el)
    return () => io.disconnect()
  }, [])

  return null
}
