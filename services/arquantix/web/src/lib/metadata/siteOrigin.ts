/**
 * Origine publique du site (canonical absolue, Open Graph `og:url`).
 *
 * Lot 6 — Priorité :
 * 1. `NEXT_PUBLIC_SITE_URL` (ex. https://www.arquantix.com) — à définir en prod.
 * 2. `VERCEL_URL` (préviews / déploiements Vercel, sans préfixe https dans l’env).
 *
 * Sans origine connue : pas de `metadataBase` imposée par l’env ; Next laissera les URLs
 * relatives ou partielles (acceptable en dev).
 */

export function getSiteOrigin(): string | null {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL?.trim()
  if (explicit) {
    try {
      const u = new URL(explicit)
      return `${u.protocol}//${u.host}`
    } catch {
      return null
    }
  }
  const vercel = process.env.VERCEL_URL?.trim()
  if (vercel) {
    const host = vercel.replace(/^https?:\/\//, '').replace(/\/$/, '')
    return `https://${host}`
  }
  return null
}

/** Pour `metadataBase` du layout racine (optionnel). */
export function getSiteMetadataBase(): URL | undefined {
  const o = getSiteOrigin()
  if (!o) return undefined
  try {
    return new URL(`${o}/`)
  } catch {
    return undefined
  }
}

/**
 * URL absolue pour un chemin canonique (sans query), ex. `/` ou `/about`.
 */
export function absoluteUrlForPath(canonicalPath: string): string | undefined {
  const o = getSiteOrigin()
  if (!o) return undefined
  const p = canonicalPath.startsWith('/') ? canonicalPath : `/${canonicalPath}`
  try {
    return new URL(p, `${o}/`).toString()
  } catch {
    return undefined
  }
}
