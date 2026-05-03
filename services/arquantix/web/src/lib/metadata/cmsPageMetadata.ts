import type { Metadata } from 'next'
import type { Locale } from '@/config/locales'
import { absoluteUrlForPath } from '@/lib/metadata/siteOrigin'

/** Aligné sur l’ancienne racine `layout` ; utilisé si `Page.title` / `Page.description` sont vides. */
export const CMS_PAGE_METADATA_FALLBACK: Metadata = {
  title: 'Arquantix',
  description: 'Fractional Real Estate, Institutional Rigor.',
}

function fallbackTitle(): string {
  const t = CMS_PAGE_METADATA_FALLBACK.title
  return typeof t === 'string' ? t : 'Arquantix'
}

function fallbackDescription(): string {
  const d = CMS_PAGE_METADATA_FALLBACK.description
  return typeof d === 'string' ? d : 'Fractional Real Estate, Institutional Rigor.'
}

/** Balises Open Graph `locale` (BCP 47 avec région) — reflet de la locale résolue pour cette réponse. */
const OG_LOCALE_BY_LOCALE: Record<Locale, string> = {
  fr: 'fr_FR',
  en: 'en_US',
  it: 'it_IT',
}

/**
 * Métadonnées pour pages CMS publiques (home et `[slug]`).
 * Les champs `Page` en base sont mono-locale ; la locale résolue sert surtout à l’alignement futur.
 */
export function metadataFromCmsPageFields(input: {
  title?: string | null
  description?: string | null
}): Metadata {
  const title = input.title?.trim()
  const description = input.description?.trim()
  return {
    title: title || fallbackTitle(),
    description: description || fallbackDescription(),
  }
}

/**
 * Metadata SEO publique — canonical sans `?locale=`.
 *
 * **hreflang** (phase 2C) : `hreflangLanguages` = URLs **absolues** par clé `fr` | `en` | `it` | `x-default`.
 * Non émis sans origine site (`NEXT_PUBLIC_SITE_URL` / `VERCEL_URL`).
 *
 * **Open Graph** : aligné sur la locale de la réponse.
 */
export function buildPublicCmsPageMetadata(input: {
  title?: string | null
  description?: string | null
  /** Surcharge OG/Twitter si renseignés en `PageI18n` (Phase 2A). */
  ogTitle?: string | null
  ogDescription?: string | null
  /** Chemin sans query, ex. `/` ou `/a-propos` — doit correspondre à l’URL indexable réelle. */
  canonicalPath: string
  /** Locale résolue (cookie / query) pour cette réponse — cohérence aperçu partage. */
  locale: Locale
  /** URLs absolues pour `link[rel="alternate"][hreflang]` — uniquement locales réellement qualifiées. */
  hreflangLanguages?: Record<string, string>
}): Metadata {
  const title = input.title?.trim() || fallbackTitle()
  const description = input.description?.trim() || fallbackDescription()
  const ogTitle = input.ogTitle?.trim() || title
  const ogDescription = input.ogDescription?.trim() || description
  const path = input.canonicalPath.startsWith('/') ? input.canonicalPath : `/${input.canonicalPath}`
  const ogUrl = absoluteUrlForPath(path)

  const href = input.hreflangLanguages
  const hasHreflang = href && Object.keys(href).length > 0

  return {
    title,
    description,
    alternates: {
      canonical: path,
      ...(hasHreflang ? { languages: href } : {}),
    },
    robots: {
      index: true,
      follow: true,
    },
    openGraph: {
      title: ogTitle,
      description: ogDescription,
      type: 'website',
      siteName: 'Arquantix',
      locale: OG_LOCALE_BY_LOCALE[input.locale],
      ...(ogUrl ? { url: ogUrl } : {}),
    },
    twitter: {
      card: 'summary',
      title: ogTitle,
      description: ogDescription,
    },
  }
}
