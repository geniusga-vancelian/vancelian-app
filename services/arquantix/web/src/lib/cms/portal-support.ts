import type { Locale } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import {
  parsePortalSupportStorage,
  resolvePortalSupportBlockForLocale,
} from '@/lib/cms/portalSupportStorage'
import type { SupportAsideContent } from '@/components/design-system/SupportAsidePanel'

/** Runtime portail — English UI (aligned with portal nav copy). */
export const PORTAL_SUPPORT_RUNTIME_LOCALE: Locale = 'en'

export type PortalSupportContent = SupportAsideContent

export function getDefaultPortalSupportContent(): PortalSupportContent {
  return {
    title: 'Questions?',
    description: 'Our team answers technical questions within 24 hours.',
    ctaLabel: 'Contact support →',
    ctaHref: '/help',
    secondaryLinkLabel: 'Help center →',
    secondaryLinkHref: '/help',
  }
}

function mergePortalSupportContent(
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

export async function getPortalSupportContent(
  locale: Locale = PORTAL_SUPPORT_RUNTIME_LOCALE,
): Promise<PortalSupportContent> {
  const row = await prisma.globalSettings.findFirst({ select: { portalSupportJson: true } })
  const parsed = parsePortalSupportStorage(row?.portalSupportJson ?? null)
  const block = resolvePortalSupportBlockForLocale(parsed, locale)
  return mergePortalSupportContent(block)
}
