import { prisma } from '@/lib/prisma'
import type { FooterJsonInput } from '@/lib/sections/library'
import type { FooterSocialPlatform } from '@/lib/sections/library'
import { resolveMedia } from '@/lib/storage/media'
import { getLocaleOrDefault } from '@/config/locales'
import { parseFooterStorage, resolveFooterPayloadForLocale } from '@/lib/cms/footerStorage'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

export type { FooterSocialPlatform }

export type SiteFooterData = {
  copyright: string
  description: string
  links: Array<{ label: string; href: string; category?: string }>
  backgroundColor: string
  logoUrl: string | null
  logoAlt: string | null
  newsletterVisible: boolean
  newsletterTitle: string
  newsletterPlaceholder: string
  newsletterButtonLabel: string
  legalTexts: string[]
  socialLinks: Array<{ platform: FooterSocialPlatform; href: string }>
}

/**
 * Defaults du footer pour la locale demandée. Ces valeurs ne servent que
 * lorsque le CMS (`footer_json`) n'a rien fourni pour le champ correspondant.
 *
 * Tous les libellés génériques passent par `siteCommonCta` (FR / EN / IT) pour
 * éviter les libellés hardcodés et garantir un fallback cohérent par locale.
 */
export function getDefaultSiteFooterData(locale?: string): SiteFooterData {
  const year = new Date().getFullYear()
  const loc = getLocaleOrDefault(locale)
  return {
    copyright: `© ${year} Arquantix. ${siteCommonCta(loc, 'footer_all_rights_reserved')}`,
    description: siteCommonCta(loc, 'footer_default_tagline'),
    links: [],
    backgroundColor: '#000000',
    logoUrl: null,
    logoAlt: null,
    newsletterVisible: true,
    newsletterTitle: siteCommonCta(loc, 'footer_newsletter_default_title'),
    newsletterPlaceholder: siteCommonCta(loc, 'footer_newsletter_default_placeholder'),
    newsletterButtonLabel: siteCommonCta(loc, 'footer_newsletter_default_button'),
    legalTexts: [],
    socialLinks: [],
  }
}

async function buildSiteFooterDataFromPayload(
  d: FooterJsonInput,
  defaults: SiteFooterData,
): Promise<SiteFooterData> {
  const logoId = d.logoMediaId ?? null
  const media = logoId ? await resolveMedia(logoId) : null

  return {
    copyright: d.copyright?.trim() || defaults.copyright,
    description: d.description?.trim() || defaults.description,
    links: Array.isArray(d.links) ? d.links : [],
    backgroundColor: (d.backgroundColor?.trim() || defaults.backgroundColor).slice(0, 80),
    logoUrl: media?.url ?? null,
    logoAlt: media?.alt ?? null,
    newsletterVisible: d.newsletterVisible ?? defaults.newsletterVisible,
    newsletterTitle: d.newsletterTitle?.trim() || defaults.newsletterTitle,
    newsletterPlaceholder: d.newsletterPlaceholder?.trim() || defaults.newsletterPlaceholder,
    newsletterButtonLabel: d.newsletterButtonLabel?.trim() || defaults.newsletterButtonLabel,
    legalTexts: Array.isArray(d.legalTexts)
      ? d.legalTexts.map((t) => (typeof t === 'string' ? t : '')).filter(Boolean)
      : [],
    socialLinks: Array.isArray(d.socialLinks)
      ? d.socialLinks.filter((s) => s?.href?.trim())
      : [],
  }
}

/**
 * Données du footer global pour la locale demandée (cookie / routing).
 * Lit `footer_json` legacy ou v2 ; fallback documenté dans `resolveFooterPayloadForLocale`.
 */
export async function getSiteFooterData(locale?: string): Promise<SiteFooterData> {
  const resolvedLocale = getLocaleOrDefault(locale)
  const defaults = getDefaultSiteFooterData(resolvedLocale)

  try {
    const row = await prisma.globalSettings.findFirst()
    if (!row?.footerJson || typeof row.footerJson !== 'object') {
      return defaults
    }

    const parsed = parseFooterStorage(row.footerJson)
    if (parsed.kind === 'invalid') {
      return defaults
    }

    const payload = resolveFooterPayloadForLocale(parsed, resolvedLocale)
    return buildSiteFooterDataFromPayload(payload, defaults)
  } catch {
    return defaults
  }
}
