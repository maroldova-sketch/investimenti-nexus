// app/robots.ts — Next.js App Router
import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: ['/api/', '/_next/static/immutable/chunks/'] },
    ],
    sitemap: 'https://www.zamek-citoliby.cz/sitemap.xml',
    host: 'https://www.zamek-citoliby.cz',
  }
}
