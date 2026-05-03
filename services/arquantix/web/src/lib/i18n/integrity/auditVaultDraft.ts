/**
 * Lot 1 — audit des champs texte allowlistés dans le JSON vault (SectionContent DRAFT).
 */

import type { Locale } from '@/config/locales'

import type { LinguisticAuditFinding } from '@/lib/i18n/integrity/types'
import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import { excerpt } from '@/lib/i18n/integrity/textPrep'
import { stableFindingId } from '@/lib/i18n/integrity/findingId'

type VaultConfig = {
  pageTitle?: { text?: string }
  fixedBottomCta?: { label?: string }
  modules?: Array<{
    type?: string
    enabled?: boolean
    content?: Record<string, unknown>
  }>
}

function pushFinding(
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
      id: stableFindingId([pageId, fieldPath, 'missing']),
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
    id: stableFindingId([pageId, fieldPath, excerpt(text, 40)]),
    fieldPath,
    status: c.status === 'MISSING' ? 'NEEDS_REVIEW' : c.status,
    excerpt: excerpt(text),
    confidence: c.confidence,
    detectedIso6393: c.detectedIso6393,
    detectedLocale: c.detectedLocale,
    suggestedAction: c.suggestedAction,
  })
}

function auditModule(
  out: LinguisticAuditFinding[],
  mod: { type?: string; content?: Record<string, unknown>; enabled?: boolean },
  index: number,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
) {
  const type = mod.type ?? 'Unknown'
  const c = mod.content ?? {}
  const base = {
    domain: 'vault' as const,
    targetLocale,
    pageSlug,
    pageId,
    sectionKey: 'vault_builder_v1',
    moduleIndex: index,
    moduleType: type,
  }

  if (type === 'TitlePage') {
    pushFinding(out, base, c.title as string | undefined, `modules[${index}].content.title`, targetLocale, pageSlug, pageId)
    pushFinding(out, base, c.subtitle as string | undefined, `modules[${index}].content.subtitle`, targetLocale, pageSlug, pageId)
  } else if (type === 'SimpleMarkdownContentModule') {
    pushFinding(
      out,
      base,
      c.moduleTitle as string | undefined,
      `modules[${index}].content.moduleTitle`,
      targetLocale,
      pageSlug,
      pageId,
    )
    pushFinding(out, base, c.markdown as string | undefined, `modules[${index}].content.markdown`, targetLocale, pageSlug, pageId)
  } else if (type === 'FaqAccordionModule') {
    pushFinding(out, base, c.title as string | undefined, `modules[${index}].content.title`, targetLocale, pageSlug, pageId)
    pushFinding(
      out,
      base,
      c.footerLinkLabel as string | undefined,
      `modules[${index}].content.footerLinkLabel`,
      targetLocale,
      pageSlug,
      pageId,
    )
  }
  /* Autres types : hors périmètre Lot 1 — pas de scan « au hasard ». */
}

/**
 * Extrait les findings pour un document vault parsé (objet `data` SectionContent).
 */
export function collectVaultDraftFindings(
  data: unknown,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
): LinguisticAuditFinding[] {
  const out: LinguisticAuditFinding[] = []
  if (data == null || typeof data !== 'object') {
    return out
  }

  const cfg = data as VaultConfig
  const baseRoot = {
    domain: 'vault' as const,
    targetLocale,
    pageSlug,
    pageId,
    sectionKey: 'vault_builder_v1',
  }

  pushFinding(out, baseRoot, cfg.pageTitle?.text, 'pageTitle.text', targetLocale, pageSlug, pageId)
  pushFinding(out, baseRoot, cfg.fixedBottomCta?.label, 'fixedBottomCta.label', targetLocale, pageSlug, pageId)

  const modules = Array.isArray(cfg.modules) ? cfg.modules : []
  modules.forEach((mod, index) => {
    if (mod && mod.enabled === false) return
    auditModule(out, mod ?? {}, index, targetLocale, pageSlug, pageId)
  })

  return out
}
