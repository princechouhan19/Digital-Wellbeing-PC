import type { Metadata, Viewport } from "next"
import localFont from "next/font/local"
import "./globals.css"
import { site } from "@/data/site"
import { Navbar } from "@/components/layout/navbar"
import { Footer } from "@/components/layout/footer"

const grotesk = localFont({
  src: "../fonts/schibsted-grotesk-latin.woff2",
  variable: "--font-grotesk",
  weight: "400 900",
  display: "swap",
  fallback: ["ui-sans-serif", "system-ui", "sans-serif"],
})

const mono = localFont({
  src: "../fonts/jetbrains-mono-latin.woff2",
  variable: "--font-jbmono",
  weight: "400 800",
  display: "swap",
  fallback: ["ui-monospace", "SFMono-Regular", "monospace"],
})

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f4f1" },
    { media: "(prefers-color-scheme: dark)", color: "#080a0d" },
  ],
  width: "device-width",
  initialScale: 1,
}

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: {
    default: "Digital Wellbeing for Windows · screen time you can act on",
    template: "%s · Digital Wellbeing",
  },
  description: site.description,
  keywords: [
    "digital wellbeing Windows",
    "Windows screen time tracker",
    "app blocker Windows",
    "app timer Windows",
    "focus mode Windows",
    "app locker Windows Hello",
    "local-first screen time",
    "SleepGuard",
    "hosts file website blocker",
  ],
  authors: [{ name: site.developer, url: site.repository }],
  creator: site.developer,
  alternates: { canonical: "/" },
  applicationName: "Digital Wellbeing",
  category: "productivity",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: site.url,
    siteName: site.name,
    title: "Digital Wellbeing for Windows · screen time you can act on",
    description: site.description,
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Digital Wellbeing for Windows: a foreground ledger of applications and time",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Digital Wellbeing for Windows",
    description: site.description,
    images: ["/opengraph-image"],
  },
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }, { url: "/logo.png", sizes: "512x512" }],
    apple: "/apple-touch-icon.png",
  },
  robots: { index: true, follow: true },
}

/** Runs before first paint: theme from storage (or the OS), motion flag for reveals. */
const bootScript = `(function(){var d=document.documentElement;try{var t=localStorage.getItem("dw-theme");if(!t){t=window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark"}d.setAttribute("data-theme",t)}catch(e){d.setAttribute("data-theme","light")}d.classList.add("js");if(window.matchMedia("(prefers-reduced-motion: no-preference)").matches){d.classList.add("motion")}})()`

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      name: site.fullName,
      alternateName: site.name,
      url: site.url,
      downloadUrl: `${site.url}/api/download`,
      installUrl: `${site.url}/api/download`,
      softwareVersion: site.version,
      operatingSystem: "Windows 10, Windows 11",
      applicationCategory: "UtilitiesApplication",
      applicationSubCategory: "Screen time and attention control",
      fileSize: "190MB",
      license: "https://opensource.org/licenses/MIT",
      sameAs: site.repository,
      author: { "@type": "Person", name: site.developer },
      description: site.description,
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD", availability: "https://schema.org/InStock" },
      featureList: [
        "Foreground application and website tracking stored in a local SQLite database",
        "Focus sessions with a process allowlist and hosts-file domain blocking",
        "Daily per-application time quotas",
        "App Locker with Windows Hello or a hashed local PIN",
        "SleepGuard bedtime inactivity handling",
        "CSV export of every recorded session",
      ],
    },
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      name: site.name,
      url: site.url,
      inLanguage: "en",
    },
  ]

  return (
    <html lang="en" data-theme="light" className={`${grotesk.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: bootScript }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <Navbar />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  )
}
