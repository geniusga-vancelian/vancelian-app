/**
 * Noyau générique « Vérifier la langue » multi-domain.
 *
 * Mutualise pour Footer / Menu / (futurement Pages) la logique :
 *   1. Scan local rapide (`classifyTextForTargetLocale` + heuristiques courts).
 *   2. Affinage IA batché OpenAI sur les cas ambigus (NEEDS_REVIEW + faibles
 *      confiances).
 *   3. Décision de traduction unique partagée entre scan et apply via
 *      `LanguageHints` (path canonique → Locale).
 *
 * Ce module ne sait *rien* du domain (Footer, Menu, …). Il prend en entrée
 * une liste plate `GenericFieldInput[]` que chaque adaptateur (footerCheck…,
 * menuCheck…) construit depuis son schéma maison.
 *
 * **Volontairement pas utilisé par `pageCheckLanguage.ts`** pour ne pas
 * risquer de régression sur la partie déjà testée et productionnée — un
 * refactor ultérieur pourra unifier les deux pipelines si les contraintes
 * convergent.
 */

import type { Locale } from '@/config/locales'
import { defaultLocale } from '@/config/locales'

import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import type { LinguisticAuditStatus } from '@/lib/i18n/integrity/types'
import {
  batchClassifyLanguages,
  type BatchClassifyItem,
  type BatchLanguageRefiner,
} from '@/lib/i18n/llm/batchClassifyLanguages'
import {
  decideShortHeaderAction,
  isShortHeaderPath,
} from '@/lib/admin/pageCheckLanguage'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { translateText } from '@/lib/translate/translateText'

/* -------------------------------------------------------------------------- */
/* Types publics                                                              */
/* -------------------------------------------------------------------------- */

export type GenericTextKind = 'plain' | 'markdown'

/**
 * Champ atomique à scanner.
 *
 * - `hintKey` : clé canonique stable utilisée pour relier le résultat de
 *   scan à l'apply (et pour propager les décisions LLM). Doit être **unique**
 *   à l'intérieur d'un même scan ; si deux items partagent une `hintKey`,
 *   le second remplace le premier dans la `Map` de hints (cas accepté pour
 *   les duplicats parfaits).
 * - `path` : chemin lisible affiché dans la modale (ex. `links[2].label`).
 * - `value` : valeur textuelle telle qu'éditée. Vide → ignoré.
 * - `kind` : `plain` ou `markdown` (pilote `translateText` vs `translateMarkdown`).
 * - `domain` : libre (`footer` / `menu` / …) — tag remonté dans les entrées
 *   pour l'UI et le debug.
 * - `groupId` / `groupLabel` : optionnels. Permettent à l'UI de regrouper
 *   les entrées (ex : « item 0 » / « item 1 » pour le menu).
 */
export type GenericFieldInput = {
  hintKey: string
  path: string
  value: string
  kind: GenericTextKind
  domain: string
  groupId?: string
  groupLabel?: string
  /**
   * Force le traitement « short header » même si le `path` ne matche pas
   * `isShortHeaderPath` (qui est conservatrice côté pages CMS pour ne pas
   * traduire de noms propres type `data.author.name`).
   *
   * Cas d'usage : adaptateur Menu (`extractMenuFields`) marque `menu.name`
   * et `items[i].label` comme short-headers car ce sont par nature des
   * en-têtes courts traductibles, sans aucun risque de nom propre.
   */
  isShortHeader?: boolean
}

export type GenericScanEntry = {
  hintKey: string
  path: string
  domain: string
  groupId?: string
  groupLabel?: string
  textKind: GenericTextKind
  valueExcerpt: string
  status: LinguisticAuditStatus
  detectedLocale?: Locale
  confidence: number
  suggestedAction?: string
  autoFixEligible: boolean
}

export type GenericScanSummary = {
  totalFields: number
  ok: number
  needsAttention: number
  byStatus: Record<LinguisticAuditStatus, number>
}

export type GenericLLMRefinement = {
  attempted: number
  refined: number
  tokensUsedApprox: number
  callCount: number
  hadError: boolean
}

export type GenericScanResult = {
  targetLocale: Locale
  entries: GenericScanEntry[]
  summary: GenericScanSummary
  llmRefinement: GenericLLMRefinement
}

/**
 * Carte path canonique (`hintKey`) → Locale détectée.
 *
 * Fournie en entrée d'`applyFieldsLanguageFixes` pour court-circuiter la
 * détection locale et garantir la cohérence avec le scan deep.
 */
