/**
 * « Check all module language » — scan par champ, détection, correction DRAFT allowlistée, vérif.
 */

import { defaultLocale } from '@/config/locales'
import type { Locale } from '@/config/locales'

import {
  collectAllowlistedVaultTextFields,
  type VaultAllowlistedTextField,
  type VaultAllowlistedTextKind,
} from '@/lib/admin/vaultAllowlistedTextFields'
import { verifyTranslatedVaultDraft } from '@/lib/admin/vaultAutoTranslateEngine'
import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import { setStringAtLot1Path } from '@/lib/i18n/integrity/fieldPathAccess'
import type { LinguisticAuditStatus } from '@/lib/i18n/integrity/types'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { translateText } from '@/lib/translate/translateText'

function excerpt(s: string, max = 140): string {
  const t = s.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

function cloneJson<T>(v: T): T {
  return typeof structuredClone !== 'undefined'
    ? structuredClone(v)
    : (JSON.parse(JSON.stringify(v)) as T)
}

export type VaultLanguageScanEntry = {
  path: string
  scope: VaultAllowlistedTextField['scope']
  textKind: VaultAllowlistedTextKind
  moduleIndex?: number
  moduleType?: string
  valueExcerpt: string
  status: LinguisticAuditStatus
  detectedLocale?: Locale
  confidence: number
  suggestedAction?: string
  autoFixEligible: boolean
}

export type VaultLanguageScanResult = {
  targetLocale: Locale
  entries: VaultLanguageScanEntry[]
  integrity: ReturnType<typeof verifyTranslatedVaultDraft>
  summary: {
    totalFields: number
    ok: number
    needsAttention: number
    byStatus: Record<LinguisticAuditStatus, number>
  }
}

/**
 * A. SCAN + détection par champ (réutilise `classifyTextForTargetLocale`).
 * C. Vérif agrégée via `collectVaultDraftFindings` (même périmètre intégrité que le lot 1 vault).
 */
export function scanVaultModuleLanguage(
  vaultData: Record<string, unknown>,
  pageI18n: { title: string | null; description: string | null } | undefined,
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
): VaultLanguageScanResult {
  const fields = collectAllowlistedVaultTextFields(vaultData, pageI18n)
  const entries: VaultLanguageScanEntry[] = []
  const byStatus: Record<LinguisticAuditStatus, number> = {
    OK: 0,
    MISSING: 0,
    WRONG_LANGUAGE: 0,
    MIXED_LANGUAGE: 0,
    NEEDS_REVIEW: 0,
    NON_TRANSLATABLE: 0,
  }

  for (const f of fields) {
    const cls = classifyTextForTargetLocale(f.value, targetLocale)
    byStatus[cls.status] += 1
    const autoFixEligible = cls.status === 'WRONG_LANGUAGE' || cls.status === 'MIXED_LANGUAGE'
    entries.push({
      path: f.path,
      scope: f.scope,
      textKind: f.textKind,
      moduleIndex: f.moduleIndex,
      moduleType: f.moduleType,
      valueExcerpt: excerpt(f.value),
      status: cls.status,
      detectedLocale: cls.detectedLocale,
      confidence: cls.confidence,
      suggestedAction: cls.suggestedAction,
      autoFixEligible,
    })
  }

  const integrity = verifyTranslatedVaultDraft(vaultData, targetLocale, pageSlug, pageId)
  const ok = entries.filter((e) => e.status === 'OK').length
  const needsAttention = entries.length - ok

  return {
    targetLocale,
    entries,
    integrity,
    summary: {
      totalFields: entries.length,
      ok,
      needsAttention,
      byStatus,
    },
  }
}

export type ApplyVaultLanguageFixResult = {
  vaultData: Record<string, unknown>
  pageI18n: { title: string | null; description: string | null }
  fixedFieldPaths: string[]
  tokensUsedApprox: number
  verifyAfter: ReturnType<typeof verifyTranslatedVaultDraft>
}

/**
 * Traduit vers `targetLocale` les champs WRONG_LANGUAGE / MIXED_LANGUAGE (allowlist uniquement).
 * NEEDS_REVIEW / OK / MISSING : non modifiés par cette passe.
 */
export async function applyVaultLanguageFixesToDraft(
  vaultData: Record<string, unknown>,
  pageI18n: { title: string | null; description: string | null },
  targetLocale: Locale,
  pageSlug: string,
  pageId: string,
): Promise<ApplyVaultLanguageFixResult> {
  const data = cloneJson(vaultData) as Record<string, unknown>
  let pi = { title: pageI18n.title, description: pageI18n.description }
  const fields = collectAllowlistedVaultTextFields(data, pi)
  const fixedFieldPaths: string[] = []
  let tokensUsedApprox = 0

  for (const f of fields) {
    const cls = classifyTextForTargetLocale(f.value, targetLocale)
    if (cls.status !== 'WRONG_LANGUAGE' && cls.status !== 'MIXED_LANGUAGE') {
      continue
    }

    const sourceLocale: Locale =
      cls.status === 'WRONG_LANGUAGE' && cls.detectedLocale
        ? cls.detectedLocale
        : (defaultLocale as Locale)

    let newText: string
    if (f.textKind === 'markdown' || cls.status === 'MIXED_LANGUAGE') {
      const r = await translateMarkdown(f.value, {
        sourceLocale,
        targetLocale,
      })
      newText = r.text
      tokensUsedApprox += r.tokensUsed ?? 0
    } else {
      const r = await translateText(f.value, {
        sourceLocale,
        targetLocale,
      })
      newText = r.text
      tokensUsedApprox += r.tokensUsed ?? 0
    }

    fixedFieldPaths.push(f.path)

    if (f.scope === 'page_i18n') {
      if (f.path === 'pageI18n.title') pi = { ...pi, title: newText }
      if (f.path === 'pageI18n.description') pi = { ...pi, description: newText }
    } else {
      setStringAtLot1Path(data, 'vault', f.path, newText)
    }
  }

  const verifyAfter = verifyTranslatedVaultDraft(data, targetLocale, pageSlug, pageId)

  return {
    vaultData: data,
    pageI18n: pi,
    fixedFieldPaths,
    tokensUsedApprox,
    verifyAfter,
  }
}
