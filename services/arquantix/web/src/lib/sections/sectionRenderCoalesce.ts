/**
 * Helpers purs pour le mapping CMS → props (Page Builder).
 * Toute logique ici doit reproduire à l’identique les coalescences historiques
 * (`||`, ordre des fallbacks) — les golden tests et la couverture i18n/editor
 * sont le filet de sécurité.
 */

/** Opacité hero / CTA : 0–1, chaîne numérique acceptée comme en production. */
export function heroBackgroundOpacity01(raw: unknown): number {
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    return Math.min(1, Math.max(0, raw))
  }
  if (typeof raw === 'string') {
    const parsed = parseFloat(raw)
    if (Number.isFinite(parsed)) {
      return Math.min(1, Math.max(0, parsed))
    }
  }
  return 1
}

/** URL média hero : uniquement `backgroundMediaUrl` CMS (trim). */
export function heroResolvedBackgroundUrl(data: { backgroundMediaUrl?: unknown }): string {
  return typeof data.backgroundMediaUrl === 'string' ? data.backgroundMediaUrl.trim() : ''
}

/** CTA marketing : `primary*` prioritaire si truthy (même `''` est falsy — `||`). */
export function ctaPrimaryFromLegacy(data: {
  primaryButtonText?: unknown
  ctaText?: unknown
  primaryButtonHref?: unknown
  ctaLink?: unknown
}): { primaryButtonText: unknown; primaryButtonHref: unknown } {
  return {
    primaryButtonText: data.primaryButtonText || data.ctaText,
    primaryButtonHref: data.primaryButtonHref || data.ctaLink,
  }
}

/** Famille about / feature_grid / features : image unifiée + pas de CTA vers le DOM. */
export function aboutFamilyToProps(data: any): {
  title: any
  description: any
  items: any
  imageUrl: any
  content: any
} {
  return {
    title: data.title,
    description: data.description,
    items: data.items,
    imageUrl: data.imageMediaUrl || data.imageUrl,
    content: data.content,
  }
}

export function projectGridLegacyItemToProp(item: any): any {
  return {
    ...item,
    backgroundImage: item.mediaUrl || item.backgroundImage,
  }
}

export function clampOpacity01(n: number): number {
  return Math.min(1, Math.max(0, n))
}