export type GenericLanguageHints = Map<string, Locale>

export type GenericSkippedFieldDiagnostic = {
  hintKey: string
  path: string
  domain: string
  groupId?: string
  status: LinguisticAuditStatus
  reason:
    | 'already_in_target'
    | 'undetectable_short_text_on_default_locale'
    | 'not_eligible'
  valueExcerpt: string
}

export type GenericApplyResult = {
  /**
   * Map `hintKey` → nouvelle valeur (texte traduit).
   *
   * Le module ne persiste rien : c'est à l'adaptateur de domain de re-projeter
   * ces valeurs dans son schéma de stockage.
   */
  fixedByHintKey: Map<string, string>
  fixedHintKeys: string[]
  tokensUsedApprox: number
  skippedFields: GenericSkippedFieldDiagnostic[]
}

/* -------------------------------------------------------------------------- */
/* Helpers internes                                                           */
/* -------------------------------------------------------------------------- */

function excerpt(s: string, max = 140): string {
  const t = s.trim()
  if (t.length <= max) return t
  return `${t.slice(0, max)}…`
}

function emptyByStatus(): Record<LinguisticAuditStatus, number> {
  return {
    OK: 0,
    MISSING: 0,
    WRONG_LANGUAGE: 0,
    MIXED_LANGUAGE: 0,
    NEEDS_REVIEW: 0,
    NON_TRANSLATABLE: 0,
  }
}

function isShortHeaderAutoFixEligible(
  status: LinguisticAuditStatus,
  field: GenericFieldInput,
  targetLocale: Locale,
): boolean {
  if (status !== 'NEEDS_REVIEW') return false
  if (!field.isShortHeader && !isShortHeaderPath(field.path)) return false
  return decideShortHeaderAction(field.value, targetLocale).kind === 'translate'
}

function isLLMRefineCandidate(entry: GenericScanEntry): boolean {
  if (entry.status === 'NEEDS_REVIEW') return true
  if (
    (entry.status === 'OK' || entry.status === 'WRONG_LANGUAGE') &&
    entry.confidence < 0.5
  ) {
    return true
  }
  return false
}

function applyLLMResultToEntry(
  entry: GenericScanEntry,
  llm: { locale: Locale | 'und'; confidence: number },
  targetLocale: Locale,
): boolean {
  if (llm.locale === 'und') return false
  if (llm.confidence < 0.4) return false

  const newDetected = llm.locale
  const newStatus: LinguisticAuditStatus =
    newDetected === targetLocale ? 'OK' : 'WRONG_LANGUAGE'

  if (entry.status === newStatus && entry.detectedLocale === newDetected) {
    return false
  }

  entry.status = newStatus
  entry.detectedLocale = newDetected
  entry.confidence = Math.max(entry.confidence, llm.confidence)

  if (newStatus === 'WRONG_LANGUAGE') {
    entry.autoFixEligible = true
    entry.suggestedAction = `Langue détectée (${newDetected}) ≠ locale cible (${targetLocale}) — IA.`
  } else {
    entry.autoFixEligible = false
    entry.suggestedAction = undefined
  }
  return true
}

/* -------------------------------------------------------------------------- */
/* SCAN local                                                                  */
/* -------------------------------------------------------------------------- */

/**
 * Scan synchrone 100 % local : `classifyTextForTargetLocale` + heuristique
 * « short header ». Aucun appel réseau.
 */
export function scanFieldsLocally(
  fields: GenericFieldInput[],
  targetLocale: Locale,
): { entries: GenericScanEntry[]; byStatus: Record<LinguisticAuditStatus, number> } {
  const entries: GenericScanEntry[] = []
  const byStatus = emptyByStatus()

  for (const field of fields) {
    const value = typeof field.value === 'string' ? field.value : ''
    if (!value.trim()) continue

    const cls = classifyTextForTargetLocale(value, targetLocale)
    byStatus[cls.status] += 1

    const shortHeaderEligible = isShortHeaderAutoFixEligible(
      cls.status,
      field,
      targetLocale,
    )

    entries.push({
      hintKey: field.hintKey,
      path: field.path,
      domain: field.domain,
      groupId: field.groupId,
      groupLabel: field.groupLabel,
      textKind: field.kind,
      valueExcerpt: excerpt(value),
      status: cls.status,
      detectedLocale: cls.detectedLocale,
      confidence: cls.confidence,
      suggestedAction: cls.suggestedAction,
      autoFixEligible:
        cls.status === 'WRONG_LANGUAGE' ||
        cls.status === 'MIXED_LANGUAGE' ||
        shortHeaderEligible,
    })
  }

  return { entries, byStatus }
}

