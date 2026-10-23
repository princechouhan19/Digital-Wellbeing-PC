"use client"
import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image from "next/image"
import {
  Focus,
  Hourglass,
  ShieldAlert,
  Moon,
  BarChart3,
  Database,
  Lock,
  Unlock,
  CheckCircle2,
  Sliders,
  Bell,
  Fingerprint,
  Eye,
  Activity,
  Check
} from "lucide-react"

interface CapabilityTab {
  id: string
  label: string
  tag: string
  headline: string
  summary: string
  icon: any
  screenshot: string
  screenshotCaption: string
}

const TABS: CapabilityTab[] = [
  {
    id: "focus",
    label: "Focus",
    tag: "01 · DEEP FOCUS & WEBSITE BLOCKING",
    headline: "Take distractions off the table. Completely.",
    summary:
      "A blocker asks you to negotiate with yourself every ten minutes. Focus Mode removes the option entirely at the Windows process level with profile presets (Study, Work, Movie, Deep Focus, Custom) and reversible hosts-based website distraction blocking.",
    icon: Focus,
    screenshot: "/images/app/focus-dark.png",
    screenshotCaption: "Focus configuration & allowlist profiles",
  },
  {
    id: "timer",
    label: "App Timer",
    tag: "02 · DAILY QUOTAS",
    headline: "Proactive limits before habits turn into loops.",
    summary:
      "Set daily usage allowances on distracting software with fast 15m, 30m, 1h, 2h, or custom hour/minute presets. When your limit is reached, the app is gracefully suspended and your focus is preserved without abrupt crashes.",
    icon: Hourglass,
    screenshot: "/images/app/app-timer-config-dark.png",
    screenshotCaption: "App Timer quota configuration modal with instant time presets",
  },
  {
    id: "locker",
    label: "App Locker",
    tag: "03 · BIOMETRIC PRIVACY",
    headline: "Protect sensitive apps with Windows Hello.",
    summary:
      "Lock Telegram, Discord, Steam, or sensitive work tools behind facial recognition, fingerprint, or a custom PIN. Launches are intercepted in milliseconds, strictly isolated from App Timer.",
    icon: ShieldAlert,
    screenshot: "/images/app/authentication-dark.png",
    screenshotCaption: "Hardware-backed Windows Hello PIN authentication modal",
  },
  {
    id: "sleepguard",
    label: "SleepGuard",
    tag: "04 · CIRCADIAN RECOVERY",
    headline: "Downtime that protects your physical rest.",
    summary:
      "If you fall asleep while watching media late at night, SleepGuard detects genuine inactivity and automatically suspends your PC with a single unified, gentle audio-visual countdown dialog.",
    icon: Moon,
    screenshot: "/images/app/sleepguard-countdown-dark.png",
    screenshotCaption: "Unified SleepGuard inactivity countdown dialog with cancel protection",
  },
  {
    id: "usage",
    label: "Usage",
    tag: "05 · HOURLY INTENSITY & TRENDS",
    headline: "Hourly granularity. Real active vs idle time.",
    summary:
      "Accurate window-level foreground monitoring with an hourly activity distribution chart, synchronized Today metrics matching Home, and multi-day 7-day and 30-day views.",
    icon: Activity,
    screenshot: "/images/app/usage-dark.png",
    screenshotCaption: "Usage page showing hourly intensity distribution and category breakdown",
  },
  {
    id: "insights",
    label: "Insights",
    tag: "06 · FOREGROUND INTELLIGENCE",
    headline: "Real screen time. No vanity metrics.",
    summary:
      "Precise window-level foreground tracking that filters idle time, background updates, and audio playback. No fake 'wellness scores' or pseudo-scientific charts.",
    icon: BarChart3,
    screenshot: "/images/app/insights-dark.png",
    screenshotCaption: "Insights analytics dashboard showing category distributions and daily trends",
  },
  {
    id: "privacy",
    label: "Local-First",
    tag: "07 · ZERO TELEMETRY",
    headline: "Your machine. Your hard drive. Nothing else.",
    summary:
      "Every tracking record is written strictly to an encrypted local SQLite database in your user profile. No telemetry servers, no cloud sync, no tracking pixels, and 100% offline functionality.",
    icon: Database,
    screenshot: "/images/app/settings-dark.png",
    screenshotCaption: "Settings with personalization and local storage controls",
  },
]

