import { ImageResponse } from "next/og"
import { site } from "@/data/site"

export const alt = "Digital Wellbeing for Windows: a foreground ledger of applications and time"
export const size = { width: 1200, height: 630 }
export const contentType = "image/png"

/**
 * The Open Graph card is the site's own instrument: the ledger on the right,
 * the claim on the left, on the same paper colour as the page.
 */
export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#f4f4f1",
          color: "#101418",
          fontFamily: "sans-serif",
          padding: 56,
          gap: 40,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", width: 560 }}>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 18, letterSpacing: 2, color: "#4d5854" }}>
              <div style={{ width: 9, height: 9, borderRadius: 9, background: "#067a58" }} />
              WINDOWS 10 AND 11, 64-BIT
            </div>
            <div style={{ display: "flex", flexDirection: "column", marginTop: 28, fontSize: 62, fontWeight: 700, lineHeight: 0.98, letterSpacing: -2.5 }}>
              <span>Control your machine.</span>
              <span style={{ color: "#4d5854" }}>Not the other way around.</span>
            </div>
            <div style={{ display: "flex", marginTop: 26, fontSize: 21, lineHeight: 1.45, color: "#3a4442" }}>
              Screen time that acts: focus sessions, daily quotas, biometric locks. All local.
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 17, color: "#4d5854" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 3.5, width: 26 }}>
              <div style={{ display: "flex", height: 4, borderRadius: 2, background: "#101418" }} />
              <div style={{ display: "flex", height: 4, borderRadius: 2, background: "#8f9995", width: "62%" }} />
              <div style={{ display: "flex", height: 4, borderRadius: 2, background: "#067a58" }} />
            </div>
            <span>{site.name} · v{site.version} · {site.license}</span>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", flex: 1, background: "#ffffff", border: "1px solid #d8d8d2", borderRadius: 18, overflow: "hidden" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 22px", borderBottom: "1px solid #e6e6e0", fontSize: 15, letterSpacing: 1.5, color: "#4d5854" }}>
            <span>FOREGROUND LEDGER</span>
            <span>LIVE · 2.0 S TICK</span>
          </div>
          {[
            ["14:02:10", "Code.exe", "machine.tsx", "#067a58", "#101418"],
            ["14:05:02", "chrome.exe", "nextjs.org", "#067a58", "#101418"],
            ["14:07:31", "Discord.exe", "quota 45 of 45 m, suspended", "#c2371a", "#c2371a"],
            ["14:08:02", "Idle", "no input for 4m 12s", "#9aa7b4", "#4d5854"],
            ["14:12:18", "Obsidian.exe", "reading queue", "#067a58", "#101418"],
            ["14:15:40", "youtube.com", "hosts block", "#c2371a", "#c2371a"],
          ].map(([t, app, note, dot, noteColor]) => (
            <div key={t} style={{ display: "flex", alignItems: "center", gap: 14, padding: "13px 22px", borderBottom: "1px solid #eeeeea", fontSize: 17 }}>
              <span style={{ color: "#6b7673", width: 76, fontVariantNumeric: "tabular-nums" }}>{t}</span>
              <span style={{ width: 8, height: 8, borderRadius: 8, background: dot }} />
              <span style={{ width: 150, fontWeight: 600 }}>{app}</span>
              <span style={{ color: noteColor, fontSize: 15 }}>{note}</span>
            </div>
          ))}
          <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "18px 22px" }}>
            <span style={{ fontSize: 13, letterSpacing: 1.6, color: "#4d5854" }}>DAILY QUOTAS</span>
            {[
              ["Discord.exe", 100, "#c2371a"],
              ["Spotify.exe", 47, "#067a58"],
            ].map(([app, pct, color]) => (
              <div key={String(app)} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "#4d5854" }}>
                  <span>{app}</span>
                </div>
                <div style={{ display: "flex", height: 5, borderRadius: 4, background: "#ecece7", width: "100%" }}>
                  <div style={{ display: "flex", height: 5, borderRadius: 4, width: `${pct}%`, background: color as string }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
    size,
  )
}