/* -------------------------------------------------------------------------- */
/* SCAN deep (avec affinage LLM batché)                                       */
/* -------------------------------------------------------------------------- */

/**
 * Scan deep : scan local + affinage LLM batché des cas ambigus.
 *
 * Tolérant aux pannes : si `refiner` throw ou retourne `hadError`, le scan
 * local est conservé tel quel.
 */
export async function scanFieldsLanguageDeep(
  fields: GenericFieldInput[],
  targetLocale: Locale,
  options?: { refiner?: BatchLanguageRefiner },
): Promise<GenericScanResult> {
  const refiner = options?.refiner ?? batchClassifyLanguages
  const { entries, byStatus } = scanFieldsLocally(fields, targetLocale)

  const candidates: Array<{ entry: GenericScanEntry; key: string }> = []
  const seenTexts = new Set<string>()
  for (const e of entries) {
    if (!isLLMRefineCandidate(e)) continue
    const text = e.valueExcerpt
    if (!text || text.length < 1) continue
    if (seenTexts.has(text)) continue
    seenTexts.add(text)
    candidates.push({ entry: e, key: `${candidates.length}-${e.hintKey}` })
  }

  const refinement: GenericLLMRefinement = {
    attempted: candidates.length,
    refined: 0,
    tokensUsedApprox: 0,
    callCount: 0,
    hadError: false,
  }

  if (candidates.length === 0) {
    const ok = entries.filter((e) => e.status === 'OK').length
    return {
      targetLocale,
      entries,
      summary: {
        totalFields: entries.length,
        ok,
        needsAttention: entries.length - ok,
        byStatus,
      },
      llmRefinement: refinement,
    }
  }

  let outcome
  try {
    const items: BatchClassifyItem[] = candidates.map((c) => ({
      id: c.key,
      text: c.entry.valueExcerpt,
    }))
    outcome = await refiner(items)
  } catch (err) {
    console.error('[scanFieldsLanguageDeep] refiner threw:', err)
    const ok = entries.filter((e) => e.status === 'OK').length
    return {
      targetLocale,
      entries,
      summary: {
        totalFields: entries.length,
        ok,
        needsAttention: entries.length - ok,
        byStatus,
      },
      llmRefinement: { ...refinement, hadError: true },
    }
  }

  refinement.tokensUsedApprox = outcome.tokensUsedApprox
  refinement.callCount = outcome.callCount
  refinement.hadError = outcome.hadError

  const byKey = new Map(outcome.results.map((r) => [r.id, r]))
  const refinedTexts = new Map<string, { locale: Locale | 'und'; confidence: number }>()
  for (const c of candidates) {
    const r = byKey.get(c.key)
    if (!r) continue
    const changed = applyLLMResultToEntry(c.entry, r, targetLocale)
    if (changed) refinement.refined += 1
    refinedTexts.set(c.entry.valueExcerpt, { locale: r.locale, confidence: r.confidence })
  }

  // Propage la décision LLM aux entries dupliquées (mêmes texte).
  for (const e of entries) {
    if (refinedTexts.has(e.valueExcerpt)) {
      const r = refinedTexts.get(e.valueExcerpt)!
      const changed = applyLLMResultToEntry(e, r, targetLocale)
      if (changed) refinement.refined += 1
    }
  }

  // Recompose `byStatus` après l'affinage.
  const finalByStatus = emptyByStatus()
  for (const e of entries) finalByStatus[e.status] += 1
  const ok = entries.filter((e) => e.status === 'OK').length

  return {
    targetLocale,
    entries,
    summary: {
      totalFields: entries.length,
      ok,
      needsAttention: entries.length - ok,
      byStatus: finalByStatus,
    },
    llmRefinement: refinement,
  }
}

/**
 * Construit la carte `hintKey → Locale` à partir d'un scan deep.
 *
 * Seules les entrées avec une `detectedLocale` exploitable (jamais `und`)
 * contribuent — l'absence de hint laisse l'apply retomber sur sa décision
 * locale par défaut.
 */
export function buildLanguageHintsFromGenericScan(
  scan: GenericScanResult,
): GenericLanguageHints {
  const hints: GenericLanguageHints = new Map()
  for (const e of scan.entries) {
    if (!e.detectedLocale) continue
    hints.set(e.hintKey, e.detectedLocale)
  }
  return hints
}

