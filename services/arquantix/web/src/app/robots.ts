import type { MetadataRoute } from 'next'
import { headers } from 'next/headers'

/**
 * Robots host-aware :
 * - `console.arquantix.com` : Disallow:/ (sous-domaine privé admin uniquement,
 *   défense en profondeur en plus du header `X-Robots-Tag` posé par le middleware)
 * - autres hosts (site public) : Allow:/, Disallow `/admin/`, `/api/admin/`,
 *   `/api/`, `/preview/` ; renvoie le sitemap public.
 *
 * Le rendu est dynamique car il dépend de l'en-tête Host.
 */
export const dynamic = 'force-dynamic'

const ADMIN_CONSOLE_HOSTS = new Set(
  (process.env.ADMIN_CONSOLE_HOSTS || 'console.arquantix.com')
    .split(',')
    .map(s => s.trim().toLowerCase())
    .filter(Boolean),
)

export default async function robots(): Promise<MetadataRoute.Robots> {
  const h = await headers()
  const host = (h.get('host') || '').toLowerCase().split(':')[0]
  const isConsole = ADMIN_CONSOLE_HOSTS.has(host)

  if (isConsole) {
    return {
      rules: [
        {
          userAgent: '*',
          disallow: '/',
        },
      ],
    }
  }

  const publicOrigin = process.env.NEXT_PUBLIC_SITE_URL?.trim() || 'https://arquantix.com'
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin/', '/api/admin/', '/api/', '/preview/'],
      },
    ],
    sitemap: `${publicOrigin.replace(/\/$/, '')}/sitemap.xml`,
  }
}
