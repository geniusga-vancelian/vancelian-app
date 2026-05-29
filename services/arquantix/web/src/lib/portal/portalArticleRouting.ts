import { resolvePortalAppUrl } from '@/lib/wallet/externalWalletConstants'

import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

function isInternalPortalHost(hostname: string): boolean {
  const h = hostname.trim().toLowerCase()
  return h === '0.0.0.0' || h === '127.0.0.1' || h === 'localhost'
}

function isPublicPortalOrigin(origin: string): boolean {
  try {
    return !isInternalPortalHost(new URL(origin).hostname)
  } catch {
    return false
  }
}

/**
 * Liens article côté navigateur : toujours un chemin relatif `/app/academy/...`.
 * Supprime les URLs absolues loopback (127.0.0.1, 0.0.0.0) renvoyées par erreur depuis le BFF ECS.
 */
export function sanitizePortalArticleClientHref(href: string): string {
  const trimmed = href.trim()
  if (!trimmed) return portalAcademyHubRoute()
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
    return trimmed.startsWith('/') ? trimmed : `/${trimmed}`
  }
  try {
    const u = new URL(trimmed)
    if (isInternalPortalHost(u.hostname)) {
      return `${u.pathname}${u.search}${u.hash}` || portalAcademyHubRoute()
    }
  } catch {
    return trimmed
  }
  return trimmed
}

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
  const o = origin?.trim()
  if (o && !path.startsWith('http') && isPublicPortalOrigin(o)) {
    return sanitizePortalArticleClientHref(`${o.replace(/\/$/, '')}${path}`)
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
