import { MetadataRoute } from 'next'
import { site } from '@/data/site'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/'],
      },
    ],
    // Derived from site.url so the canonical host is changed in one place.
    sitemap: `${site.url}/sitemap.xml`,
  }
}
