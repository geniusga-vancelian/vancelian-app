import { resolvePortalAppUrl } from '@/lib/wallet/externalWalletConstants'

import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Hub Academy portail — liste / filtres éditoriaux. */
export function portalAcademyHubRoute(): string {
  return PORTAL_ROUTES.academy
}

/** Détail article portail (news, research, academy) — jamais `/blog/` dans la webapp. */
export function portalArticleRoute(slug: string): string {
  const normalized = slug.trim()
  if (!normalized) return portalAcademyHubRoute()
  return `${PORTAL_ROUTES.academy}/${encodeURIComponent(normalized)}`
}

/** URL article pour APIs portail (origin optionnel pour SSR absolutisé). */
export function resolvePortalArticleHref(slug: string, origin?: string): string {
  const path = portalArticleRoute(slug)
  if (origin && !path.startsWith('http')) {
    return `${origin.replace(/\/$/, '')}${path}`
  }
  return path
}

/** Canonical share URL côté webapp (Open Graph portail). */
export function portalArticlePublicUrl(slug: string, baseUrl?: string): string {
  const path = portalArticleRoute(slug)
  const base = (baseUrl ?? resolvePortalAppUrl()).replace(/\/$/, '')
  try {
    return new URL(path, base).href
  } catch {
    return path
  }
}