export function CapabilitiesCanvas() {
  const [activeId, setActiveId] = useState("focus")
  const [viewMode, setViewMode] = useState<"interactive" | "screenshot">("interactive")
  const activeTab = TABS.find((t) => t.id === activeId) || TABS[0]

  // Interactive states inside the tabs
  const [timerMinutes, setTimerMinutes] = useState(45)
  const [pinUnlocked, setPinUnlocked] = useState(false)
  const [pinInput, setPinInput] = useState("")
  const [activeHour, setActiveHour] = useState<number | null>(14)

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Top Floating Pill Navigation */}
      <div className="flex items-center justify-center mb-8 overflow-x-auto py-2 px-4 no-scrollbar">
        <div className="inline-flex items-center gap-1.5 p-1.5 rounded-full bg-slate-100/90 dark:bg-surface border border-slate-200 dark:border-white/[0.08] backdrop-blur-xl">
          {TABS.map((tab) => {
            const isActive = activeId === tab.id
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveId(tab.id)}
                className={`relative px-4 py-2 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-2 whitespace-nowrap ${
                  isActive
                    ? "text-slate-900 dark:text-white font-semibold"
                    : "text-slate-700 dark:text-foreground/70 hover:text-slate-950 dark:hover:text-white hover:bg-black/[0.03] dark:hover:bg-white/[0.02]"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="activeTabBadge"
                    className="absolute inset-0 rounded-full bg-white dark:bg-white/[0.12] border border-slate-200 dark:border-white/20 shadow-sm"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <Icon className="w-3.5 h-3.5 relative z-10" />
                <span className="relative z-10">{tab.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Canvas Card */}
      <div className="glass-card rounded-3xl p-6 md:p-10 border border-slate-200 dark:border-white/[0.08] relative overflow-hidden">
        {/* View Mode Toggle */}
        <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono tracking-[0.2em] text-dw-emerald uppercase font-semibold">
              {activeTab.tag}
            </span>
          </div>
          <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-slate-100 dark:bg-surface border border-slate-200 dark:border-white/[0.08]">
            <button
              onClick={() => setViewMode("interactive")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 ${
                viewMode === "interactive"
                  ? "bg-white dark:bg-white/[0.12] text-slate-900 dark:text-white border border-slate-200 dark:border-white/20 shadow-sm"
                  : "text-slate-600 dark:text-foreground/60 hover:text-slate-950 dark:hover:text-white"
              }`}
            >
              <Sliders className="w-3.5 h-3.5 text-dw-emerald" />
              <span>Interactive</span>
            </button>
            <button
              onClick={() => setViewMode("screenshot")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold cursor-pointer transition-all flex items-center gap-1.5 ${
                viewMode === "screenshot"
                  ? "bg-dw-emerald/15 text-dw-emerald border border-dw-emerald/30 shadow-sm"
                  : "text-slate-600 dark:text-foreground/60 hover:text-slate-950 dark:hover:text-white"
              }`}
            >
              <Eye className="w-3.5 h-3.5 text-dw-amber" />
              <span>App Screenshot</span>
            </button>
          </div>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={`${activeTab.id}-${viewMode}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center"
          >
            {/* Left Column: Conceptual Overview */}
            <div className="lg:col-span-5 space-y-4 text-left">
              <h3 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900 dark:text-white leading-snug">
                {activeTab.headline}
              </h3>
              <p className="text-sm md:text-base text-slate-700 dark:text-foreground/75 leading-relaxed font-normal">
                {activeTab.summary}
              </p>
            </div>

            {/* Right Column: Interactive Prototype OR Real App Screenshot */}
            <div className="lg:col-span-7">
              {viewMode === "screenshot" ? (
                <div className="relative rounded-2xl overflow-hidden bg-slate-100 dark:bg-black/60 border border-slate-200 dark:border-white/[0.12] aspect-[16/10] shadow-2xl group">
                  <Image
                    src={activeTab.screenshot}
                    alt={activeTab.headline}
                    fill
                    sizes="(max-width: 1024px) 100vw, 700px"
                    className="object-cover object-top transition-transform duration-500 group-hover:scale-[1.01]"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent p-3 pt-6 text-left">
                    <p className="text-xs text-white font-medium">{activeTab.screenshotCaption}</p>
                    <p className="text-[10px] text-white/70 font-mono">Digital Wellbeing · Windows 10 & 11</p>
                  </div>
                </div>
              ) : (
                <div className="rounded-2xl bg-slate-50/90 dark:bg-black/40 border border-slate-200 dark:border-white/[0.08] p-6 md:p-8 min-h-[320px] flex flex-col justify-center relative overflow-hidden shadow-inner">
                  {/* 1. FOCUS TAB */}
                  {activeTab.id === "focus" && (
                    <div className="space-y-6">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-dw-emerald/10 border border-dw-emerald/20 flex items-center justify-center text-dw-emerald">
                            <Focus className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                              Deep Focus Mode
                            </p>
                            <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                              Kernel-Level Process Interception & Website Blocking
                            </p>
                          </div>
                        </div>
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-emerald/15 text-dw-emerald border border-dw-emerald/30">
                          ACTIVE · STRICT
                        </span>
                      </div>

                      <div className="space-y-2 text-left">
                        <div className="text-[11px] uppercase tracking-wider text-slate-600 dark:text-foreground/65 font-mono">
                          Permitted Applications
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {["VS Code", "Windows Terminal", "Obsidian", "Figma"].map((app) => (
                            <span
                              key={app}
                              className="px-3 py-1.5 rounded-xl bg-white dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08] text-xs font-medium text-slate-800 dark:text-foreground/80 flex items-center gap-1.5 shadow-sm"
                            >
                              <CheckCircle2 className="w-3 h-3 text-dw-emerald" />
                              {app}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="p-3 rounded-xl bg-red-500/[0.06] border border-red-500/20 text-left flex items-start gap-3">
                        <ShieldAlert className="w-4 h-4 text-red-500 dark:text-red-400 shrink-0 mt-0.5" />
                        <div className="text-xs">
                          <span className="text-red-700 dark:text-red-300 font-semibold">Strict Rule Active:</span>{" "}
                          <span className="text-slate-700 dark:text-foreground/70">
                            Non-allowlisted processes and blocked websites (social/games) are instantly intercepted.
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2. APP TIMER TAB */}
                  {activeTab.id === "timer" && (
                    <div className="space-y-6 text-left">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div>
                          <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                            Daily Quota Simulator
                          </p>
                          <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                            Target: social & entertainment applications
                          </p>
                        </div>
                        <span className="text-lg font-mono font-bold text-dw-amber">
                          {timerMinutes}m daily limit
                        </span>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between text-xs text-slate-700 dark:text-foreground/70 font-mono">
                          <span>Allowance adjustment:</span>
                          <span>{timerMinutes} minutes</span>
                        </div>
                        <input
                          type="range"
                          min="15"
                          max="120"
                          step="5"
                          value={timerMinutes}
                          onChange={(e) => setTimerMinutes(Number(e.target.value))}
                          className="w-full accent-dw-amber cursor-pointer bg-slate-200 dark:bg-white/10 rounded-lg h-2"
                        />
                        <div className="flex justify-between gap-2 pt-1">
                          {[15, 30, 60, 120].map((preset) => (
                            <button
                              key={preset}
                              onClick={() => setTimerMinutes(preset)}
                              className={`px-2 py-1 rounded text-[10px] font-mono transition-colors ${
                                timerMinutes === preset
                                  ? "bg-dw-amber/20 text-dw-amber border border-dw-amber/30"
                                  : "bg-white dark:bg-white/[0.04] text-slate-700 dark:text-foreground/70 border border-slate-200 dark:border-transparent hover:text-slate-900 dark:hover:text-white shadow-xs"
                              }`}
                            >
                              {preset >= 60 ? `${preset / 60}h` : `${preset}m`}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] space-y-2 shadow-xs">
                        <div className="flex justify-between text-xs">
                          <span className="text-slate-800 dark:text-foreground/80">Discord.exe today:</span>
                          <span className="font-mono text-dw-amber font-semibold">
                            {Math.min(timerMinutes, 38)}m / {timerMinutes}m
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-dw-amber rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(100, (38 / timerMinutes) * 100)}%`,
                            }}
                          />
                        </div>
                        <p className="text-[11px] text-slate-600 dark:text-foreground/65">
                          {38 >= timerMinutes
                            ? "Limit reached: Application gracefully paused."
                            : `${timerMinutes - 38} minutes remaining before pause.`}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* 3. APP LOCKER TAB */}
                  {activeTab.id === "locker" && (
                    <div className="space-y-5 text-left max-w-sm mx-auto w-full">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Fingerprint className="w-5 h-5 text-dw-emerald" />
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white">
                            Security Gate Preview
                          </span>
                        </div>
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-mono ${
                            pinUnlocked
                              ? "bg-dw-emerald/20 text-dw-emerald"
                              : "bg-slate-200 dark:bg-white/10 text-slate-700 dark:text-foreground/70"
                          }`}
                        >
                          {pinUnlocked ? "AUTHENTICATED" : "LOCKED"}
                        </span>
                      </div>

                      <div className="p-5 rounded-2xl bg-white dark:bg-black/60 border border-slate-200 dark:border-white/10 text-center space-y-4 shadow-sm">
                        <div className="w-12 h-12 rounded-full mx-auto flex items-center justify-center bg-slate-100 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08]">
                          {pinUnlocked ? (
                            <Unlock className="w-6 h-6 text-dw-emerald" />
                          ) : (
                            <Lock className="w-6 h-6 text-dw-amber" />
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-slate-900 dark:text-white">Telegram.exe Intercepted</p>
                          <p className="text-xs text-slate-600 dark:text-foreground/65 mt-1">
                            {pinUnlocked
                              ? "Access granted via Windows Hello."
                              : "Enter sample PIN (1234) or click authenticate."}
                          </p>
                        </div>

                        {!pinUnlocked ? (
                          <div className="flex gap-2 justify-center">
                            <input
                              type="password"
                              maxLength={4}
                              placeholder="PIN"
                              value={pinInput}
                              onChange={(e) => {
                                setPinInput(e.target.value)
                                if (e.target.value === "1234") {
                                   setPinUnlocked(true)
                                  setPinInput("")
                                }
                              }}
                              className="w-24 text-center px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-white/5 border border-slate-300 dark:border-white/15 text-sm text-slate-900 dark:text-white font-mono focus:outline-none focus:border-dw-emerald"
                            />
                            <button
                              onClick={() => setPinUnlocked(true)}
                              className="px-3 py-1.5 rounded-lg bg-dw-emerald text-black text-xs font-semibold hover:bg-dw-emerald/90 transition-colors cursor-pointer"
                            >
                              Verify
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setPinUnlocked(false)}
                            className="px-4 py-1.5 rounded-lg bg-slate-100 dark:bg-white/10 text-xs text-slate-800 dark:text-foreground/80 hover:bg-slate-200 dark:hover:bg-white/15 transition-colors cursor-pointer"
                          >
                            Reset Lock
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 4. SLEEPGUARD TAB */}
                  {activeTab.id === "sleepguard" && (
                    <div className="space-y-6 text-left">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-500">
                            <Moon className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                              SleepGuard Inactivity Monitor
                            </p>
                            <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                              Circadian window: 11:00 PM – 6:00 AM
                            </p>
                          </div>
                        </div>
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-600 dark:text-indigo-300 border border-indigo-500/30">
                          STANDBY
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] space-y-3 shadow-xs">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-800 dark:text-foreground/80">Idle Threshold Countdown:</span>
                          <span className="font-mono text-indigo-600 dark:text-indigo-300 font-bold">15m idle detected</span>
                        </div>
                        <div className="p-3 rounded-lg bg-indigo-500/[0.08] border border-indigo-500/20 text-xs text-slate-800 dark:text-foreground/80 flex items-center gap-3">
                          <Bell className="w-4 h-4 text-indigo-500 dark:text-indigo-400 shrink-0" />
                          <span>
                            A single warning dialog: your PC safely sleeps in 60s unless you cancel or motion is detected.
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 5. USAGE TAB */}
                  {activeTab.id === "usage" && (
                    <div className="space-y-6 text-left">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div>
                          <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                            Hourly Activity Intensity (Today)
                          </p>
                          <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                            3h 0m Screen Time · 2h 40m Active
                          </p>
                        </div>
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-emerald/15 text-dw-emerald border border-dw-emerald/30">
                          TODAY
                        </span>
                      </div>

                      {/* 24-Hour Mini Activity Chart */}
                      <div className="space-y-2">
                        <div className="flex items-end justify-between gap-1 h-20 px-2 pt-2 bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] rounded-xl shadow-xs">
                          {[
                            0, 0, 0, 0, 0, 0, 0, 0, 15, 38, 45, 50, 20, 10, 52, 40,
                            25, 0, 0, 0, 0, 0, 0, 0,
                          ].map((val, idx) => (
                            <div
                              key={idx}
                              onMouseEnter={() => setActiveHour(idx)}
                              className="flex-1 h-full flex items-end group relative cursor-pointer"
                            >
                              <div
                                className={`w-full rounded-t transition-all ${
                                  activeHour === idx
                                    ? "bg-dw-emerald"
                                    : val > 0
                                    ? "bg-slate-300 hover:bg-slate-400 dark:bg-white/20 dark:hover:bg-white/40"
                                    : "bg-slate-100 dark:bg-white/5"
                                }`}
                                style={{ height: `${Math.max(8, (val / 60) * 100)}%` }}
                              />
                            </div>
                          ))}
                        </div>
                        <div className="flex justify-between text-[10px] text-slate-600 dark:text-foreground/65 font-mono px-2">
                          <span>12 AM</span>
                          <span>6 AM</span>
                          <span>12 PM</span>
                          <span>6 PM</span>
                          <span>11 PM</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-xs p-3 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] shadow-xs">
                        <span className="text-slate-700 dark:text-foreground/70 font-mono">Selected Hour: {activeHour ?? 14}:00</span>
                        <span className="text-dw-emerald font-semibold font-mono">
                          {activeHour === 14 ? "52m active" : activeHour ? "Recorded activity" : "No activity"}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 6. INSIGHTS TAB */}
                  {activeTab.id === "insights" && (
                    <div className="space-y-6 text-left">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div>
                          <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                            Foreground Session Analytics
                          </p>
                          <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                            Native Win32 event hooks · Sub-second accuracy
                          </p>
                        </div>
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-emerald/15 text-dw-emerald border border-dw-emerald/30">
                          CALM DATA
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div className="p-3 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] text-center shadow-xs">
                          <div className="text-xs text-slate-600 dark:text-foreground/65 font-mono">Focus Ratio</div>
                          <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">78%</div>
                        </div>
                        <div className="p-3 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] text-center shadow-xs">
                          <div className="text-xs text-slate-600 dark:text-foreground/65 font-mono">Deep Blocks</div>
                          <div className="text-xl font-bold text-dw-emerald mt-1">4 sessions</div>
                        </div>
                        <div className="p-3 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/[0.06] text-center shadow-xs">
                          <div className="text-xs text-slate-600 dark:text-foreground/65 font-mono">Friction Saved</div>
                          <div className="text-xl font-bold text-dw-amber mt-1">1h 14m</div>
                        </div>
                      </div>

                      <div className="text-[11px] text-slate-600 dark:text-foreground/65 italic text-center">
                        No deceptive wellness scores. Just raw, honest visibility into where your hours went.
                      </div>
                    </div>
                  )}

                  {/* 7. LOCAL-FIRST PRIVACY TAB */}
                  {activeTab.id === "privacy" && (
                    <div className="space-y-6 text-left">
                      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/[0.06] pb-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-dw-emerald/10 border border-dw-emerald/20 flex items-center justify-center text-dw-emerald">
                            <Database className="w-4 h-4" />
                          </div>
                          <div>
                            <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                              Local SQLite Architecture
                            </p>
                            <p className="text-[11px] text-slate-600 dark:text-foreground/65 font-mono">
                              ~/.digital_wellbeing/digital_wellbeing.db
                            </p>
                          </div>
                        </div>
                        <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-emerald/15 text-dw-emerald border border-dw-emerald/30">
                          100% OFFLINE
                        </span>
                      </div>

                      <div className="p-4 rounded-xl bg-slate-900 text-slate-100 dark:bg-black/60 dark:text-slate-200 border border-slate-800 dark:border-white/10 font-mono text-xs space-y-1.5 shadow-sm">
                        <div className="text-dw-emerald font-semibold">// Zero Cloud Sync Protocol</div>
                        <div>• Network socket listening: DISABLED</div>
                        <div>• Outbound usage telemetries: 0 packets</div>
                        <div>• Third-party data brokers: NONE</div>
                        <div>• Database location: Local NVMe / SSD only</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
