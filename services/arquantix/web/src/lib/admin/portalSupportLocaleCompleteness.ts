import type { PortalSupportLocaleBlock } from '@/lib/cms/portalSupportSchema'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'

function t(s: string | undefined): string {
  return (s ?? '').trim()
}

export function levelForPortalSupportBlock(
  block: PortalSupportLocaleBlock,
): LocaleCompletenessLevel {
  const titleOk = t(block.title)
  const descriptionOk = t(block.description)
  const ctaOk = t(block.ctaLabel) && t(block.ctaHref)
  const secondaryOk = t(block.secondaryLinkLabel) && t(block.secondaryLinkHref)

  const hasAny = titleOk || descriptionOk || ctaOk || secondaryOk
  if (!hasAny) return 'missing'
  if (titleOk && descriptionOk && ctaOk && secondaryOk) return 'complete'
  return 'partial'
}

export function computePortalSupportLocalesCompleteness(
  locales: Record<Locale, PortalSupportLocaleBlock>,
): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    out[loc] = levelForPortalSupportBlock(locales[loc] ?? {})
  }
  return out
}
