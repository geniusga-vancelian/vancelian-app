import { getLocaleOrDefault } from '@/config/locales'
import { getSiteOrigin } from '@/lib/metadata/siteOrigin'
import { resolvePortalAppUrl } from '@/lib/wallet/externalWalletConstants'

function resolveBlogPublicOrigin(): string {
  return (
    getSiteOrigin() ??
    (() => {
      const base = process.env.NEXT_PUBLIC_BASE_URL?.trim()
      if (base) {
        try {
          const u = new URL(base)
          if (u.hostname !== '0.0.0.0' && u.hostname !== '127.0.0.1') {
            return `${u.protocol}//${u.host}`
          }
        } catch {
          // ignore
        }
      }
      return resolvePortalAppUrl()
    })()
  )
}

/** URL canonique publique d’un article blog (partage / Open Graph). */
export function publicArticlePageUrl(locale: string, slug: string): string {
  const loc = getLocaleOrDefault(locale)
  const path = `/${loc}/blog/${slug}`
  try {
    return new URL(path, `${resolveBlogPublicOrigin()}/`).href
  } catch {
    return path
  }
}
