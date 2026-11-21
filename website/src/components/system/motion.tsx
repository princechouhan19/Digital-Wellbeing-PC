"use client"

import { useEffect } from "react"

/**
 * The page has one idle behaviour: things arrive once, in the order they are
 * read, then hold. A single IntersectionObserver drives every path:
 *
 *   .reveal              section blocks, staggered inside a [data-stagger] group
 *   [data-meter-group]   quota meters, which fill left to right on entry
 *
 * There is no scroll listener, no parallax and no cursor follower, so the
 * compositor keeps the scrolling thread to itself. Everything gated here is
 * also gated on html.motion, which the pre-paint boot script only adds when
 * the visitor has not asked for reduced motion; without JS nothing is hidden.
 */
export function Motion() {
  useEffect(() => {
    const root = document.documentElement
    if (!root.classList.contains("motion")) return

    // Children of a stagger group are delayed by their reading order. Capped at
    // six steps so a long section cannot take a second to arrive.
    const groups = Array.from(document.querySelectorAll<HTMLElement>("[data-stagger]"))
    for (const group of groups) {
      const items = Array.from(group.querySelectorAll<HTMLElement>(":scope > .reveal"))
      items.forEach((item, index) => {
        item.style.setProperty("--reveal-delay", `${Math.min(index, 6) * 70}ms`)
      })
    }

    const reveals = Array.from(document.querySelectorAll<HTMLElement>(".reveal"))
    const meters = Array.from(document.querySelectorAll<HTMLElement>("[data-meter-group]"))
    if (!reveals.length && !meters.length) return

    // Anything already on screen at first paint is marked before reveal-ready
    // lands, so a deep link never flashes content that is then hidden. Meters
    // are deliberately left alone: they should fill on entry, even at the top.
    const viewport = window.innerHeight
    for (const el of reveals) {
      const rect = el.getBoundingClientRect()
      if (rect.top < viewport * 0.92 && rect.bottom > 0) el.classList.add("is-in")
    }
    root.classList.add("reveal-ready")

    if (!("IntersectionObserver" in window)) {
      for (const el of [...reveals, ...meters]) el.classList.add("is-in")
      return
    }

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

    for (const el of reveals) {
      if (!el.classList.contains("is-in")) io.observe(el)
    }
    for (const el of meters) io.observe(el)

    return () => io.disconnect()
  }, [])

  return null
}