/* -------------------------------------------------------------------------- */
/* APPLY                                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Décide quelle action prendre pour un champ :
 *   - `null` → pas éligible (OK / MISSING / NON_TRANSLATABLE / NEEDS_REVIEW
 *     non short-header).
 *   - `translate` → on traduit avec `sourceLocale` indiquée.
 *   - `skip` → on n'écrit pas, on reporte la raison.
 *
 * Priorité (haute → basse) :
 *   1. `hint` LLM si présent.
 *   2. `cls.detectedLocale` (franc local).
 *   3. `decideShortHeaderAction` pour les short-headers `NEEDS_REVIEW`.
 *   4. `defaultLocale` en filet (best-effort historique).
 */
function resolveTranslationDecision(
  cls: ReturnType<typeof classifyTextForTargetLocale>,
  field: GenericFieldInput,
  targetLocale: Locale,
  hints: GenericLanguageHints | undefined,
):
  | { action: 'translate'; sourceLocale: Locale }
  | { action: 'skip'; reason: GenericSkippedFieldDiagnostic['reason'] }
  | null {
  const hint = hints?.get(field.hintKey)

  if (hint != null) {
    if (hint === targetLocale) {
      if (cls.status === 'OK' || cls.status === 'MISSING') return null
      return { action: 'skip', reason: 'already_in_target' }
    }
    return { action: 'translate', sourceLocale: hint }
  }

  if (cls.status === 'WRONG_LANGUAGE') {
    const sourceLocale: Locale = cls.detectedLocale ?? (defaultLocale as Locale)
    if (sourceLocale === targetLocale) {
      return { action: 'skip', reason: 'already_in_target' }
    }
    return { action: 'translate', sourceLocale }
  }
  if (cls.status === 'MIXED_LANGUAGE') {
    return { action: 'translate', sourceLocale: defaultLocale as Locale }
  }
  if (cls.status !== 'NEEDS_REVIEW') return null
  if (!field.isShortHeader && !isShortHeaderPath(field.path)) return null
  const decision = decideShortHeaderAction(field.value, targetLocale)
  if (decision.kind === 'translate') {
    return { action: 'translate', sourceLocale: decision.sourceLocale }
  }
  return { action: 'skip', reason: decision.reason }
}

/**
 * Applique les corrections de langue à une liste de champs.
 *
 * Ne persiste rien : retourne `fixedByHintKey: Map<hintKey, newValue>`.
 * L'adaptateur de domain (footer / menu) doit re-projeter ces valeurs
 * dans son schéma de stockage et faire la persistance DB.
 */
export async function applyFieldsLanguageFixes(
  fields: GenericFieldInput[],
  targetLocale: Locale,
  options?: { languageHints?: GenericLanguageHints },
): Promise<GenericApplyResult> {
  const fixedByHintKey = new Map<string, string>()
  const fixedHintKeys: string[] = []
  const skippedFields: GenericSkippedFieldDiagnostic[] = []
  let tokensUsedApprox = 0
  const hints = options?.languageHints

  for (const field of fields) {
    const value = typeof field.value === 'string' ? field.value : ''
    if (!value.trim()) continue

    const cls = classifyTextForTargetLocale(value, targetLocale)
    const decision = resolveTranslationDecision(cls, field, targetLocale, hints)
    if (decision == null) continue
    if (decision.action === 'skip') {
      skippedFields.push({
        hintKey: field.hintKey,
        path: field.path,
        domain: field.domain,
        groupId: field.groupId,
        status: cls.status,
        reason: decision.reason,
        valueExcerpt: excerpt(value),
      })
      continue
    }

    let newText: string
    if (field.kind === 'markdown' || cls.status === 'MIXED_LANGUAGE') {
      const r = await translateMarkdown(value, {
        sourceLocale: decision.sourceLocale,
        targetLocale,
      })
      newText = r.translated
      tokensUsedApprox += r.tokensUsed ?? 0
    } else {
      const r = await translateText(value, {
        sourceLocale: decision.sourceLocale,
        targetLocale,
      })
      newText = r.translated
      tokensUsedApprox += r.tokensUsed ?? 0
    }

    fixedByHintKey.set(field.hintKey, newText)
    fixedHintKeys.push(field.hintKey)
  }

  return {
    fixedByHintKey,
    fixedHintKeys,
    tokensUsedApprox,
    skippedFields,
  }
}
