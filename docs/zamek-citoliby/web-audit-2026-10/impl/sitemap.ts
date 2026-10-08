// app/sitemap.ts — Next.js App Router. Fáze 1: statické stránky; akce doplnit z CMS.
import type { MetadataRoute } from 'next'

const BASE = 'https://www.zamek-citoliby.cz'

// TODO: nahradit načtením z CMS (events, posts). Zachovat lastModified = datum poslední editace obsahu.
const staticPages: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]['changeFrequency'] }[] = [
  { path: '/', priority: 1.0, changeFrequency: 'weekly' },
  { path: '/program', priority: 0.9, changeFrequency: 'daily' },
  { path: '/divadlo', priority: 0.9, changeFrequency: 'weekly' },
  { path: '/svatby', priority: 0.9, changeFrequency: 'weekly' },
  { path: '/firemni-akce', priority: 0.8, changeFrequency: 'weekly' },
  { path: '/gastronomie', priority: 0.6, changeFrequency: 'weekly' },
  { path: '/historie', priority: 0.6, changeFrequency: 'monthly' },
  { path: '/obnova-zamku', priority: 0.7, changeFrequency: 'weekly' },
  { path: '/navsteva', priority: 0.7, changeFrequency: 'monthly' },
  { path: '/fotografie', priority: 0.5, changeFrequency: 'monthly' },
  { path: '/pamet-mista', priority: 0.4, changeFrequency: 'monthly' },
  { path: '/kontakt', priority: 0.8, changeFrequency: 'monthly' },
  { path: '/ochrana-osobnich-udaju', priority: 0.1, changeFrequency: 'yearly' },
]

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date()
  const pages = staticPages.map((p) => ({ url: `${BASE}${p.path}`, lastModified: now, changeFrequency: p.changeFrequency, priority: p.priority }))
  // const events = await getEvents(); pages.push(...events.map(e => ({ url: `${BASE}/program/${e.slug}`, lastModified: e.updatedAt, changeFrequency: 'weekly', priority: 0.8 })))
  return pages
}
