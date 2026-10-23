"use client"
import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Users, DownloadCloud } from "lucide-react"

export function StatsDisplay() {
  const [stats, setStats] = useState<{ downloads: number, activeInstalls: number, version: string } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        if (!data.error) {
          setStats(data)
        }
        setLoading(false)
      })
      .catch(err => {
        console.error("Failed to load stats:", err)
        setLoading(false)
      })
  }, [])

  const formatNumber = (num: number) => {
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num.toString()
  }

  if (loading || !stats) {
    return (
      <div className="flex flex-col sm:flex-row items-center justify-center gap-6 mt-12 opacity-0">
        {/* Placeholder to prevent layout shift */}
        <div className="h-16 w-32"></div>
      </div>
    )
  }

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="flex flex-col sm:flex-row items-center justify-center gap-8 mt-12 mb-4"
    >
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2 text-3xl font-black text-foreground">
          <DownloadCloud className="w-6 h-6 text-accent" />
          <span>{formatNumber(stats.downloads)}</span>
        </div>
        <span className="text-sm font-medium text-foreground/60">Downloads</span>
      </div>

      <div className="hidden sm:block h-10 w-px bg-border/50"></div>

      <div className="flex flex-col items-center">
        <div className="flex items-center gap-2 text-3xl font-black text-foreground">
          <Users className="w-6 h-6 text-accent" />
          <span>{formatNumber(stats.activeInstalls)}</span>
        </div>
        <span className="text-sm font-medium text-foreground/60">Active installations</span>
      </div>
    </motion.div>
  )
}
