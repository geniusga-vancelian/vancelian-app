/**
 * Lot 1 — sections CMS `hero` et `cta` uniquement (champs texte allowlistés).
 */

import type { Locale } from '@/config/locales'

import type { LinguisticAuditFinding } from '@/lib/i18n/integrity/types'
import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import { excerpt } from '@/lib/i18n/integrity/textPrep'
import { stableFindingId } from '@/lib/i18n/integrity/findingId'

function push(
  out: LinguisticAuditFinding[],
  base: Omit<
    LinguisticAuditFinding,
    'id' | 'fieldPath' | 'excerpt' | 'status' | 'confidence' | 'suggestedAction' | 'detectedIso6393' | 'detectedLocale'
  >,
  raw: string | undefined | null,
  fieldPath: string,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
) {
  const text = typeof raw === 'string' ? raw : ''
  if (!text.trim()) {
    out.push({
      ...base,
      id: stableFindingId([pageId, base.sectionKey ?? '', fieldPath, 'missing']),
      fieldPath,
      status: 'MISSING',
      excerpt: '',
      confidence: 0,
      detectedIso6393: 'und',
      suggestedAction: 'Renseigner ce champ pour la locale (brouillon).',
    })
    return
  }
  const c = classifyTextForTargetLocale(text, targetLocale)
  out.push({
    ...base,
    id: stableFindingId([pageId, base.sectionKey ?? '', fieldPath, excerpt(text, 40)]),
    fieldPath,
    status: c.status === 'MISSING' ? 'NEEDS_REVIEW' : c.status,
    excerpt: excerpt(text),
    confidence: c.confidence,
    detectedIso6393: c.detectedIso6393,
    detectedLocale: c.detectedLocale,
    suggestedAction: c.suggestedAction,
  })
}

/** Champs `data` hero (sans URLs / IDs médias). */
export function collectHeroDraftFindings(
  data: Record<string, unknown>,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
  sectionId: string,
  sectionKey: 'hero' | 'hero_secondary' = 'hero',
): LinguisticAuditFinding[] {
  const out: LinguisticAuditFinding[] = []
  const base = {
    domain: 'cms_section' as const,
    targetLocale,
    pageSlug,
    pageId,
    sectionKey,
    sectionId,
  }

  push(out, base, data.title as string | undefined, 'data.title', targetLocale, pageSlug, pageId)
  push(out, base, data.subtitle as string | undefined, 'data.subtitle', targetLocale, pageSlug, pageId)
  push(out, base, data.ctaText as string | undefined, 'data.ctaText', targetLocale, pageSlug, pageId)
  push(out, base, data.sidebarText as string | undefined, 'data.sidebarText', targetLocale, pageSlug, pageId)

  /*
   * Champs `emailPlaceholder` / `emailButtonText` / `keyStats` retirés de l'audit
   * Lot 1 : ils ont été supprimés du `heroSchema` (cf. audit Famille 3 — Q1
   * « hero_extras: remove »). Aucun composant ne les rend plus.
   */
  /* tags : souvent très courts — hors périmètre Lot 1 (trop de faux positifs). */

  return out
}

export function collectCtaDraftFindings(
  data: Record<string, unknown>,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
  sectionId: string,
): LinguisticAuditFinding[] {
  const out: LinguisticAuditFinding[] = []
  const base = {
    domain: 'cms_section' as const,
    targetLocale,
    pageSlug,
    pageId,
    sectionKey: 'cta',
    sectionId,
  }

  push(out, base, data.eyebrow as string | undefined, 'data.eyebrow', targetLocale, pageSlug, pageId)
  push(out, base, data.title as string | undefined, 'data.title', targetLocale, pageSlug, pageId)
  push(out, base, data.description as string | undefined, 'data.description', targetLocale, pageSlug, pageId)
  push(out, base, data.primaryButtonText as string | undefined, 'data.primaryButtonText', targetLocale, pageSlug, pageId)
  push(out, base, data.secondaryButtonText as string | undefined, 'data.secondaryButtonText', targetLocale, pageSlug, pageId)

  return out
}
