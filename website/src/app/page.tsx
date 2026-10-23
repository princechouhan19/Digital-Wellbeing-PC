"use client"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image from "next/image"
import { SoftwareDemo } from "@/components/interactive/software-demo"
import { CapabilitiesCanvas } from "@/components/interactive/capabilities-canvas"
import {
  ShieldCheck,
  Cpu,
  Moon,
  Sun,
  HardDrive,
  EyeOff,
  Terminal,
  Zap,
  Palette,
  Download,
  Sparkles,
  Layers,
  Activity,
  CheckCircle2,
} from "lucide-react"

export default function Home() {
  const [themeSectionMode, setThemeSectionMode] = useState<"dark" | "light">("dark")
  const [themeSectionScreen, setThemeSectionScreen] = useState<"home" | "usage" | "focus" | "insights" | "settings">("home")

  const themeScreens = {
    home: {
      title: "Dashboard & Realtime Activity",
      desc: "Personalized greeting, instant glance at daily screen time, active app breakdown, and quick focus controls.",
      dark: "/images/app/home-dark.png",
      light: "/images/app/home-light.png",
    },
    usage: {
      title: "Usage & Hourly Intensity",
      desc: "Precise hourly active distribution, 1-day, 7-day, and 30-day activity trends, and modern category breakdowns.",
      dark: "/images/app/usage-dark.png",
      light: "/images/app/usage-light.png",
    },
    focus: {
      title: "Focus Mode & Preflight Enforcement",
      desc: "Process-level application allowlisting and hosts-based website distraction blocking.",
      dark: "/images/app/focus-dark.png",
      light: "/images/app/focus-light.png",
    },
    insights: {
      title: "Foreground Intelligence & Trends",
      desc: "Category distributions, weekly screen time patterns, and high-contrast analytical charts.",
      dark: "/images/app/insights-dark.png",
      light: "/images/app/insights-light.png",
    },
    settings: {
      title: "Categorized Preferences & Privacy",
      desc: "Display name customization, clean segmented theme controls, SleepGuard timing, and local database management.",
      dark: "/images/app/settings-dark.png",
      light: "/images/app/settings-light.png",
    },
  }

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground transition-colors duration-300">
      <main className="flex-1">
        
        {/* ===================================================
            HERO SECTION WITH LIVE INTERACTIVE SOFTWARE DEMO
        =================================================== */}
        <section className="relative pt-32 pb-20 md:pt-40 md:pb-28 overflow-hidden text-center">
          {/* Ambient Glow / Radial Gradients */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[720px] h-[380px] bg-gradient-to-tr from-dw-emerald/15 via-dw-amber/10 to-transparent blur-[150px] pointer-events-none -z-10" />

          <div className="container mx-auto px-4 sm:px-6 max-w-6xl">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="space-y-6"
            >
              {/* Category Pill Tag */}
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-slate-100/80 dark:bg-surface border border-slate-200 dark:border-border text-[11px] font-mono uppercase tracking-[0.2em] text-slate-800 dark:text-foreground/80 backdrop-blur-md">
                <span className="w-1.5 h-1.5 rounded-full bg-dw-emerald animate-pulse" />
                <span>Windows 10 & 11 (64-bit) · Native PySide6</span>
              </div>

              {/* Bold Headline */}
              <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-slate-900 dark:text-foreground leading-[1.1] max-w-4xl mx-auto">
                Control your machine. <br />
                <span className="text-slate-800 dark:text-foreground/80 font-semibold">
                  Not the other way around.
                </span>
              </h1>

              {/* Subtext */}
              <p className="text-base sm:text-xl text-slate-700 dark:text-foreground/75 max-w-2xl mx-auto leading-relaxed font-normal">
                Digital Wellbeing is an Apple-grade digital wellbeing and attention-control system for Windows. It tracks your screen time, enforces boundaries, and filters the web — completely locally with zero telemetry.
              </p>

              {/* Primary Download CTAs */}
              <div className="pt-2 pb-2 flex flex-wrap items-center justify-center gap-3">
                <a
                  href="/api/download"
                  className="inline-flex items-center gap-3 px-8 py-3.5 rounded-full text-sm sm:text-base font-semibold transition-all duration-200 bg-slate-900 text-white dark:bg-foreground dark:text-background hover:opacity-90 shadow-xl glow-emerald cursor-pointer group"
                  title="Download for Windows"
                >
                  <Download className="w-5 h-5 transition-transform duration-200 group-hover:-translate-y-0.5" />
                  <span>Download for Windows</span>
                </a>
                <a
                  href="https://github.com/princechouhan19/Digital-Wellbeing-PC"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full text-sm font-semibold transition-all duration-200 bg-slate-100 dark:bg-surface border border-slate-200 dark:border-border text-slate-900 dark:text-foreground hover:bg-slate-200/80 dark:hover:bg-white/10"
                >
                  <span>View on GitHub</span>
                </a>
              </div>

              <p className="text-xs font-mono text-slate-600 dark:text-foreground/60">
                Windows 10 / 11 (64-bit) · Inno Setup installer · Free &amp; local-first
              </p>

              {/* Interactive App Banner / Prompt */}
              <div className="pt-8 pb-2 flex flex-col items-center justify-center gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-dw-emerald/10 border border-dw-emerald/30 text-[11px] font-mono text-dw-emerald font-semibold uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Interactive Live Software Demo · Click Below to Test</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-foreground/65 max-w-md">
                  Interact with real app pages: switch between modules, start a focus sprint, test PIN unlocking, adjust quotas, and toggle themes.
                </p>
              </div>

              {/* ===================================================
                  REAL INTERACTIVE SOFTWARE APPLICATION PREVIEW
              =================================================== */}
              <div id="product" className="scroll-mt-28">
                <SoftwareDemo />
              </div>

              {/* Native Architecture Spec Badges */}
              <div className="pt-4 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-600 dark:text-foreground/70 font-mono">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-dw-emerald" />
                  <span>Sub-25MB RAM Footprint</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-dw-amber" />
                  <span>0% Idle CPU Overhead</span>
                </div>
                <div className="flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-indigo-400" />
                  <span>100% Local SQLite Storage</span>
                </div>
                <div className="flex items-center gap-2">
                  <EyeOff className="w-4 h-4 text-emerald-400" />
                  <span>Zero Cloud Telemetry</span>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* ===================================================
            SECTION 02: CORE CAPABILITIES (INTERACTIVE CANVAS)
        =================================================== */}
        <section id="capabilities" className="scroll-mt-28 py-24 md:py-32 border-t border-slate-200 dark:border-border bg-slate-50/60 dark:bg-[#07090c] relative">
          <div className="container mx-auto px-6 max-w-6xl text-center">
            <div className="max-w-2xl mx-auto mb-14 space-y-3">
              <span className="text-[11px] font-mono tracking-[0.2em] text-dw-emerald uppercase font-semibold">
                SYSTEM ARCHITECTURE
              </span>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-foreground">
                Engineered for focus. Tested for safety.
              </h2>
              <p className="text-sm md:text-base text-slate-700 dark:text-foreground/75 leading-relaxed">
                Explore the foundational capabilities engineered to give you complete mechanical control over your operating system.
              </p>
            </div>

            {/* Interactive Tabbed Capabilities Canvas */}
            <CapabilitiesCanvas />
          </div>
        </section>

        {/* ===================================================
            SECTION 03: THEME THAT FITS YOUR WORKSPACE
        =================================================== */}
        <section id="themes" className="scroll-mt-28 py-24 md:py-32 border-t border-slate-200 dark:border-border relative">
          <div className="container mx-auto px-6 max-w-5xl">
            <div className="text-center max-w-2xl mx-auto mb-12 space-y-3">
              <span className="text-[11px] font-mono tracking-[0.2em] text-dw-amber uppercase font-semibold flex items-center justify-center gap-1.5">
                <Palette className="w-3.5 h-3.5" />
                <span>THEME THAT FITS YOUR WORKSPACE</span>
              </span>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-foreground">
                Crafted for day and night.
              </h2>
              <p className="text-sm md:text-base text-slate-700 dark:text-foreground/75 leading-relaxed">
                Digital Wellbeing supports Dark and Light themes, with clean typography, high-contrast analytics, and soft translucent materials tailored to any ambient lighting.
              </p>
            </div>

            {/* Screen Selector & Theme Selector Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6 p-2 rounded-2xl glass-card border border-slate-200 dark:border-border shadow-sm">
              {/* Screen Tabs */}
              <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar w-full sm:w-auto">
                {(["home", "usage", "focus", "insights", "settings"] as const).map((scr) => (
                  <button
                    key={scr}
                    onClick={() => setThemeSectionScreen(scr)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold capitalize cursor-pointer transition-all ${
                      themeSectionScreen === scr
                        ? "bg-slate-900 text-white dark:bg-foreground/10 dark:text-foreground border border-slate-800 dark:border-border shadow-xs"
                        : "text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-foreground"
                    }`}
                  >
                    {scr}
                  </button>
                ))}
              </div>

              {/* Mode Toggle */}
              <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-slate-100 dark:bg-surface border border-slate-200 dark:border-border">
                <button
                  onClick={() => setThemeSectionMode("dark")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 ${
                    themeSectionMode === "dark"
                      ? "bg-slate-900 text-white dark:bg-white/[0.12] dark:text-foreground border border-slate-800 dark:border-white/20 shadow-xs"
                      : "text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-foreground"
                  }`}
                >
                  <Moon className="w-3 h-3 text-indigo-400" />
                  <span>Dark</span>
                </button>
                <button
                  onClick={() => setThemeSectionMode("light")}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 ${
                    themeSectionMode === "light"
                      ? "bg-dw-emerald/15 text-dw-emerald-dark dark:text-dw-emerald border border-dw-emerald/30 shadow-xs font-bold"
                      : "text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-foreground"
                  }`}
                >
                  <Sun className="w-3 h-3 text-dw-amber" />
                  <span>Light</span>
                </button>
              </div>
            </div>

            {/* Showcase Display Card */}
            <div className="glass-card rounded-3xl p-3 md:p-5 border border-slate-200 dark:border-border shadow-xl space-y-4">
              <div className="relative rounded-2xl overflow-hidden bg-slate-950 border border-slate-200 dark:border-border aspect-[16/10] md:aspect-[16/9]">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={`${themeSectionScreen}-${themeSectionMode}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="relative w-full h-full"
                  >
                    <Image
                      src={themeScreens[themeSectionScreen][themeSectionMode]}
                      alt={`${themeScreens[themeSectionScreen].title} in ${themeSectionMode} mode`}
                      fill
                      sizes="(max-width: 1200px) 100vw, 1200px"
                      className="object-cover object-top"
                    />
                  </motion.div>
                </AnimatePresence>
              </div>

              <div className="pt-2 px-3 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs">
                <div>
                  <span className="font-bold text-slate-900 dark:text-foreground">{themeScreens[themeSectionScreen].title}</span>
                  <span className="text-slate-700 dark:text-foreground/75 ml-2 font-normal hidden md:inline">{themeScreens[themeSectionScreen].desc}</span>
                </div>
                <span className="font-mono text-slate-600 dark:text-foreground/65 text-[11px]">
                  Windows Desktop Application · {themeSectionMode === "dark" ? "Aurora Dark" : "Aurora Light"}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================
            SECTION 04: PHILOSOPHY & DIGITAL WELLBEING STORY
        =================================================== */}
        <section id="philosophy" className="scroll-mt-28 py-24 md:py-32 border-t border-slate-200 dark:border-border bg-slate-50/60 dark:bg-[#07090c] relative">
          <div className="container mx-auto px-6 max-w-5xl">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
              <div className="lg:col-span-6 space-y-6 text-left">
                <span className="text-[11px] font-mono tracking-[0.2em] text-dw-amber uppercase font-semibold">
                  HONEST WELLBEING
                </span>
                <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 dark:text-foreground leading-tight">
                  Why conventional blockers fail.
                </h2>
                <div className="space-y-4 text-sm md:text-base text-slate-700 dark:text-foreground/80 leading-relaxed">
                  <p>
                    Conventional website blockers ask you to negotiate with yourself every ten minutes. They rely on browser extensions you can disable in two clicks, and barrage you with patronizing &quot;productivity scores&quot;.
                  </p>
                  <p>
                    Willpower is a finite resource. When you are mentally exhausted at 4:00 PM, you will click past an extension block every single time.
                  </p>
                  <p>
                    Digital Wellbeing operates on a mechanical principle: <strong>if the distracting app is locked or suspended at the process level, there is nothing left to negotiate.</strong> You return to your work because there is nothing else on the table.
                  </p>
                </div>
              </div>

              <div className="lg:col-span-6">
                <div className="space-y-4">
                  <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border text-left">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-foreground uppercase tracking-wide flex items-center gap-2">
                      <Zap className="w-4 h-4 text-dw-amber" />
                      <span>Zero Friction Negotiation</span>
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-foreground/75 mt-2 leading-relaxed">
                      Lock your game clients and social platforms into Deep Focus sessions. The barrier is physical and intentional, not psychological.
                    </p>
                  </div>

                  <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border text-left">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-foreground uppercase tracking-wide flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-dw-emerald" />
                      <span>Protected Process Architecture</span>
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-foreground/75 mt-2 leading-relaxed">
                      Windows system processes (`explorer.exe`, `dwm.exe`, background services) are strictly immune to termination, keeping your PC stable.
                    </p>
                  </div>

                  <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border text-left">
                    <h4 className="text-sm font-bold text-slate-900 dark:text-foreground uppercase tracking-wide flex items-center gap-2">
                      <Moon className="w-4 h-4 text-indigo-500" />
                      <span>Circadian Sleep Guard</span>
                    </h4>
                    <p className="text-xs text-slate-700 dark:text-foreground/75 mt-2 leading-relaxed">
                      Prevents late-night passive video bingeing by safely sleeping the computer when user inactivity is verified.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================
            SECTION 05: PRIVACY GUARANTEE
        =================================================== */}
        <section id="privacy" className="scroll-mt-28 py-24 md:py-32 border-t border-slate-200 dark:border-border relative">
          <div className="container mx-auto px-6 max-w-5xl">
            <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
              <span className="text-[11px] font-mono tracking-[0.2em] text-dw-emerald uppercase font-semibold">
                PRIVACY FIRST · LOCAL ONLY
              </span>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-foreground">
                Your data never leaves your hard drive.
              </h2>
              <p className="text-sm md:text-base text-slate-700 dark:text-foreground/75 leading-relaxed">
                Privacy is not a feature we toggle on. It is the fundamental architecture of Digital Wellbeing.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
              <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border space-y-3">
                <HardDrive className="w-6 h-6 text-dw-emerald" />
                <h4 className="text-base font-bold text-slate-900 dark:text-foreground">100% Local SQLite</h4>
                <p className="text-xs text-slate-700 dark:text-foreground/75 leading-relaxed">
                  Every application timestamp and session event is committed directly to a local SQLite database in your user folder.
                </p>
              </div>

              <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border space-y-3">
                <EyeOff className="w-6 h-6 text-dw-amber" />
                <h4 className="text-base font-bold text-slate-900 dark:text-foreground">No Telemetry or Tracking</h4>
                <p className="text-xs text-slate-700 dark:text-foreground/75 leading-relaxed">
                  No telemetry pings, no usage beacons, no analytics servers, and no third-party data broker partnerships.
                </p>
              </div>

              <div className="p-6 rounded-2xl glass-card border border-slate-200 dark:border-border space-y-3">
                <ShieldCheck className="w-6 h-6 text-indigo-500" />
                <h4 className="text-base font-bold text-slate-900 dark:text-foreground">No Account Required</h4>
                <p className="text-xs text-slate-700 dark:text-foreground/75 leading-relaxed">
                  The desktop app functions completely offline without sign-in, cloud sync, or remote dependencies.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ===================================================
            SECTION 06: GET THE APP / DOWNLOAD CTA
        =================================================== */}
        <section className="py-24 md:py-36 border-t border-slate-200 dark:border-border bg-slate-50/60 dark:bg-[#07090c] relative overflow-hidden text-center">
          <div className="container mx-auto px-6 max-w-3xl space-y-8">
            <div className="w-16 h-16 rounded-full mx-auto relative flex-shrink-0 mb-4">
              <Image
                src="/logo.png"
                alt="Digital Wellbeing logo"
                width={64}
                height={64}
                className="object-contain"
              />
            </div>

            <div className="space-y-3">
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight text-slate-900 dark:text-foreground">
                Experience intentional computing.
              </h2>
              <p className="text-sm md:text-base text-slate-700 dark:text-foreground/75 max-w-lg mx-auto leading-relaxed">
                Digital Wellbeing is free to download and local-first. No account, email signup, or cloud sync is required.
              </p>
            </div>

            <div className="pt-4 flex flex-col items-center gap-3">
              <a
                href="/api/download"
                className="inline-flex items-center gap-3 px-8 py-4 rounded-full text-sm sm:text-base font-semibold transition-all duration-200 bg-slate-900 text-white dark:bg-foreground dark:text-background hover:opacity-90 shadow-xl glow-emerald cursor-pointer group"
                title="Download for Windows"
              >
                <Download className="w-5 h-5 transition-transform duration-200 group-hover:-translate-y-0.5" />
                <span>Download for Windows</span>
              </a>
              <p className="text-[11px] font-mono text-slate-600 dark:text-foreground/65 font-medium">
                Windows 10 / Windows 11 (64-bit) · Independent Software
              </p>
            </div>
          </div>
        </section>

      </main>
    </div>
  )
}
