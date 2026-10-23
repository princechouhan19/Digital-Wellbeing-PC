import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { siteConfig } from "@/config/site"
import { Navbar } from "@/components/layout/navbar"
import { Footer } from "@/components/layout/footer"
import { Analytics } from "@vercel/analytics/react"
import { SpeedInsights } from "@vercel/speed-insights/next"

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" })

export const viewport: Viewport = {
  themeColor: "#080a0d",
  colorScheme: "dark",
}

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.url),
  title: {
    default: "Digital Wellbeing for Windows",
    template: `%s · Digital Wellbeing`,
  },
  description: siteConfig.description,
  keywords: [
    "Digital Wellbeing",
    "Digital Wellbeing Windows",
    "digital wellbeing Windows",
    "Windows screen time tracker",
    "screen time control Windows",
    "Focus Mode Windows",
    "app blocker Windows",
    "app timer Windows",
    "SleepGuard",
    "app locker Windows",
    "attention control app",
    "productivity Windows",
    "local-first wellbeing",
    "privacy-first screen time",
  ],
  authors: [{ name: siteConfig.developer }],
  alternates: {
    canonical: "https://digitalwellbeing.vercel.app/",
  },
  icons: {
    icon: "/logo.png",
    apple: "/logo.png",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://digitalwellbeing.vercel.app/",
    title: "Digital Wellbeing for Windows",
    description:
      "Understand your computer usage. Block distractions. Set limits. Protect your attention with Digital Wellbeing.",
    siteName: "Digital Wellbeing",
    images: [
      {
        url: "/logo.png",
        width: 1254,
        height: 1254,
        alt: "Digital Wellbeing for Windows",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Digital Wellbeing for Windows",
    description:
      "Understand your computer usage. Block distractions. Set limits. Protect your attention with Digital Wellbeing.",
    images: ["/logo.png"],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const softwareAppJsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Digital Wellbeing",
    alternateName: "Digital Wellbeing for Windows",
    url: "https://digitalwellbeing.vercel.app/",
    downloadUrl: "https://digitalwellbeing.vercel.app/api/download",
    operatingSystem: "Windows 10, Windows 11",
    applicationCategory: "ProductivityApplication",
    description: siteConfig.description,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      availability: "https://schema.org/InStock",
    },
  }

  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Digital Wellbeing",
    url: "https://digitalwellbeing.vercel.app/",
    description: siteConfig.description,
    potentialAction: {
      "@type": "SearchAction",
      target: "https://digitalwellbeing.vercel.app/",
    },
  }

  return (
    <html lang="en" className="dark scroll-smooth" style={{ colorScheme: "dark" }}>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("dw-website-theme")||localStorage.getItem("dw-website-theme");if(t==="light"||(!t&&window.matchMedia&&!window.matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.remove("dark");document.documentElement.classList.add("light");document.documentElement.style.colorScheme="light";}else{document.documentElement.classList.remove("light");document.documentElement.classList.add("dark");document.documentElement.style.colorScheme="dark";}}catch(e){}})();`
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareAppJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd) }}
        />
      </head>
      <body className={`${inter.variable} min-h-screen bg-background font-sans antialiased text-foreground selection:bg-dw-emerald/20 selection:text-white`}>
        <Navbar />
        {children}
        <Footer />
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  )
}
