"use client"
import Link from "next/link"
import Image from "next/image"
import { siteConfig } from "@/config/site"
import { ShieldCheck, GitBranch, Code2, Bug, Sparkles, Mail } from "lucide-react"

export function Footer() {
  return (
    <footer className="border-t border-slate-200 dark:border-white/[0.06] py-16 md:py-24 bg-slate-50/80 dark:bg-[#06080a] relative overflow-hidden transition-colors duration-300">
      <div className="container mx-auto px-6 md:px-12 max-w-6xl">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-12 items-start justify-between">
          {/* Brand Info */}
          <div className="md:col-span-6 space-y-4 text-left">
            <Link href="/" className="inline-flex items-center gap-3">
              <div className="relative w-8 h-8 flex-shrink-0">
                <Image
                  src="/logo.png"
                  alt="Digital Wellbeing"
                  width={32}
                  height={32}
                  className="object-contain"
                />
              </div>
              <span className="font-bold text-base tracking-wider text-slate-900 dark:text-white">
                DIGITAL WELLBEING
              </span>
              <span className="text-[10px] uppercase font-mono tracking-widest px-2 py-0.5 rounded-full bg-slate-200/80 dark:bg-white/[0.05] text-slate-700 dark:text-foreground/60 border border-slate-300/80 dark:border-white/[0.08]">
                v{siteConfig.version} · {siteConfig.stage}
              </span>
            </Link>

            <p className="text-sm text-slate-700 dark:text-foreground/75 max-w-sm leading-relaxed">
              {siteConfig.fullName}. An intentional, minimalist digital wellbeing and attention-control system engineered for Windows 10 & 11.
            </p>

            <div className="inline-flex items-center gap-2 pt-2 text-xs font-mono text-slate-600 dark:text-foreground/65">
              <ShieldCheck className="w-4 h-4 text-dw-emerald" />
              <span>100% Local-First · Zero Cloud Sync · No Telemetry</span>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="md:col-span-3 space-y-3 text-left">
            <p className="text-xs uppercase font-mono tracking-widest text-slate-700 dark:text-foreground/70 font-semibold">
              Product
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-foreground/75">
              <li>
                <Link href="#product" className="hover:text-slate-950 dark:hover:text-white transition-colors">
                  Experience
                </Link>
              </li>
              <li>
                <Link href="#capabilities" className="hover:text-slate-950 dark:hover:text-white transition-colors">
                  Capabilities
                </Link>
              </li>
              <li>
                <Link href="#philosophy" className="hover:text-slate-950 dark:hover:text-white transition-colors">
                  Philosophy
                </Link>
              </li>
              <li>
                <Link href="#privacy" className="hover:text-slate-950 dark:hover:text-white transition-colors">
                  Privacy Declaration
                </Link>
              </li>
              <li>
                <a href="/api/download" className="text-dw-emerald hover:text-dw-emerald-dark transition-colors font-medium">
                  Download Digital Wellbeing
                </a>
              </li>
            </ul>
          </div>

          {/* Open Development */}
          <div className="md:col-span-3 space-y-3 text-left">
            <p className="text-xs uppercase font-mono tracking-widest text-slate-700 dark:text-foreground/70 font-semibold">
              Engineering
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-foreground/75">
              <li>
                <Link
                  href={siteConfig.links.github}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-slate-950 dark:hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <Code2 className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </Link>
              </li>
              <li>
                <Link
                  href={siteConfig.links.releases}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-slate-950 dark:hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>Release History</span>
                </Link>
              </li>
              <li>
                <a
                  href={siteConfig.links.reportBug}
                  className="hover:text-slate-950 dark:hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <Bug className="w-3.5 h-3.5" />
                  <span>Report a Bug</span>
                </a>
              </li>
              <li>
                <a
                  href={siteConfig.links.requestFeature}
                  className="hover:text-slate-950 dark:hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Request a Feature</span>
                </a>
              </li>
              <li>
                <a
                  href={siteConfig.links.contactSupport}
                  className="hover:text-slate-950 dark:hover:text-white transition-colors flex items-center gap-1.5"
                >
                  <Mail className="w-3.5 h-3.5" />
                  <span>Contact Support</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="mt-16 pt-8 border-t border-slate-200 dark:border-white/[0.04] flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-600 dark:text-foreground/65 font-medium">
          <p>© {new Date().getFullYear()} {siteConfig.developer}. All rights reserved.</p>
          <p className="font-mono text-[11px] flex items-center gap-1.5">
            <Mail className="w-3 h-3 flex-shrink-0" />
            <a
              href={siteConfig.links.contactSupport}
              className="hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              GitHub Issues
            </a>
          </p>
        </div>
      </div>
    </footer>
  )
}
