import { cache } from 'react'

import type { Locale } from '@/config/locales'
import { getLocaleOrDefault } from '@/config/locales'
import { parseFooterStorage, resolveFooterPayloadForLocale } from '@/lib/cms/footerStorage'
import { normalizeVancelianDarkColor } from '@/lib/cms/parseEditorialTitle'
import {
  getDefaultPortalSupportContent,
  type PortalSupportContent,
} from '@/lib/cms/portal-support'
import { getDefaultSiteFooterData, type SiteFooterData } from '@/lib/cms/site-footer'
import { parsePortalSupportStorage, resolvePortalSupportBlockForLocale } from '@/lib/cms/portalSupportStorage'
import { prisma } from '@/lib/prisma'
import type { FooterJsonInput } from '@/lib/sections/library'
import { resolveMedia } from '@/lib/storage/media'

export type PortalShellBootstrap = {
  footer: SiteFooterData
  support: PortalSupportContent
}

async function buildFooterFromPayload(
  d: FooterJsonInput,
  defaults: SiteFooterData,
): Promise<SiteFooterData> {
  const logoId = d.logoMediaId ?? null
  const media = logoId ? await resolveMedia(logoId) : null

  return {
    copyright: d.copyright?.trim() || defaults.copyright,
    description: d.description?.trim() || defaults.description,
    companyAddress: d.companyAddress?.trim() || defaults.companyAddress,
    secondaryNote: d.secondaryNote?.trim() || defaults.secondaryNote,
    links: Array.isArray(d.links) ? d.links : [],
    backgroundColor: normalizeVancelianDarkColor(d.backgroundColor?.trim() || defaults.backgroundColor).slice(
      0,
      80,
    ),
    logoUrl: media?.url ?? null,
    logoAlt: media?.alt ?? null,
    logoMediaInvert: d.logoMediaInvert ?? defaults.logoMediaInvert,
    newsletterVisible: d.newsletterVisible ?? defaults.newsletterVisible,
    newsletterTitle: d.newsletterTitle?.trim() || defaults.newsletterTitle,
    newsletterPlaceholder: d.newsletterPlaceholder?.trim() || defaults.newsletterPlaceholder,
    newsletterButtonLabel: d.newsletterButtonLabel?.trim() || defaults.newsletterButtonLabel,
    legalTexts: Array.isArray(d.legalTexts)
      ? d.legalTexts.map((t) => (typeof t === 'string' ? t : '')).filter(Boolean)
      : [],
    socialLinks: Array.isArray(d.socialLinks) ? d.socialLinks.filter((s) => s?.href?.trim()) : [],
  }
}

function mergeSupportBlock(
  block: ReturnType<typeof resolvePortalSupportBlockForLocale>,
): PortalSupportContent {
  const defaults = getDefaultPortalSupportContent()
  return {
    title: block.title?.trim() || defaults.title,
    description: block.description?.trim() || defaults.description,
    ctaLabel: block.ctaLabel?.trim() || defaults.ctaLabel,
    ctaHref: block.ctaHref?.trim() || defaults.ctaHref,
    secondaryLinkLabel: block.secondaryLinkLabel?.trim() || defaults.secondaryLinkLabel,
    secondaryLinkHref: block.secondaryLinkHref?.trim() || defaults.secondaryLinkHref,
  }
}

async function loadPortalShellBootstrapUncached(locale?: string): Promise<PortalShellBootstrap> {
  const resolvedLocale = getLocaleOrDefault(locale) as Locale
  const footerDefaults = getDefaultSiteFooterData(resolvedLocale)
  const supportDefaults = getDefaultPortalSupportContent()

  try {
    const row = await prisma.globalSettings.findFirst({
      select: { footerJson: true, portalSupportJson: true },
    })

    let footer = footerDefaults
    if (row?.footerJson && typeof row.footerJson === 'object') {
      const parsed = parseFooterStorage(row.footerJson)
      if (parsed.kind !== 'invalid') {
        const payload = resolveFooterPayloadForLocale(parsed, resolvedLocale)
        footer = await buildFooterFromPayload(payload, footerDefaults)
      }
    }

    const supportParsed = parsePortalSupportStorage(row?.portalSupportJson ?? null)
    const support = mergeSupportBlock(resolvePortalSupportBlockForLocale(supportParsed, resolvedLocale))

    return { footer, support }
  } catch {
    return { footer: footerDefaults, support: supportDefaults }
  }
}

/** Footer + support portail — une requête `global_settings` par rendu RSC (cache React). */
export const getPortalShellBootstrap = cache(loadPortalShellBootstrapUncached)
