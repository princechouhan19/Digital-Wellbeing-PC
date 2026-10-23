"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import Image from "next/image"
import {
  Home,
  Activity,
  Globe,
  Sparkles,
  Target,
  Hourglass,
  Lock,
  Unlock,
  Moon,
  Sun,
  Settings,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Zap,
  Plus,
  Trash2,
  AlertTriangle,
  Sliders,
  Laptop,
  Check,
  RefreshCw,
  Bell,
  Cpu,
} from "lucide-react"

type PageId =
  | "home"
  | "usage"
  | "websites"
  | "insights"
  | "focus"
  | "timer"
  | "locker"
  | "sleepguard"
  | "settings"

export function SoftwareDemo() {
  const [activePage, setActivePage] = useState<PageId>("home")
  const [appTheme, setAppTheme] = useState<"dark" | "light">("dark")

  // --- Home / Quick Actions State ---
  const [userName, setUserName] = useState("Prince")

  // --- Focus Timer State ---
  const [isFocusing, setIsFocusing] = useState(false)
  const [focusSeconds, setFocusSeconds] = useState(25 * 60)
  const [focusProfile, setFocusProfile] = useState<"deep" | "work" | "study" | "reading">("deep")
  const [allowlist, setAllowlist] = useState<string[]>([
    "Code.exe",
    "WindowsTerminal.exe",
    "Obsidian.exe",
    "Slack.exe",
  ])
  const [newAllowApp, setNewAllowApp] = useState("")

  useEffect(() => {
    if (!isFocusing) return
    const timer = setInterval(() => {
      setFocusSeconds((prev) => (prev > 0 ? prev - 1 : 25 * 60))
    }, 1000)
    return () => clearInterval(timer)
  }, [isFocusing])

  const formatTimer = (totalSec: number) => {
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`
  }

  // --- App Timer State ---
  const [discordLimit, setDiscordLimit] = useState(45)
  const [discordUsed, setDiscordUsed] = useState(38)
  const [steamLimit, setSteamLimit] = useState(30)
  const [steamUsed, setSteamUsed] = useState(30)
  const [spotifyLimit, setSpotifyLimit] = useState(90)
  const [spotifyUsed, setSpotifyUsed] = useState(42)

  // --- App Locker State ---
  const [pinInput, setPinInput] = useState("")
  const [isLockerAuthenticated, setIsLockerAuthenticated] = useState(false)
  const [lockedApps, setLockedApps] = useState([
    { name: "Telegram.exe", desc: "Private messaging & cloud chats", locked: true },
    { name: "Discord.exe", desc: "Communities & voice calls", locked: true },
    { name: "Financials.xlsx", desc: "Local encrypted spreadsheet", locked: true },
  ])
  const [authError, setAuthError] = useState(false)

  const handlePinDigit = (digit: string) => {
    if (pinInput.length < 4) {
      const nextPin = pinInput + digit
      setPinInput(nextPin)
      if (nextPin === "1234") {
        setIsLockerAuthenticated(true)
        setPinInput("")
        setAuthError(false)
      } else if (nextPin.length === 4) {
        setAuthError(true)
        setTimeout(() => {
          setPinInput("")
          setAuthError(false)
        }, 700)
      }
    }
  }

  // --- Websites / SafeBrowse State ---
  const [safeBrowseEnabled, setSafeBrowseEnabled] = useState(true)
  const [blockedDomains, setBlockedDomains] = useState<string[]>([
    "youtube.com",
    "x.com",
    "reddit.com",
    "tiktok.com",
    "instagram.com",
  ])
  const [newDomain, setNewDomain] = useState("")

  const handleAddDomain = () => {
    if (!newDomain.trim()) return
    const clean = newDomain.trim().toLowerCase().replace(/^https?:\/\//, "")
    if (!blockedDomains.includes(clean)) {
      setBlockedDomains([...blockedDomains, clean])
      setNewDomain("")
    }
  }

  // --- Usage / Activity State ---
  const [selectedUsageTimeframe, setSelectedUsageTimeframe] = useState<"today" | "7d" | "30d">("today")
  const [activeHourlyIndex, setActiveHourlyIndex] = useState<number>(14)
  const hourlyData = [
    { hour: "12 AM", mins: 0 },
    { hour: "1 AM", mins: 0 },
    { hour: "2 AM", mins: 0 },
    { hour: "3 AM", mins: 0 },
    { hour: "4 AM", mins: 0 },
    { hour: "5 AM", mins: 0 },
    { hour: "6 AM", mins: 0 },
    { hour: "7 AM", mins: 8 },
    { hour: "8 AM", mins: 22 },
    { hour: "9 AM", mins: 45 },
    { hour: "10 AM", mins: 54 },
    { hour: "11 AM", mins: 50 },
    { hour: "12 PM", mins: 28 },
    { hour: "1 PM", mins: 15 },
    { hour: "2 PM", mins: 52 },
    { hour: "3 PM", mins: 42 },
    { hour: "4 PM", mins: 35 },
    { hour: "5 PM", mins: 18 },
    { hour: "6 PM", mins: 0 },
    { hour: "7 PM", mins: 0 },
    { hour: "8 PM", mins: 0 },
    { hour: "9 PM", mins: 0 },
    { hour: "10 PM", mins: 0 },
    { hour: "11 PM", mins: 0 },
  ]

  // --- SleepGuard State ---
  const [sleepGuardActive, setSleepGuardActive] = useState(true)
  const [sleepGuardAction, setSleepGuardAction] = useState<"sleep" | "lock" | "hibernate">("sleep")
  const [showCountdownModal, setShowCountdownModal] = useState(false)
  const [modalCountdown, setModalCountdown] = useState(60)

  useEffect(() => {
    if (!showCountdownModal) return
    const interval = setInterval(() => {
      setModalCountdown((prev) => (prev > 0 ? prev - 1 : 60))
    }, 1000)
    return () => clearInterval(interval)
  }, [showCountdownModal])

  // --- Navigation Items ---
  const navSections = [
    {
      title: "OVERVIEW",
      items: [
        { id: "home" as PageId, label: "Home", icon: Home },
        { id: "usage" as PageId, label: "Usage", icon: Activity },
        { id: "websites" as PageId, label: "Websites", icon: Globe, badge: "SafeBrowse" },
        { id: "insights" as PageId, label: "Insights", icon: Sparkles },
      ],
    },
    {
      title: "CONTROL",
      items: [
        { id: "focus" as PageId, label: "Focus", icon: Target, badge: isFocusing ? "ACTIVE" : undefined },
        { id: "timer" as PageId, label: "App Timer", icon: Hourglass },
        { id: "locker" as PageId, label: "App Locker", icon: Lock, badge: isLockerAuthenticated ? "UNLOCKED" : "LOCKED" },
        { id: "sleepguard" as PageId, label: "SleepGuard", icon: Moon },
      ],
    },
    {
      title: "SYSTEM",
      items: [
        { id: "settings" as PageId, label: "Settings", icon: Settings },
      ],
    },
  ]

  // App Theme Classes
  const isDark = appTheme === "dark"
  const windowBg = isDark ? "bg-[#0b0f14] text-slate-100" : "bg-[#f8fafc] text-slate-900"
  const sidebarBg = isDark ? "bg-[#070a0e]/95 border-white/[0.08]" : "bg-slate-100/90 border-slate-200"
  const cardBg = isDark ? "bg-[#111720]/80 border-white/[0.08]" : "bg-white border-slate-200 shadow-sm"
  const subText = isDark ? "text-slate-400" : "text-slate-500"
  const accentBorder = isDark ? "border-white/[0.08]" : "border-slate-200"

  return (
    <div className="w-full max-w-6xl mx-auto my-6">
      {/* Outer Glow & Window Container */}
      <div className="relative rounded-3xl p-1 md:p-2 bg-gradient-to-b from-slate-200/50 via-slate-300/20 to-slate-200/50 dark:from-white/15 dark:via-white/5 dark:to-white/10 shadow-2xl backdrop-blur-2xl">
        <div className={`rounded-[22px] overflow-hidden border ${accentBorder} ${windowBg} transition-colors duration-300 shadow-2xl relative flex flex-col min-h-[680px]`}>
          
          {/* ==========================================
              NATIVE TITLEBAR (macOS / Windows Hybrid)
          ========================================== */}
          <div className={`h-11 px-4 flex items-center justify-between border-b ${accentBorder} ${isDark ? "bg-[#070a0e]" : "bg-slate-100"} select-none`}>
            {/* Window Traffic Lights */}
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/80 hover:bg-red-500 transition-colors cursor-pointer" />
              <span className="w-3 h-3 rounded-full bg-amber-500/80 hover:bg-amber-500 transition-colors cursor-pointer" />
              <span className="w-3 h-3 rounded-full bg-emerald-500/80 hover:bg-emerald-500 transition-colors cursor-pointer" />
              <span className="ml-2 text-[11px] font-mono tracking-wider font-semibold uppercase opacity-60 hidden sm:inline">
                Digital Wellbeing
              </span>
            </div>

            {/* Center: Window Title & Status */}
            <div className="flex items-center gap-2 text-xs font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-dw-emerald animate-pulse" />
              <span className="capitalize">{activePage === "sleepguard" ? "SleepGuard" : activePage}</span>
              <span className="text-[10px] font-mono opacity-50 px-1.5 py-0.5 rounded bg-black/10 dark:bg-white/10">
                Interactive Sandbox
              </span>
            </div>

            {/* Right: Quick In-App Theme Switcher */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setAppTheme(isDark ? "light" : "dark")}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all cursor-pointer ${
                  isDark
                    ? "bg-white/10 text-white hover:bg-white/15 border border-white/10"
                    : "bg-slate-200 text-slate-800 hover:bg-slate-300 border border-slate-300"
                }`}
                title="Toggle interactive app theme"
              >
                {isDark ? (
                  <>
                    <Sun className="w-3 h-3 text-dw-amber" />
                    <span className="hidden sm:inline">Light</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-3 h-3 text-indigo-500" />
                    <span className="hidden sm:inline">Dark</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* ==========================================
              MAIN APP BODY (Sidebar + Content View)
          ========================================== */}
          <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
            
            {/* --- LEFT SIDEBAR (Desktop) / TOP RAIL (Mobile) --- */}
            <aside className={`w-full md:w-60 border-b md:border-b-0 md:border-r ${sidebarBg} flex flex-col justify-between p-3 shrink-0`}>
              <div>
                {/* Brand Header */}
                <div className="flex items-center gap-3 px-3 py-3 mb-2">
                  <div className="relative w-8 h-8 rounded-lg overflow-hidden shrink-0 shadow-sm">
                    <Image
                      src="/logo.png"
                      alt="Logo"
                      width={32}
                      height={32}
                      className="object-contain"
                    />
                  </div>
                  <div>
                    <div className="text-[9px] font-mono tracking-[0.2em] uppercase text-dw-emerald font-bold leading-none">
                      DIGITAL
                    </div>
                    <div className="text-sm font-bold tracking-tight leading-tight">
                      WELLBEING
                    </div>
                  </div>
                </div>

                {/* Navigation Sections */}
                <div className="flex md:flex-col gap-1 overflow-x-auto no-scrollbar py-1">
                  {navSections.map((sec, idx) => (
                    <div key={idx} className="space-y-1 w-full shrink-0">
                      <div className="hidden md:block px-3 pt-3 pb-1 text-[10px] font-mono tracking-widest uppercase opacity-45 font-semibold">
                        {sec.title}
                      </div>
                      <div className="flex md:flex-col gap-1">
                        {sec.items.map((item) => {
                          const Icon = item.icon
                          const isActive = activePage === item.id
                          return (
                            <button
                              key={item.id}
                              onClick={() => setActivePage(item.id)}
                              className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-200 cursor-pointer whitespace-nowrap ${
                                isActive
                                  ? isDark
                                    ? "bg-white/10 text-white font-semibold shadow-inner border border-white/10"
                                    : "bg-white text-slate-900 font-bold shadow-sm border border-slate-200"
                                  : isDark
                                  ? "text-slate-400 hover:text-white hover:bg-white/5"
                                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/60"
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <Icon className={`w-4 h-4 ${isActive ? "text-dw-emerald" : ""}`} />
                                <span>{item.label}</span>
                              </div>
                              {item.badge && (
                                <span
                                  className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full uppercase tracking-wider ${
                                    item.badge === "ACTIVE"
                                      ? "bg-dw-emerald/20 text-dw-emerald"
                                      : item.badge === "SafeBrowse"
                                      ? "bg-indigo-500/20 text-indigo-400"
                                      : isDark
                                      ? "bg-white/10 text-slate-300"
                                      : "bg-slate-200 text-slate-700"
                                  }`}
                                >
                                  {item.badge}
                                </span>
                              )}
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sidebar Footer info */}
              <div className="hidden md:block px-3 py-2 border-t border-inherit text-[10px] font-mono opacity-50 space-y-1">
                <div className="flex items-center justify-between">
                  <span>SQLite</span>
                  <span className="text-dw-emerald">Local Only</span>
                </div>
                <div>Memory: 22.4 MB</div>
              </div>
            </aside>

            {/* --- RIGHT CONTENT AREA --- */}
            <main className="flex-1 p-4 md:p-6 overflow-y-auto max-h-[720px] select-text">
              <AnimatePresence mode="wait">
                
                {/* ==========================================
                    PAGE 0: HOME / DASHBOARD
                ========================================== */}
                {activePage === "home" && (
                  <motion.div
                    key="home"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    {/* Welcome Banner */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          Good Afternoon, {userName}
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Friday, October 23 · Today's Screen Time Summary
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          setActivePage("focus")
                          setIsFocusing(true)
                        }}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-dw-emerald text-black text-xs font-bold hover:bg-dw-emerald/90 shadow-md glow-emerald transition-all cursor-pointer self-start sm:self-auto"
                      >
                        <Zap className="w-3.5 h-3.5 fill-current" />
                        <span>Start 25m Focus Sprint</span>
                      </button>
                    </div>

                    {/* Primary Hero Metric Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className={`p-4 rounded-2xl border ${cardBg}`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Total Screen Time
                        </span>
                        <div className="text-3xl font-bold mt-1 text-dw-emerald">3h 48m</div>
                        <div className="text-[11px] mt-1 font-mono text-emerald-500 flex items-center gap-1">
                          <span>↓ 18% less than yesterday</span>
                        </div>
                      </div>

                      <div className={`p-4 rounded-2xl border ${cardBg}`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Focus Sprint Time
                        </span>
                        <div className="text-3xl font-bold mt-1">1h 35m</div>
                        <div className={`text-[11px] mt-1 font-mono ${subText}`}>
                          3 uninterrupted blocks
                        </div>
                      </div>

                      <div className={`p-4 rounded-2xl border ${cardBg}`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Protected Limits
                        </span>
                        <div className="text-3xl font-bold mt-1 text-dw-amber">1 Active</div>
                        <div className={`text-[11px] mt-1 font-mono ${subText}`}>
                          Discord.exe near quota
                        </div>
                      </div>
                    </div>

                    {/* Top Used Apps List */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-4`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Most Used Applications Today
                        </span>
                        <button
                          onClick={() => setActivePage("usage")}
                          className="text-[11px] text-dw-emerald hover:underline cursor-pointer font-mono"
                        >
                          View Full Breakdown →
                        </button>
                      </div>

                      <div className="space-y-3">
                        {/* App 1: VS Code */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-blue-500" />
                              Visual Studio Code
                            </span>
                            <span className="font-mono">1h 52m (50%)</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: "50%" }} />
                          </div>
                        </div>

                        {/* App 2: Chrome */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-amber-500" />
                              Google Chrome
                            </span>
                            <span className="font-mono">58m (26%)</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                            <div className="h-full bg-amber-500 rounded-full" style={{ width: "26%" }} />
                          </div>
                        </div>

                        {/* App 3: Discord */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-indigo-500" />
                              Discord.exe
                              <span className="text-[10px] font-mono px-1.5 rounded bg-dw-amber/20 text-dw-amber">
                                Limit: 45m
                              </span>
                            </span>
                            <span className="font-mono text-dw-amber">{discordUsed}m / {discordLimit}m</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                            <div
                              className="h-full bg-dw-amber rounded-full"
                              style={{ width: `${Math.min(100, (discordUsed / discordLimit) * 100)}%` }}
                            />
                          </div>
                        </div>

                        {/* App 4: Windows Terminal */}
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs font-medium">
                            <span className="flex items-center gap-2">
                              <span className="w-2 h-2 rounded-full bg-emerald-500" />
                              Windows Terminal
                            </span>
                            <span className="font-mono">24m (11%)</span>
                          </div>
                          <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                            <div className="h-full bg-emerald-500 rounded-full" style={{ width: "11%" }} />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Quick Protection Status Bar */}
                    <div className="p-3 rounded-xl bg-dw-emerald/10 border border-dw-emerald/20 flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-dw-emerald shrink-0" />
                        <span>SafeBrowse & Process Interceptor: All rules operational.</span>
                      </div>
                      <span className="font-mono text-[11px] text-dw-emerald font-semibold hidden sm:inline">
                        Win32 Native Hook
                      </span>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 1: USAGE / ACTIVITY
                ========================================== */}
                {activePage === "usage" && (
                  <motion.div
                    key="usage"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          Hourly Intensity &amp; Distribution
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Detailed foreground window activity logged locally
                        </p>
                      </div>

                      {/* Timeframe Filter Buttons */}
                      <div className={`inline-flex p-1 rounded-xl border ${accentBorder} ${cardBg}`}>
                        {(["today", "7d", "30d"] as const).map((tf) => (
                          <button
                            key={tf}
                            onClick={() => setSelectedUsageTimeframe(tf)}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition-all cursor-pointer ${
                              selectedUsageTimeframe === tf
                                ? isDark
                                  ? "bg-white/15 text-white shadow-xs"
                                  : "bg-slate-200 text-slate-900"
                                : subText
                            }`}
                          >
                            {tf === "today" ? "Today" : tf === "7d" ? "7 Days" : "30 Days"}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Interactive 24-Hour Intensity Chart */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-4`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider">
                          24-Hour Timeline Intensity
                        </span>
                        <span className="text-xs font-mono text-dw-emerald font-semibold">
                          Selected Hour: {hourlyData[activeHourlyIndex].hour} ({hourlyData[activeHourlyIndex].mins}m active)
                        </span>
                      </div>

                      {/* Bar columns */}
                      <div className="flex items-end justify-between gap-1 h-36 pt-4 pb-1 border-b border-inherit">
                        {hourlyData.map((item, idx) => {
                          const isHovered = activeHourlyIndex === idx
                          const heightPct = Math.max(6, (item.mins / 60) * 100)
                          return (
                            <div
                              key={idx}
                              onClick={() => setActiveHourlyIndex(idx)}
                              onMouseEnter={() => setActiveHourlyIndex(idx)}
                              className="flex-1 h-full flex flex-col justify-end items-center group cursor-pointer relative"
                            >
                              <div
                                className={`w-full rounded-t transition-all duration-150 ${
                                  isHovered
                                    ? "bg-dw-emerald"
                                    : item.mins > 30
                                    ? "bg-emerald-500/80 hover:bg-emerald-500"
                                    : item.mins > 0
                                    ? isDark
                                      ? "bg-white/20 hover:bg-white/40"
                                      : "bg-slate-300 hover:bg-slate-400"
                                    : isDark
                                    ? "bg-white/5"
                                    : "bg-slate-100"
                                }`}
                                style={{ height: `${heightPct}%` }}
                              />
                            </div>
                          )
                        })}
                      </div>

                      <div className={`flex justify-between text-[10px] font-mono ${subText}`}>
                        <span>12 AM</span>
                        <span>4 AM</span>
                        <span>8 AM</span>
                        <span>12 PM</span>
                        <span>4 PM</span>
                        <span>8 PM</span>
                        <span>11 PM</span>
                      </div>
                    </div>

                    {/* Category Breakdown Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className={`p-4 rounded-xl border ${cardBg}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold">Productivity</span>
                          <span className="text-xs font-mono text-dw-emerald font-bold">62%</span>
                        </div>
                        <div className={`text-xs mt-1 ${subText}`}>VS Code, Obsidian, Excel</div>
                      </div>

                      <div className={`p-4 rounded-xl border ${cardBg}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold">Communication</span>
                          <span className="text-xs font-mono text-indigo-400 font-bold">24%</span>
                        </div>
                        <div className={`text-xs mt-1 ${subText}`}>Slack, Telegram, Teams</div>
                      </div>

                      <div className={`p-4 rounded-xl border ${cardBg}`}>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold">Entertainment</span>
                          <span className="text-xs font-mono text-amber-500 font-bold">14%</span>
                        </div>
                        <div className={`text-xs mt-1 ${subText}`}>Spotify, Discord, Steam</div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 2: WEBSITES / SAFEBROWSE
                ========================================== */}
                {activePage === "websites" && (
                  <motion.div
                    key="websites"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          Websites &amp; SafeBrowse Protection
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Cross-browser website blocking without slow extensions
                        </p>
                      </div>

                      {/* Master SafeBrowse Toggle */}
                      <button
                        onClick={() => setSafeBrowseEnabled(!safeBrowseEnabled)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                          safeBrowseEnabled
                            ? "bg-dw-emerald text-black shadow-md glow-emerald"
                            : isDark
                            ? "bg-white/10 text-slate-400"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        <ShieldCheck className="w-4 h-4" />
                        <span>SafeBrowse: {safeBrowseEnabled ? "ENABLED" : "PAUSED"}</span>
                      </button>
                    </div>

                    {/* Add Custom Domain Input */}
                    <div className={`p-4 rounded-2xl border ${cardBg} flex flex-col sm:flex-row gap-2`}>
                      <input
                        type="text"
                        placeholder="Enter domain to block (e.g., reddit.com, twitch.tv)"
                        value={newDomain}
                        onChange={(e) => setNewDomain(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleAddDomain()}
                        className={`flex-1 px-3.5 py-2 rounded-xl text-xs font-mono outline-none border ${
                          isDark
                            ? "bg-black/30 border-white/10 text-white focus:border-dw-emerald"
                            : "bg-slate-50 border-slate-300 text-slate-900 focus:border-dw-emerald"
                        }`}
                      />
                      <button
                        onClick={handleAddDomain}
                        className="px-4 py-2 rounded-xl bg-dw-emerald text-black text-xs font-bold hover:bg-dw-emerald/90 transition-all cursor-pointer flex items-center justify-center gap-1.5"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Block</span>
                      </button>
                    </div>

                    {/* Blocked Domains List */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Distraction Blocklist ({blockedDomains.length} domains)
                        </span>
                        <span className={`text-[11px] font-mono ${subText}`}>
                          Enforced via Windows DNS / Hosts filter
                        </span>
                      </div>

                      <div className="space-y-2">
                        {blockedDomains.map((domain) => (
                          <div
                            key={domain}
                            className={`flex items-center justify-between p-2.5 px-3 rounded-xl border ${accentBorder} ${
                              isDark ? "bg-white/[0.02]" : "bg-slate-50"
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <Globe className="w-4 h-4 text-dw-emerald" />
                              <span className="text-xs font-mono font-medium">{domain}</span>
                            </div>
                            <button
                              onClick={() => setBlockedDomains(blockedDomains.filter((d) => d !== domain))}
                              className="p-1 rounded-lg hover:bg-red-500/10 text-slate-400 hover:text-red-500 transition-colors cursor-pointer"
                              title="Remove domain"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 3: INSIGHTS
                ========================================== */}
                {activePage === "insights" && (
                  <motion.div
                    key="insights"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div>
                      <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                        Foreground Intelligence &amp; Analytics
                      </h2>
                      <p className={`text-xs ${subText} font-mono mt-0.5`}>
                        Pure telemetry-free usage statistics derived from local Win32 events
                      </p>
                    </div>

                    {/* Key Ratios */}
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div className={`p-4 rounded-2xl border ${cardBg} text-center sm:text-left`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Focus Ratio
                        </span>
                        <div className="text-3xl font-bold mt-1 text-dw-emerald">82%</div>
                        <div className="text-[11px] text-emerald-500 font-mono mt-1">
                          +7% increase this week
                        </div>
                      </div>

                      <div className={`p-4 rounded-2xl border ${cardBg} text-center sm:text-left`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Peak Deep Work Window
                        </span>
                        <div className="text-2xl font-bold mt-1">10 AM – 1 PM</div>
                        <div className={`text-[11px] font-mono ${subText} mt-1`}>
                          Lowest context switches
                        </div>
                      </div>

                      <div className={`p-4 rounded-2xl border ${cardBg} text-center sm:text-left`}>
                        <span className={`text-[11px] font-mono uppercase tracking-wider ${subText}`}>
                          Distraction Deflections
                        </span>
                        <div className="text-3xl font-bold mt-1 text-dw-amber">18</div>
                        <div className={`text-[11px] font-mono ${subText} mt-1`}>
                          Habitual loops intercepted
                        </div>
                      </div>
                    </div>

                    {/* Weekly Screen Time Comparison */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Weekly Focus Consistency
                      </span>
                      <div className="grid grid-cols-7 gap-2 pt-2 text-center">
                        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day, idx) => {
                          const hours = [4.2, 5.1, 4.8, 3.9, 3.8, 2.1, 1.5][idx]
                          return (
                            <div key={day} className="space-y-1">
                              <div className="h-24 flex items-end justify-center">
                                <div
                                  className="w-full max-w-[28px] rounded-t bg-dw-emerald/80 transition-all"
                                  style={{ height: `${(hours / 6) * 100}%` }}
                                />
                              </div>
                              <div className="text-[11px] font-mono font-bold">{hours}h</div>
                              <div className={`text-[10px] ${subText}`}>{day}</div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 4: FOCUS MODE
                ========================================== */}
                {activePage === "focus" && (
                  <motion.div
                    key="focus"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          Focus Mode &amp; Allowlisting
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Mechanical distraction prevention at the Windows process level
                        </p>
                      </div>

                      {/* Status indicator */}
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-mono font-bold self-start sm:self-auto ${
                          isFocusing
                            ? "bg-dw-emerald/20 text-dw-emerald border border-dw-emerald/40 animate-pulse"
                            : isDark
                            ? "bg-white/10 text-slate-300"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {isFocusing ? "ENFORCEMENT ACTIVE" : "STANDBY"}
                      </span>
                    </div>

                    {/* Central Focus Timer Card */}
                    <div className={`p-6 rounded-2xl border ${cardBg} text-center space-y-4`}>
                      {/* Profile Selectors */}
                      <div className="inline-flex items-center gap-1.5 p-1 rounded-xl bg-black/10 dark:bg-white/5">
                        {(["deep", "work", "study", "reading"] as const).map((prf) => (
                          <button
                            key={prf}
                            onClick={() => {
                              setFocusProfile(prf)
                              setFocusSeconds(prf === "deep" ? 50 * 60 : 25 * 60)
                            }}
                            className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize cursor-pointer transition-all ${
                              focusProfile === prf
                                ? "bg-dw-emerald text-black shadow-sm font-bold"
                                : subText
                            }`}
                          >
                            {prf} Focus
                          </button>
                        ))}
                      </div>

                      {/* Big Monospace Clock */}
                      <div className="text-5xl md:text-6xl font-mono font-bold tracking-wider py-2 text-dw-emerald">
                        {formatTimer(focusSeconds)}
                      </div>

                      {/* Controls */}
                      <div className="flex items-center justify-center gap-3">
                        <button
                          onClick={() => setIsFocusing(!isFocusing)}
                          className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                            isFocusing
                              ? "bg-amber-500 text-black hover:bg-amber-400"
                              : "bg-dw-emerald text-black hover:bg-dw-emerald/90 shadow-lg glow-emerald"
                          }`}
                        >
                          {isFocusing ? (
                            <>
                              <Pause className="w-4 h-4 fill-current" />
                              <span>Pause Sprint</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-4 h-4 fill-current" />
                              <span>Start Focus Sprint</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setIsFocusing(false)
                            setFocusSeconds(25 * 60)
                          }}
                          className={`p-2.5 rounded-full border ${accentBorder} hover:bg-white/10 transition-colors cursor-pointer`}
                          title="Reset Timer"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Active Allowlist */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Allowed Applications ({allowlist.length})
                        </span>
                        <span className={`text-[11px] font-mono ${subText}`}>
                          All other background processes suspended
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {allowlist.map((app) => (
                          <span
                            key={app}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border ${accentBorder} text-xs font-mono font-medium ${
                              isDark ? "bg-white/[0.04]" : "bg-slate-100"
                            }`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5 text-dw-emerald" />
                            <span>{app}</span>
                            <button
                              onClick={() => setAllowlist(allowlist.filter((a) => a !== app))}
                              className="ml-1 text-slate-400 hover:text-red-400 cursor-pointer"
                            >
                              ×
                            </button>
                          </span>
                        ))}
                      </div>

                      {/* Add app input */}
                      <div className="flex gap-2 pt-2">
                        <input
                          type="text"
                          placeholder="Add executable (e.g., Notion.exe)"
                          value={newAllowApp}
                          onChange={(e) => setNewAllowApp(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && newAllowApp.trim()) {
                              setAllowlist([...allowlist, newAllowApp.trim()])
                              setNewAllowApp("")
                            }
                          }}
                          className={`px-3 py-1.5 rounded-xl text-xs font-mono outline-none border ${
                            isDark
                              ? "bg-black/30 border-white/10 text-white"
                              : "bg-slate-50 border-slate-300 text-slate-900"
                          }`}
                        />
                        <button
                          onClick={() => {
                            if (newAllowApp.trim()) {
                              setAllowlist([...allowlist, newAllowApp.trim()])
                              setNewAllowApp("")
                            }
                          }}
                          className="px-3 py-1.5 rounded-xl bg-dw-emerald text-black text-xs font-bold cursor-pointer"
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 5: APP TIMER
                ========================================== */}
                {activePage === "timer" && (
                  <motion.div
                    key="timer"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div>
                      <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                        App Timer &amp; Daily Quotas
                      </h2>
                      <p className={`text-xs ${subText} font-mono mt-0.5`}>
                        Proactive limits that gracefully pause apps when allowances are reached
                      </p>
                    </div>

                    <div className="space-y-4">
                      {/* App 1: Discord */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-bold">Discord.exe</div>
                            <div className={`text-xs ${subText} font-mono`}>Social &amp; Gaming Communities</div>
                          </div>
                          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-amber/20 text-dw-amber font-bold">
                            {discordUsed}m / {discordLimit}m Used
                          </span>
                        </div>

                        {/* Slider */}
                        <div className="space-y-1">
                          <div className={`flex justify-between text-xs font-mono ${subText}`}>
                            <span>Daily Limit: {discordLimit} minutes</span>
                            <span>{discordUsed >= discordLimit ? "Limit Reached" : `${discordLimit - discordUsed}m remaining`}</span>
                          </div>
                          <input
                            type="range"
                            min="15"
                            max="120"
                            step="5"
                            value={discordLimit}
                            onChange={(e) => setDiscordLimit(Number(e.target.value))}
                            className="w-full accent-dw-amber cursor-pointer"
                          />
                        </div>

                        {/* Presets */}
                        <div className="flex gap-2">
                          {[15, 30, 45, 60, 90].map((preset) => (
                            <button
                              key={preset}
                              onClick={() => setDiscordLimit(preset)}
                              className={`px-2.5 py-1 rounded-lg text-[11px] font-mono transition-all cursor-pointer ${
                                discordLimit === preset
                                  ? "bg-dw-amber text-black font-bold"
                                  : isDark
                                  ? "bg-white/5 text-slate-300 hover:bg-white/10"
                                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                              }`}
                            >
                              {preset}m
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* App 2: Steam */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-bold">Steam.exe</div>
                            <div className={`text-xs ${subText} font-mono`}>Game launcher &amp; Store</div>
                          </div>
                          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 font-bold">
                            Quota Exceeded · Suspended
                          </span>
                        </div>

                        <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                          <div className="h-full bg-red-500 rounded-full" style={{ width: "100%" }} />
                        </div>
                        <div className={`text-[11px] font-mono ${subText}`}>
                          Daily limit of {steamLimit}m was reached at 2:15 PM.
                        </div>
                      </div>

                      {/* App 3: Spotify */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <div className="flex items-center justify-between">
                          <div>
                            <div className="text-sm font-bold">Spotify.exe</div>
                            <div className={`text-xs ${subText} font-mono`}>Music Streaming</div>
                          </div>
                          <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-dw-emerald/20 text-dw-emerald font-bold">
                            {spotifyUsed}m / {spotifyLimit}m
                          </span>
                        </div>

                        <div className="w-full h-2 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-dw-emerald rounded-full"
                            style={{ width: `${(spotifyUsed / spotifyLimit) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 6: APP LOCKER
                ========================================== */}
                {activePage === "locker" && (
                  <motion.div
                    key="locker"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          App Locker &amp; Windows Hello Gate
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Biometric authentication intercepting protected software
                        </p>
                      </div>

                      <span
                        className={`px-3 py-1 rounded-full text-xs font-mono font-bold self-start sm:self-auto ${
                          isLockerAuthenticated
                            ? "bg-dw-emerald/20 text-dw-emerald"
                            : "bg-dw-amber/20 text-dw-amber"
                        }`}
                      >
                        {isLockerAuthenticated ? "GATE UNLOCKED" : "AUTHENTICATION REQUIRED"}
                      </span>
                    </div>

                    {/* Authentication Sandbox */}
                    <div className={`p-6 rounded-2xl border ${cardBg} max-w-md mx-auto text-center space-y-4`}>
                      <div className="w-12 h-12 rounded-full mx-auto flex items-center justify-center bg-black/10 dark:bg-white/5 border border-inherit">
                        {isLockerAuthenticated ? (
                          <Unlock className="w-6 h-6 text-dw-emerald" />
                        ) : (
                          <Lock className="w-6 h-6 text-dw-amber" />
                        )}
                      </div>

                      <div>
                        <div className="text-sm font-bold">
                          {isLockerAuthenticated ? "Access Granted" : "Protected Process Intercepted"}
                        </div>
                        <div className={`text-xs ${subText} mt-1`}>
                          {isLockerAuthenticated
                            ? "Protected apps can now launch without restriction."
                            : "Enter sample PIN (1234) or simulate Windows Hello."}
                        </div>
                      </div>

                      {!isLockerAuthenticated ? (
                        <div className="space-y-4">
                          {/* PIN display dots */}
                          <div className="flex justify-center gap-3 py-2">
                            {[0, 1, 2, 3].map((idx) => (
                              <div
                                key={idx}
                                className={`w-3.5 h-3.5 rounded-full border ${
                                  pinInput.length > idx
                                    ? "bg-dw-emerald border-dw-emerald"
                                    : "border-slate-400 dark:border-white/20"
                                }`}
                              />
                            ))}
                          </div>

                          {authError && (
                            <div className="text-xs text-red-500 font-mono">Incorrect PIN. Try 1234.</div>
                          )}

                          {/* Keypad */}
                          <div className="grid grid-cols-3 gap-2 max-w-[200px] mx-auto">
                            {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((num) => (
                              <button
                                key={num}
                                onClick={() => handlePinDigit(num)}
                                className={`h-10 rounded-xl font-mono text-sm font-semibold transition-all cursor-pointer ${
                                  isDark
                                    ? "bg-white/5 hover:bg-white/10 text-white"
                                    : "bg-slate-100 hover:bg-slate-200 text-slate-900"
                                }`}
                              >
                                {num}
                              </button>
                            ))}
                            <button
                              onClick={() => setPinInput("")}
                              className={`h-10 rounded-xl font-mono text-xs ${
                                isDark ? "text-slate-400" : "text-slate-500"
                              }`}
                            >
                              Clear
                            </button>
                            <button
                              onClick={() => handlePinDigit("0")}
                              className={`h-10 rounded-xl font-mono text-sm font-semibold ${
                                isDark
                                  ? "bg-white/5 hover:bg-white/10 text-white"
                                  : "bg-slate-100 hover:bg-slate-200 text-slate-900"
                              }`}
                            >
                              0
                            </button>
                            <button
                              onClick={() => setPinInput(pinInput.slice(0, -1))}
                              className={`h-10 rounded-xl font-mono text-xs ${
                                isDark ? "text-slate-400" : "text-slate-500"
                              }`}
                            >
                              ⌫
                            </button>
                          </div>

                          {/* Windows Hello Simulator */}
                          <div className="pt-2">
                            <button
                              onClick={() => setIsLockerAuthenticated(true)}
                              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-dw-emerald text-black text-xs font-bold hover:bg-dw-emerald/90 transition-all cursor-pointer shadow-md glow-emerald"
                            >
                              <Fingerprint className="w-4 h-4" />
                              <span>Simulate Windows Hello (Biometric)</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="p-3 rounded-xl bg-dw-emerald/10 border border-dw-emerald/30 text-xs text-dw-emerald font-semibold">
                            Biometric validation verified via Win32 Credential API.
                          </div>
                          <button
                            onClick={() => setIsLockerAuthenticated(false)}
                            className="px-4 py-2 rounded-xl bg-black/10 dark:bg-white/10 text-xs font-semibold hover:opacity-80 transition-opacity cursor-pointer"
                          >
                            Re-lock Gate
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Locked apps list */}
                    <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                      <span className="text-xs font-bold uppercase tracking-wider">
                        Protected Applications ({lockedApps.length})
                      </span>
                      <div className="space-y-2">
                        {lockedApps.map((app) => (
                          <div
                            key={app.name}
                            className={`flex items-center justify-between p-3 rounded-xl border ${accentBorder} ${
                              isDark ? "bg-white/[0.02]" : "bg-slate-50"
                            }`}
                          >
                            <div>
                              <div className="text-xs font-bold font-mono">{app.name}</div>
                              <div className={`text-[11px] ${subText}`}>{app.desc}</div>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-dw-emerald/15 text-dw-emerald font-semibold">
                              INTERCEPT ON LAUNCH
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 7: SLEEPGUARD
                ========================================== */}
                {activePage === "sleepguard" && (
                  <motion.div
                    key="sleepguard"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                          Circadian SleepGuard
                        </h2>
                        <p className={`text-xs ${subText} font-mono mt-0.5`}>
                          Automatic bedtime suspension to prevent passive late-night bingeing
                        </p>
                      </div>

                      <button
                        onClick={() => setSleepGuardActive(!sleepGuardActive)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                          sleepGuardActive
                            ? "bg-indigo-600 text-white shadow-md"
                            : isDark
                            ? "bg-white/10 text-slate-400"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        <Moon className="w-4 h-4" />
                        <span>SleepGuard: {sleepGuardActive ? "ACTIVE" : "OFF"}</span>
                      </button>
                    </div>

                    {/* Schedule & Action Picker */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Circadian Bedtime Window
                        </span>
                        <div className="flex items-center justify-between p-3 rounded-xl border border-inherit">
                          <span className="text-xs font-semibold">Active Hours:</span>
                          <span className="text-xs font-mono text-indigo-400 font-bold">
                            11:00 PM – 06:00 AM
                          </span>
                        </div>
                        <div className={`text-[11px] ${subText}`}>
                          If inactivity exceeds 15 minutes during this window, a graceful countdown begins.
                        </div>
                      </div>

                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Power Action
                        </span>
                        <div className="flex gap-2">
                          {(["sleep", "lock", "hibernate"] as const).map((act) => (
                            <button
                              key={act}
                              onClick={() => setSleepGuardAction(act)}
                              className={`flex-1 py-2 rounded-xl text-xs font-semibold capitalize transition-all cursor-pointer ${
                                sleepGuardAction === act
                                  ? "bg-indigo-600 text-white font-bold"
                                  : isDark
                                  ? "bg-white/5 text-slate-300"
                                  : "bg-slate-100 text-slate-700"
                              }`}
                            >
                              {act}
                            </button>
                          ))}
                        </div>
                        <div className={`text-[11px] ${subText}`}>
                          Windows will safely {sleepGuardAction} the computer.
                        </div>
                      </div>
                    </div>

                    {/* Test Warning Dialog Trigger */}
                    <div className={`p-5 rounded-2xl border ${cardBg} flex flex-col sm:flex-row items-center justify-between gap-4`}>
                      <div>
                        <div className="text-sm font-bold flex items-center gap-2">
                          <Bell className="w-4 h-4 text-indigo-500" />
                          <span>Simulate Bedtime Countdown Warning</span>
                        </div>
                        <div className={`text-xs ${subText} mt-1`}>
                          Triggers the exact 60-second audio-visual warning modal users see before sleep.
                        </div>
                      </div>

                      <button
                        onClick={() => {
                          setModalCountdown(60)
                          setShowCountdownModal(true)
                        }}
                        className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all cursor-pointer shrink-0 shadow-md"
                      >
                        Launch Countdown Dialog
                      </button>
                    </div>

                    {/* Interactive Modal Preview */}
                    <AnimatePresence>
                      {showCountdownModal && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.95 }}
                          className="p-6 rounded-2xl bg-indigo-950/80 border border-indigo-500/30 text-white space-y-4 shadow-2xl relative"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono font-bold tracking-widest text-indigo-300 uppercase flex items-center gap-2">
                              <Moon className="w-4 h-4 text-indigo-300 animate-pulse" />
                              SleepGuard Countdown Active
                            </span>
                            <span className="text-2xl font-mono font-bold text-dw-amber">
                              {modalCountdown}s
                            </span>
                          </div>

                          <p className="text-xs text-indigo-200 leading-relaxed">
                            Inactivity was verified past your 11:00 PM circadian schedule. Your machine will enter {sleepGuardAction} mode in {modalCountdown} seconds.
                          </p>

                          <div className="flex justify-end gap-3 pt-2">
                            <button
                              onClick={() => setShowCountdownModal(false)}
                              className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold cursor-pointer"
                            >
                              Cancel &amp; Continue Working
                            </button>
                            <button
                              onClick={() => {
                                setShowCountdownModal(false)
                                alert("Simulated: Windows received power state command.")
                              }}
                              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold cursor-pointer"
                            >
                              {sleepGuardAction === "sleep" ? "Sleep Now" : "Execute Action"}
                            </button>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )}

                {/* ==========================================
                    PAGE 8: SETTINGS
                ========================================== */}
                {activePage === "settings" && (
                  <motion.div
                    key="settings"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    transition={{ duration: 0.2 }}
                    className="space-y-6 text-left"
                  >
                    <div>
                      <h2 className="text-xl md:text-2xl font-bold tracking-tight">
                        Settings &amp; Local Preferences
                      </h2>
                      <p className={`text-xs ${subText} font-mono mt-0.5`}>
                        Preferences stored strictly on your local NVMe/SSD
                      </p>
                    </div>

                    <div className="space-y-4">
                      {/* Personalization */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Display Name
                        </span>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={userName}
                            onChange={(e) => setUserName(e.target.value)}
                            className={`flex-1 px-3.5 py-2 rounded-xl text-xs font-medium outline-none border ${
                              isDark
                                ? "bg-black/30 border-white/10 text-white focus:border-dw-emerald"
                                : "bg-slate-50 border-slate-300 text-slate-900 focus:border-dw-emerald"
                            }`}
                          />
                        </div>
                        <div className={`text-[11px] ${subText}`}>
                          Updates greeting dynamically across the dashboard.
                        </div>
                      </div>

                      {/* Theme Selection */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-3`}>
                        <span className="text-xs font-bold uppercase tracking-wider">
                          App Theme (Aurora Design Tokens)
                        </span>
                        <div className="flex gap-3">
                          <button
                            onClick={() => setAppTheme("dark")}
                            className={`flex-1 p-3 rounded-xl border flex items-center justify-center gap-2 text-xs font-bold transition-all cursor-pointer ${
                              isDark
                                ? "bg-white/15 border-white/30 text-white shadow-sm"
                                : "border-slate-200 text-slate-600 hover:bg-slate-100"
                            }`}
                          >
                            <Moon className="w-4 h-4 text-indigo-400" />
                            <span>Aurora Dark</span>
                          </button>
                          <button
                            onClick={() => setAppTheme("light")}
                            className={`flex-1 p-3 rounded-xl border flex items-center justify-center gap-2 text-xs font-bold transition-all cursor-pointer ${
                              !isDark
                                ? "bg-dw-emerald/15 border-dw-emerald/30 text-dw-emerald-dark font-bold shadow-sm"
                                : "border-white/10 text-slate-400 hover:bg-white/5"
                            }`}
                          >
                            <Sun className="w-4 h-4 text-dw-amber" />
                            <span>Aurora Light</span>
                          </button>
                        </div>
                      </div>

                      {/* Storage Info */}
                      <div className={`p-4 md:p-5 rounded-2xl border ${cardBg} space-y-2 font-mono text-xs`}>
                        <span className="font-bold uppercase tracking-wider text-dw-emerald">
                          Database &amp; Local Privacy Status
                        </span>
                        <div className={subText}>Path: ~/.digital_wellbeing/digital_wellbeing.db</div>
                        <div className={subText}>Engine: SQLite 3 (WAL mode enabled)</div>
                        <div className={subText}>Outbound telemetry sockets: 0</div>
                        <div className="text-dw-emerald pt-1">
                          ✓ 100% Offline &amp; Independent
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

              </AnimatePresence>
            </main>
          </div>

          {/* Window Footer / Status Line */}
          <div className={`h-8 px-4 border-t ${accentBorder} ${isDark ? "bg-[#070a0e]" : "bg-slate-100"} flex items-center justify-between text-[11px] font-mono ${subText}`}>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-dw-emerald" />
              <span>Digital Wellbeing v4.2.0 · PySide6 Native Engine</span>
            </div>
            <span className="hidden sm:inline">Click any sidebar tab above to test features</span>
          </div>

        </div>
      </div>
    </div>
  )
}
