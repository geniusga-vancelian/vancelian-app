import type { FooterJsonInput } from '@/lib/sections/library'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import type { LocaleCompletenessLevel } from '@/lib/admin/pageLocaleCompleteness'

function t(s: string | undefined): string {
  return (s ?? '').trim()
}

/**
 * Complétude éditoriale d’un bloc footer pour une locale (pas de statut DB type SectionContent).
 * — missing : presque vide (inutilisable en prod pour cette langue)
 * — partial : contenu partiel ou incohérences (lien incomplet, newsletter visible mais champs vides)
 * — complete : champs « cœur » remplis et cohérence des listes
 */
export function levelForFooterBlock(block: FooterJsonInput): LocaleCompletenessLevel {
  const copyright = t(block.copyright)
  const description = t(block.description)
  const links = block.links ?? []
  const hasRealLink = links.some((l) => t(l.label) && t(l.href))
  const incompleteLink = links.some((l) => (t(l.label) && !t(l.href)) || (!t(l.label) && t(l.href)))

  const newsOn = block.newsletterVisible !== false
  const nt = t(block.newsletterTitle)
  const np = t(block.newsletterPlaceholder)
  const nb = t(block.newsletterButtonLabel)
  const newsFields = [nt, np, nb].filter(Boolean).length
  const newsBroken = newsOn && newsFields > 0 && newsFields < 3

  const social = block.socialLinks ?? []
  const socialIncomplete = social.some((s) => !t(s.href))

  const legal = block.legalTexts ?? []
  const hasLegal = legal.some((x) => t(x))

  const hasAnyText =
    copyright.length > 0 ||
    description.length > 0 ||
    hasRealLink ||
    (newsOn && newsFields > 0) ||
    hasLegal ||
    social.some((s) => t(s.href))

  if (!hasAnyText) return 'missing'

  if (incompleteLink || newsBroken || socialIncomplete) return 'partial'

  const coreOk = copyright.length > 0 && description.length > 0
  const newsOk = !newsOn || (nt.length > 0 && np.length > 0 && nb.length > 0)

  if (coreOk && newsOk) return 'complete'
  return 'partial'
}

export function computeFooterLocalesCompleteness(
  locales: Record<Locale, FooterJsonInput>,
): Record<Locale, LocaleCompletenessLevel> {
  const out = {} as Record<Locale, LocaleCompletenessLevel>
  for (const loc of supportedLocales) {
    out[loc] = levelForFooterBlock(locales[loc] ?? {})
  }
  return out
}
