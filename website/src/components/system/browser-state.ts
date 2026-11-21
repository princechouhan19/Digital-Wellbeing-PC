"use client"

import { useSyncExternalStore } from "react"

/**
 * Browser-only state read through useSyncExternalStore, so the server output
 * stays stable and hydration never disagrees with it.
 */

type Theme = "light" | "dark"
const themeListeners = new Set<() => void>()

function readTheme(): Theme {
  if (typeof document === "undefined") return "light"
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"
}

function subscribeTheme(listener: () => void) {
  themeListeners.add(listener)
  return () => themeListeners.delete(listener)
}

export function useTheme() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, () => "light" as Theme)

  const setTheme = (next: Theme) => {
    document.documentElement.setAttribute("data-theme", next)
    try {
      localStorage.setItem("dw-theme", next)
    } catch {
      /* storage can be blocked; the visit still uses the chosen theme */
    }
    themeListeners.forEach((listener) => listener())
  }

  return [theme, setTheme] as const
}

function subscribeMotion(listener: () => void) {
  const query = window.matchMedia("(prefers-reduced-motion: no-preference)")
  query.addEventListener("change", listener)
  return () => query.removeEventListener("change", listener)
}

/** True when the visitor has not asked for reduced motion. Server renders false. */
export function useMotionAllowed() {
  return useSyncExternalStore(
    subscribeMotion,
    () => window.matchMedia("(prefers-reduced-motion: no-preference)").matches,
    () => false,
  )
}

function subscribeVisibility(listener: () => void) {
  document.addEventListener("visibilitychange", listener)
  return () => document.removeEventListener("visibilitychange", listener)
}

export function useTabHidden() {
  return useSyncExternalStore(
    subscribeVisibility,
    () => document.hidden,
    () => false,
  )
}
