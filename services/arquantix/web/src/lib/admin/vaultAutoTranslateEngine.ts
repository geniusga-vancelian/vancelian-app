/**
 * Pipeline logique COPY (clone FR) → TRANSLATE (OpenAI, allowlist) → VERIFY (intégrité linguistique).
 * Aucune écriture DB ici — voir la route API.
 */

import type { Locale } from '@/config/locales'
import { translateText } from '@/lib/translate/translateText'
import type { TranslationOptions } from '@/lib/translate/types'

import { shouldSkipPlainString } from '@/lib/admin/vaultAutoTranslateAllowlist'
import {
  translateModuleContent,
  type TranslateStats,
} from '@/lib/admin/vaultAutoTranslateModules'
import { collectVaultDraftFindings } from '@/lib/i18n/integrity/auditVaultDraft'
import type {
  LinguisticAuditFinding,
  LinguisticAuditStatus,
} from '@/lib/i18n/integrity/types'

const SOURCE_LOCALE: Locale = 'fr'

function cloneJson<T>(v: T): T {
  return typeof structuredClone !== 'undefined'
    ? structuredClone(v)
    : (JSON.parse(JSON.stringify(v)) as T)
}

async function translatePlainField(
  s: string | undefined,
  opts: TranslationOptions,
  stats: TranslateStats,
): Promise<string | undefined> {
  if (s == null || typeof s !== 'string') return s
  if (!s.trim()) return s
  if (shouldSkipPlainString(s)) return s
  const r = await translateText(s, opts)
  stats.fieldsTranslated += 1
  stats.tokensUsedApprox += r.tokensUsed ?? 0
  return r.translated
}

/**
 * Clone profond du JSON vault + traduction des champs racine (`pageTitle.text`, `fixedBottomCta.label`) et de chaque module allowlisté.
 */
export async function translateVaultDraftJsonFromFr(
  sourceData: Record<string, unknown>,
  targetLocale: 'en' | 'it',
): Promise<{ data: Record<string, unknown>; stats: TranslateStats }> {
  const data = cloneJson(sourceData)
  const stats: TranslateStats = { fieldsTranslated: 0, tokensUsedApprox: 0 }
  const opts: TranslationOptions = {
    sourceLocale: SOURCE_LOCALE,
    targetLocale,
  }

  if (data.pageTitle && typeof data.pageTitle === 'object') {
    const pt = { ...(data.pageTitle as Record<string, unknown>) }
    if (typeof pt.text === 'string') {
      pt.text = (await translatePlainField(pt.text, opts, stats)) ?? pt.text
    }
    data.pageTitle = pt
  }

  if (data.fixedBottomCta && typeof data.fixedBottomCta === 'object') {
    const fb = { ...(data.fixedBottomCta as Record<string, unknown>) }
    if (typeof fb.label === 'string') {
      fb.label = (await translatePlainField(fb.label, opts, stats)) ?? fb.label
    }
    data.fixedBottomCta = fb
  }

  const modules = Array.isArray(data.modules) ? data.modules : []
  data.modules = await Promise.all(
    modules.map(async (mod) => {
      if (mod == null || typeof mod !== 'object') return mod
      const m = { ...(mod as Record<string, unknown>) }
      const typ = typeof m.type === 'string' ? m.type : 'unknown'
      const rawContent = m.content
      const content =
        rawContent != null && typeof rawContent === 'object' && !Array.isArray(rawContent)
          ? ({ ...(rawContent as Record<string, unknown>) } as Record<string, unknown>)
          : {}
      m.content = await translateModuleContent(typ, content, opts, stats)
      return m
    }),
  )

  return { data, stats }
}

/**
 * Traduit titre / description PageI18n à partir du texte français source.
 */
export async function translatePageI18nFromFr(
  titleFr: string | null,
  descriptionFr: string | null,
  targetLocale: 'en' | 'it',
): Promise<{
  title: string | null
  description: string | null
  stats: TranslateStats
}> {
  const stats: TranslateStats = { fieldsTranslated: 0, tokensUsedApprox: 0 }
  const opts: TranslationOptions = { sourceLocale: SOURCE_LOCALE, targetLocale }

  let title: string | null = titleFr
  let description: string | null = descriptionFr

  if (typeof titleFr === 'string' && titleFr.trim()) {
    const r = await translateText(titleFr, opts)
    title = r.translated
    stats.fieldsTranslated += 1
    stats.tokensUsedApprox += r.tokensUsed ?? 0
  }

  if (typeof descriptionFr === 'string' && descriptionFr.trim()) {
    const r = await translateText(descriptionFr, opts)
    description = r.translated
    stats.fieldsTranslated += 1
    stats.tokensUsedApprox += r.tokensUsed ?? 0
  }

  return { title, description, stats }
}

export function mergeTranslateStats(a: TranslateStats, b: TranslateStats): TranslateStats {
  return {
    fieldsTranslated: a.fieldsTranslated + b.fieldsTranslated,
    tokensUsedApprox: a.tokensUsedApprox + b.tokensUsedApprox,
  }
}

export function verifyTranslatedVaultDraft(
  vaultData: unknown,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
): {
  findings: LinguisticAuditFinding[]
  byStatus: Record<LinguisticAuditStatus, number>
  suspiciousCount: number
} {
  const findings = collectVaultDraftFindings(vaultData, targetLocale, pageSlug, pageId)
  const byStatus: Record<LinguisticAuditStatus, number> = {
    OK: 0,
    MISSING: 0,
    WRONG_LANGUAGE: 0,
    MIXED_LANGUAGE: 0,
    NEEDS_REVIEW: 0,
    NON_TRANSLATABLE: 0,
  }
  for (const f of findings) {
    byStatus[f.status] += 1
  }
  const suspiciousCount = findings.filter((f) => f.status !== 'OK').length
  return { findings, byStatus, suspiciousCount }
}
