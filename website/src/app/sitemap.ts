import { MetadataRoute } from "next"
import { docPages, site } from "@/data/site"

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date()
  return [
    { url: `${site.url}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${site.url}/docs`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    ...docPages.map((page) => ({
      url: `${site.url}/docs/${page.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ]
}
