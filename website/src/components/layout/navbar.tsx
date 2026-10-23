"use client"
import { useState, useEffect } from "react"
import Link from "next/link"
import Image from "next/image"
import { siteConfig } from "@/config/site"
import { Sun, Moon, Download } from "lucide-react"

export function Navbar() {
  const [theme, setTheme] = useState<"dark" | "light">("dark")

  const applyTheme = (t: "dark" | "light") => {
    if (t === "light") {
      document.documentElement.classList.add("light")
      document.documentElement.classList.remove("dark")
      document.documentElement.style.colorScheme = "light"
    } else {
      document.documentElement.classList.add("dark")
      document.documentElement.classList.remove("light")
      document.documentElement.style.colorScheme = "dark"
    }
  }

  useEffect(() => {
    const saved = (localStorage.getItem("dw-website-theme")) as "dark" | "light" | null
    const initial = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
    setTheme(initial)
    applyTheme(initial)
  }, [])

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark"
    setTheme(next)
    localStorage.setItem("dw-website-theme", next)
    applyTheme(next)
  }

  return (
    <header className="fixed top-6 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
      <nav className="glass-island rounded-full p-2 pl-4 pr-2 flex items-center justify-between gap-4 md:gap-8 pointer-events-auto max-w-3xl w-full shadow-xl transition-all duration-300">
        {/* Left: Canonical Logo + Name */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="relative w-7 h-7 flex-shrink-0 transition-transform duration-300 group-hover:scale-110">
            <Image
              src="/logo.png"
              alt="Digital Wellbeing"
              width={28}
              height={28}
              className="object-contain"
              priority
            />
          </div>
          <span className="font-bold text-sm tracking-wider text-slate-900 dark:text-foreground">
            DIGITAL WELLBEING
          </span>
        </Link>

        {/* Center: Navigation Links */}
        <div className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-700 dark:text-foreground/70">
          <Link
            href="#product"
            className="hover:text-slate-950 dark:hover:text-foreground transition-colors duration-200"
          >
            Product
          </Link>
          <Link
            href="#capabilities"
            className="hover:text-slate-950 dark:hover:text-foreground transition-colors duration-200"
          >
            Capabilities
          </Link>
          <Link
            href="#themes"
            className="hover:text-slate-950 dark:hover:text-foreground transition-colors duration-200"
          >
            Themes
          </Link>
          <Link
            href="#privacy"
            className="hover:text-slate-950 dark:hover:text-foreground transition-colors duration-200"
          >
            Privacy
          </Link>
        </div>

        {/* Right: Theme Toggle & CTA Pill */}
        <div className="flex items-center gap-2">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle theme"
            className="p-2 rounded-full text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-foreground hover:bg-black/[0.05] dark:hover:bg-white/[0.06] transition-colors cursor-pointer"
            title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
          >
            {theme === "dark" ? (
              <Sun className="w-4 h-4 text-dw-amber" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600" />
            )}
          </button>

          <Link
            href={siteConfig.links.github}
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex text-xs font-medium text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-foreground transition-colors px-2.5 py-1.5"
          >
            GitHub
          </Link>

          <a
            href="/api/download"
            className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold transition-all duration-200 cursor-pointer bg-slate-900 text-white dark:bg-foreground dark:text-background hover:opacity-90 shadow-md glow-emerald"
            title="Download Digital Wellbeing for Windows"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download</span>
          </a>
        </div>
      </nav>
    </header>
  )
}
