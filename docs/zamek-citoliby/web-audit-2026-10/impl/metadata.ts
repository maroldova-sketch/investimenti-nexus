// app/layout.tsx (export const metadata) — základ pro canonical, OG a title šablonu.
import type { Metadata } from 'next'

export const metadata: Metadata = {
  metadataBase: new URL('https://www.zamek-citoliby.cz'),
  title: {
    default: 'Zámek Cítoliby – divadlo, svatby a gastronomie u Loun',
    template: '%s | Zámek Cítoliby',
  },
  description:
    'Barokní zámek u Loun se probouzí. Letní divadlo Zámecká Resonance 2027, svatby, firemní akce a zámecká gastronomie. Program akcí a předprodej vstupenek.',
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    locale: 'cs_CZ',
    siteName: 'Zámek Cítoliby',
    url: '/',
    images: [{ url: '/og/zamek-citoliby.jpg', width: 1200, height: 630, alt: 'Zámek Cítoliby – nádvoří barokního zámku' }], // skutečná fotografie, < 200 kB
  },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true },
  icons: { icon: '/favicon.ico', apple: '/apple-touch-icon.png' },
}

// Příklad pro stránku: app/svatby/page.tsx
export const svatbyMetadata: Metadata = {
  title: 'Svatba na zámku Cítoliby u Loun | 60 min od Prahy, 5 termínů 2027',
  description:
    'Prémiová svatba na soukromém barokním zámku 60 minut od Prahy. Nádvoří s arkádami, zahrada, sál, apartmá pro novomanžele a profesionální tým. V roce 2027 jen 5 svateb.',
  alternates: { canonical: '/svatby' },
  openGraph: { url: '/svatby', images: [{ url: '/og/svatby.jpg', width: 1200, height: 630 }] },
}
