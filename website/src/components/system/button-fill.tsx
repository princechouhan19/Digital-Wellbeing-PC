"use client"

import { useEffect } from "react"

/**
 * The primary action fills from the point where the pointer enters it.
 * One delegated listener, no per-element handlers, nothing on touch devices
 * beyond the press state that CSS already provides.
 */
export function ButtonFill() {
  useEffect(() => {
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return

    const onEnter = (event: PointerEvent) => {
      const node = event.target as Element | null
      if (!node || typeof node.closest !== "function") return
      const target = node.closest<HTMLElement>("[data-fill]")
      if (!target) return
      const rect = target.getBoundingClientRect()
      const x = ((event.clientX - rect.left) / rect.width) * 100
      const y = ((event.clientY - rect.top) / rect.height) * 100
      target.style.setProperty("--fill-x", `${x.toFixed(1)}%`)
      target.style.setProperty("--fill-y", `${y.toFixed(1)}%`)
    }

    document.addEventListener("pointerenter", onEnter, true)
    return () => document.removeEventListener("pointerenter", onEnter, true)
  }, [])

  return null
}
