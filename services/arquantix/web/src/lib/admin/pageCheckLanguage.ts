/**
 * « Vérifier la langue » d'une page CMS — scan + correction DRAFT.
 *
 * Pendant CMS du flux Vault Builder `vaultCheckModuleLanguage.ts` :
 *   1. SCAN : pour la page courante, pour chaque section traduisible (cf.
 *      `SECTION_I18N_POLICIES`), parcours **uniquement** les chemins déclarés
 *      par la politique i18n, classification `franc` via
 *      `classifyTextForTargetLocale`.
 *   2. APPLY : retraduit (OpenAI) :
 *        - les champs `WRONG_LANGUAGE` / `MIXED_LANGUAGE` (cas standard) ;
 *        - en best-effort, les **en-têtes courts** (`eyebrow`, `label`,
 *          `kicker`, `title`, `subtitle`) classés `NEEDS_REVIEW` parce
 *          que trop courts pour la détection trigrammes — cf.
 *          `isShortHeaderPath` plus bas pour le pourquoi détaillé.
 *      Persiste en DRAFT — PUBLISHED inchangé.
 *
 * Allowlist : `SECTION_I18N_POLICIES` (`@/lib/sections/sectionI18nPolicy`)
 * — exactement la même source de vérité que `translateSectionData` pour
 * éviter toute dérive.
 *
 * PageI18n (title / description) est inclus.
 *
 * Périmètre éligible auto-fix :
 * - WRONG_LANGUAGE / MIXED_LANGUAGE : toujours
 * - NEEDS_REVIEW : seulement pour les en-têtes courts (et si
 *   `defaultLocale !== targetLocale`, sinon rien à faire)
 * - OK / MISSING / NON_TRANSLATABLE : jamais
 */

import { franc } from 'franc'

import type { Locale } from '@/config/locales'
import { defaultLocale } from '@/config/locales'

import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import {
  getStringAtLot1Path,
  setStringAtLot1Path,
} from '@/lib/i18n/integrity/fieldPathAccess'
import { prepareTextForLanguageDetection } from '@/lib/i18n/integrity/textPrep'
import type { LinguisticAuditStatus } from '@/lib/i18n/integrity/types'
import {
  batchClassifyLanguages,
  type BatchClassifyItem,
  type BatchLanguageRefiner,
} from '@/lib/i18n/llm/batchClassifyLanguages'
import { expandTranslatablePaths } from '@/lib/i18n/translatablePathExpansion'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import {
  resolveSectionI18nPolicy,
  type ResolvedSectionI18n,
} from '@/lib/sections/sectionI18nPolicy'
import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { translateText } from '@/lib/translate/translateText'

/* -------------------------------------------------------------------------- */
/* Types publics                                                              */
/* -------------------------------------------------------------------------- */

export type PageLanguageTextKind = 'plain' | 'markdown'
export type PageLanguageScope = 'section' | 'page_i18n'

export type PageLanguageScanEntry = {
  /**
   * Chemin lisible et stable.
   * - `pageI18n.title` / `pageI18n.description` pour le scope page_i18n
   * - `data.title` / `data.items[2].question` … pour le scope section
   *   (préfixe `data.` pour rester cohérent avec `domain='cms_section'`)
   */
  path: string
  scope: PageLanguageScope
  textKind: PageLanguageTextKind
  /** id stable de la section concernée (utile pour `builderHref`). */
  sectionId?: string
  sectionKey?: string
  /** Index d'ordre (ordre `Section.order`), utile pour grouper l'UI. */
  sectionIndex?: number
  valueExcerpt: string
  status: LinguisticAuditStatus
  detectedLocale?: Locale
  confidence: number
  suggestedAction?: string
  autoFixEligible: boolean
}

export type PageLanguageScanSummary = {
  totalFields: number
  ok: number
  needsAttention: number
  byStatus: Record<LinguisticAuditStatus, number>
  /** Sections rencontrées pendant le scan, pour debug/UI. */
  sectionsScanned: number
  /** Sections dont la clé n'a pas de politique i18n (ignorées sans planter). */
  sectionsMissingPolicy: Array<{ sectionKey: string; sectionId: string }>
}

export type PageLanguageScanResult = {
  targetLocale: Locale
  entries: PageLanguageScanEntry[]
  summary: PageLanguageScanSummary
}

/**
 * Diagnostic du raffinage LLM appliqué à un scan local.
 *
 * - `attempted` : nombre de champs candidats envoyés au LLM (NEEDS_REVIEW
 *   ou statuts à faible confiance).
 * - `refined` : nombre d'entrées effectivement reclassifiées (statut et/ou
 *   detectedLocale modifiés par rapport au scan local).
 * - `tokensUsedApprox` : approximation des tokens consommés (cumul des batchs).
 * - `callCount` : nombre d'appels OpenAI effectivement émis.
 * - `hadError` : `true` si au moins un batch a échoué (l'appelant doit
 *   afficher un avertissement, le scan reste consommable).
 */
export type PageLanguageLLMRefinement = {
  attempted: number
  refined: number
  tokensUsedApprox: number
  callCount: number
  hadError: boolean
}

export type PageLanguageDeepScanResult = PageLanguageScanResult & {
  llmRefinement: PageLanguageLLMRefinement
}

export type PageSectionInput = {
  id: string
  /** Clé brute en base (`hero`, `cta_2`, `features`, …). */
  key: string
  order: number
  /** `data` JSON brut du `SectionContent` pour la locale cible (DRAFT préféré). */
  data: Record<string, unknown>
}

export type PageI18nInput = {
  title: string | null
  description: string | null
}

/**
 * Diagnostic d'un champ détecté par le scan mais non corrigé par l'apply.
 *
 * Utile pour expliquer à l'opérateur (modale + rapport) pourquoi un champ
 * « visible côté scan » n'a pas été touché — typiquement les en-têtes courts
 * déjà dans la bonne langue, ou indétectables sur la locale par défaut.
 */
export type SkippedFieldDiagnostic = {
  path: string
  scope: PageLanguageScope
  sectionId?: string
  sectionKey?: string
  status: LinguisticAuditStatus
  reason:
    | 'already_in_target'
    | 'undetectable_short_text_on_default_locale'
    | 'not_eligible'
  valueExcerpt: string
}

export type PageLanguageApplyResult = {
  /** Nouveaux objets `data` par section (uniquement celles modifiées). */
  patchedSections: Map<string, Record<string, unknown>>
  /** Nouveaux PageI18n (toujours retourné, valeurs identiques à l'entrée si rien n'a changé). */
  patchedPageI18n: PageI18nInput
  fixedFieldPaths: string[]
  tokensUsedApprox: number
  /**
   * Champs visibles côté scan (allowlist policy) NON modifiés par l'apply, avec
   * raison lisible. Exclut les champs `OK` / `MISSING` / `NON_TRANSLATABLE` qui
   * ne sont jamais censés bouger.
   */
  skippedFields: SkippedFieldDiagnostic[]
}

/* -------------------------------------------------------------------------- */
/* Helpers internes                                                           */
/* -------------------------------------------------------------------------- */

const TEXT_KIND_MARKDOWN_HINTS = ['markdown', 'bodycontent']

function detectTextKindFromPath(path: string, sectionCanonicalKey: string | null): PageLanguageTextKind {
  const lower = path.toLowerCase()
  if (TEXT_KIND_MARKDOWN_HINTS.some((h) => lower.includes(h))) return 'markdown'
  // Heuristiques alignées avec `translateSectionData` :
  // - `cta.description` est traité en markdown
  // - `company_map.bodyContent` aussi (déjà couvert par le hint)
  if (sectionCanonicalKey === 'cta' && /(^|\.)description$/.test(path)) {
    return 'markdown'
  }
  return 'plain'
}

/**
 * Détermine si un path correspond à un champ « court par nature » (en-tête de
 * section : surtitre, titre, label, kicker, sous-titre).
 *
 * Pourquoi c'est important
 * ------------------------
 *
 * Le détecteur de langue (`classifyTextForTargetLocale`) refuse de classer un
 * texte de moins de ~24 caractères et renvoie `NEEDS_REVIEW`. Or les surtitres
 * (`eyebrow`, « TÉMOIGNAGES », « ÉQUIPE », « FAQ »…), labels et titres courts
 * (« Management Team », « Nos dirigeants »…) sont presque toujours sous ce
 * seuil. Sans cette heuristique, ils tombaient dans un trou noir : ni détectés
 * comme `WRONG_LANGUAGE`, ni auto-traduits par `apply` — alors même qu'ils
 * sont déclarés traduisibles dans `SECTION_I18N_POLICIES`.
 *
 * Convention
 * ----------
 *
 * On reconnaît les paths qui se terminent par l'un des noms canoniques :
 * `eyebrow`, `label`, `kicker`, `title`, `subtitle`. La détection ignore les
 * indices de tableau (`items[2].label` matche aussi).
 *
 * Comportement déclenché
 * ----------------------
 *
 * Pour ces paths, si la classification retombe en `NEEDS_REVIEW` ET que la
 * `defaultLocale` (FR) diffère de la `targetLocale`, le scan déclare le champ
 * `autoFixEligible: true` et `apply` le retraduit en best-effort en partant de
 * `defaultLocale`. Si `defaultLocale === targetLocale`, on ne fait rien (pas
 * de surchage du contenu source).
 */
/**
 * Exporté pour réutilisation par le pipeline générique multi-domain
 * (`src/lib/admin/i18n/genericLanguageCheck.ts`) — Footer / Menu / Pages
 * partagent la même règle « court par nature ».
 */
export function isShortHeaderPath(path: string): boolean {
  const lower = path.toLowerCase()
  return /(?:^|[.\]])(eyebrow|label|kicker|title|subtitle)$/.test(lower)
}

/**
 * Décision d'action pour un en-tête court classé `NEEDS_REVIEW`.
 *
 * On évite ici deux pièges connus de l'ancienne logique binaire
 * `defaultLocale !== targetLocale` :
 *
 *   1. **« Court EN sur cible FR » → non corrigé.** L'ancienne règle skippait
 *      tous les courts dès que `target === defaultLocale`, alors qu'un texte
 *      anglais sur la page FR doit être traduit EN→FR.
 *   2. **« Court EN sur cible EN » → traduit dans le mauvais sens.** L'ancienne
 *      règle assumait `sourceLocale = defaultLocale (fr)` et envoyait à OpenAI
 *      « ce texte est en FR, traduis en EN » — résultat aléatoire (souvent du
 *      français généré).
 *
 * On utilise donc `bestEffortDetectShortLocale` qui essaye de classer même les
 * textes courts (franc avec `minLength: 0` + heuristique accents). Si on
 * détecte la locale source avec assez de signal :
 *   - identique à la cible → SKIP (`already_in_target`)
 *   - différente de la cible → TRADUIRE en partant de cette source
 * Si on ne détecte rien :
 *   - cible ≠ defaultLocale → best-effort historique (sourceLocale = defaultLocale)
 *   - cible === defaultLocale → SKIP (`undetectable_short_text_on_default_locale`)
 *     pour éviter une réécriture FR→FR aveugle.
 */
export type ShortHeaderAction =
  | { kind: 'translate'; sourceLocale: Locale }
  | {
      kind: 'skip'
      reason:
        | 'already_in_target'
        | 'undetectable_short_text_on_default_locale'
    }

/**
 * Mots-clés très fréquents par langue (stop-words + verbes/CTA marketing).
 *
 * Volontairement courts et orthogonaux entre les 3 langues : on évite les
 * mots ambigus (« art », « note », …). Un seul match suffit pour incliner
 * fortement la décision — combiné aux autres heuristiques, c'est le signal
 * le plus fiable sur des textes < ~20 caractères où franc se trompe souvent.
 */
const FR_HINT_RE =
  /\b(le|la|les|un|une|des|du|de|et|ou|en|au|aux|pour|avec|sur|sans|dans|par|notre|votre|nos|vos|cette|cet|ces|qui|que|où|plus|moins|très|merci|bonjour|voir|télécharger|contactez|contact|découvrir|notre|nos)\b/i

const EN_HINT_RE =
  /\b(the|and|or|of|to|in|on|for|with|from|by|at|as|is|are|was|were|be|been|our|your|their|this|that|these|those|who|what|when|where|why|how|more|less|very|well|thank|thanks|hello|get|started|learn|view|read|all|new|see|download|contact|discover|team|started|started|sign|up|now|today)\b/i

const IT_HINT_RE =
  /\b(il|lo|gli|della|dei|delle|del|nostro|vostro|nostra|vostra|questo|questa|più|meno|grazie|ciao|inizia|impara|vedi|tutti|nuovi|scarica|contatta|scopri|nostro|nostra)\b/i

/**
 * Détection « best-effort » de la langue d'un texte court.
 *
 * Pourquoi pas juste franc ? franc s'appuie sur des trigrammes ; sur < ~20
 * caractères il se trompe régulièrement (ex. « ÉQUIPE » classé « eng »,
 * « Our Team » classé « und »…). On combine donc trois signaux par ordre de
 * fiabilité décroissante :
 *
 *   1. Accents exclusivement FR (`éèêëàâîïôûùçœ`) → 'fr'. Signal fort
 *      car ces caractères n'apparaissent ni en EN ni en IT.
 *   2. Mots-clés fréquents par langue (stop-words + CTA marketing). Le
 *      score le plus élevé l'emporte ; en cas d'égalité on n'arbitre pas
 *      pour ne pas inventer.
 *   3. franc avec `minLength: 0` en dernier filet — utile sur des textes
 *      modérément courts mais sans accent ni mot reconnu.
 *
 * Retourne `null` si aucun signal n'est exploitable — l'appelant prend
 * alors une décision de sécurité (cf. `decideShortHeaderAction`).
 */
function bestEffortDetectShortLocale(value: string): Locale | null {
  const prepared = prepareTextForLanguageDetection(value)
  if (prepared.length < 2) return null

  // 1. Accents FR (signal exclusif parmi fr/en/it).
  if (/[éèêëàâîïôûùçœÉÈÊËÀÂÎÏÔÛÙÇŒ]/.test(prepared)) return 'fr'

  // 2. Mots-clés fréquents.
  const lower = prepared.toLowerCase()
  const frHits = (lower.match(FR_HINT_RE) || []).length
  const enHits = (lower.match(EN_HINT_RE) || []).length
  const itHits = (lower.match(IT_HINT_RE) || []).length
  const max = Math.max(frHits, enHits, itHits)
  if (max > 0) {
    if (frHits === max && enHits < max && itHits < max) return 'fr'
    if (enHits === max && frHits < max && itHits < max) return 'en'
    if (itHits === max && frHits < max && enHits < max) return 'it'
    // Égalité (ambigu) → on ne tranche pas, on tente franc en filet.
  }

  // 3. franc relâché — dernier filet de sécurité.
  const code = franc(prepared, { only: ['fra', 'eng', 'ita'], minLength: 0 })
  if (code === 'fra') return 'fr'
  if (code === 'eng') return 'en'
  if (code === 'ita') return 'it'

  return null
}

/**
 * Exporté pour pouvoir le tester unitairement (la logique de skip/translate
 * conditionne tout le comportement « court header » de scan + apply).
 * Hors tests : utilisez le scan ou l'apply, pas cette fonction directement.
 */
export function decideShortHeaderAction(
  value: string,
  targetLocale: Locale,
): ShortHeaderAction {
  const detected = bestEffortDetectShortLocale(value)

  if (detected != null && detected === targetLocale) {
    return { kind: 'skip', reason: 'already_in_target' }
  }
  if (detected != null) {
    return { kind: 'translate', sourceLocale: detected }
  }
  if (defaultLocale !== targetLocale) {
    return { kind: 'translate', sourceLocale: defaultLocale as Locale }
  }
  return { kind: 'skip', reason: 'undetectable_short_text_on_default_locale' }
}

/**
 * Décide si un champ classé `NEEDS_REVIEW` est éligible à l'auto-correction
 * via la nouvelle logique `decideShortHeaderAction`.
 *
 * Le scan utilise ce booléen pour piloter `autoFixEligible`, et l'apply
 * réutilise directement `decideShortHeaderAction` pour récupérer en plus la
 * `sourceLocale`. Les deux pipelines partagent ainsi la même règle.
 */
function isShortHeaderAutoFixEligible(
  status: LinguisticAuditStatus,
  fullPath: string,
  value: string,
  targetLocale: Locale,
): boolean {
  if (status !== 'NEEDS_REVIEW') return false
  if (!isShortHeaderPath(fullPath)) return false
  return decideShortHeaderAction(value, targetLocale).kind === 'translate'
}

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

/**
 * Adaptateur autour de `expandTranslatablePaths` qui ré-applique le préfixe
 * `data.` (cohérent avec `setStringAtLot1Path(data, 'cms_section', …)`).
 *
 * Toute la logique d'expansion (multi-`[]`, arrays de strings, tableaux vides…)
 * vit dans `@/lib/i18n/translatablePathExpansion` — partagée avec
 * `translateSectionData` pour éviter les divergences silencieuses.
 */
function expandPathForData(
  data: Record<string, unknown>,
  abstractPath: string,
): string[] {
  return expandTranslatablePaths(data, abstractPath).map((p) => `data.${p}`)
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

/* -------------------------------------------------------------------------- */
/* SCAN                                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Scanne la page (sections + PageI18n) pour la `targetLocale`.
 *
 * - Sections `notTranslatable` : sautées sans bruit (alignement `translateSectionData`).
 * - Sections `missingPolicy` : sautées et listées dans `summary.sectionsMissingPolicy`
 *   (signal pour ajouter une entrée dans `SECTION_I18N_POLICIES`).
 *
 * Aucune écriture, aucune mutation des objets en entrée.
 */
export function scanPageLanguage(
  sections: PageSectionInput[],
  pageI18n: PageI18nInput,
  targetLocale: Locale,
): PageLanguageScanResult {
  const entries: PageLanguageScanEntry[] = []
  const byStatus = emptyByStatus()
  const sectionsMissingPolicy: PageLanguageScanSummary['sectionsMissingPolicy'] = []

  // 1. PageI18n (title / description) — toujours scanné comme `plain`.
  const pageI18nFields: Array<{ path: string; value: string | null }> = [
    { path: 'pageI18n.title', value: pageI18n.title },
    { path: 'pageI18n.description', value: pageI18n.description },
  ]
  for (const f of pageI18nFields) {
    if (typeof f.value !== 'string' || !f.value.trim()) {
      // On ne pousse PAS d'entrée MISSING pour PageI18n (cohérent avec Vault :
      // seul ce qui a une valeur exploitable est classifié). Cela évite du
      // bruit pour des pages où title/description sont volontairement vides.
      continue
    }
    const cls = classifyTextForTargetLocale(f.value, targetLocale)
    byStatus[cls.status] += 1
    // PageI18n.title est court par nature (cf. `isShortHeaderPath`) : on lui
    // applique aussi le best-effort. PageI18n.description peut être plus long,
    // mais s'il retombe en NEEDS_REVIEW, c'est que le texte est trop court de
    // toute façon — même traitement honnête.
    const shortHeaderEligible = isShortHeaderAutoFixEligible(
      cls.status,
      f.path,
      f.value,
      targetLocale,
    )
    entries.push({
      path: f.path,
      scope: 'page_i18n',
      textKind: 'plain',
      valueExcerpt: excerpt(f.value),
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

  // 2. Sections.
  for (const section of sections) {
    const canonicalKey = resolveCanonicalSectionKey(section.key)
    const policy: ResolvedSectionI18n = resolveSectionI18nPolicy(
      section.key,
      canonicalKey,
    )
    if (policy.kind === 'notTranslatable') continue
    if (policy.kind === 'missingPolicy') {
      sectionsMissingPolicy.push({
        sectionKey: section.key,
        sectionId: section.id,
      })
      continue
    }

    for (const abstractPath of policy.paths) {
      const concretePaths = expandPathForData(section.data, abstractPath)
      for (const fullPath of concretePaths) {
        const value = getStringAtLot1Path(section.data, 'cms_section', fullPath)
        if (typeof value !== 'string' || !value.trim()) continue
        const cls = classifyTextForTargetLocale(value, targetLocale)
        byStatus[cls.status] += 1
        const shortHeaderEligible = isShortHeaderAutoFixEligible(
          cls.status,
          fullPath,
          value,
          targetLocale,
        )
        entries.push({
          path: fullPath,
          scope: 'section',
          textKind: detectTextKindFromPath(fullPath, canonicalKey),
          sectionId: section.id,
          sectionKey: section.key,
          sectionIndex: section.order,
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
    }
  }

  const ok = entries.filter((e) => e.status === 'OK').length

  return {
    targetLocale,
    entries,
    summary: {
      totalFields: entries.length,
      ok,
      needsAttention: entries.length - ok,
      byStatus,
      sectionsScanned: sections.length,
      sectionsMissingPolicy,
    },
  }
}

/* -------------------------------------------------------------------------- */
/* HINTS scan ↔ apply                                                         */
/* -------------------------------------------------------------------------- */

/**
 * Carte des langues détectées par le LLM pendant le scan, partagée avec
 * l'apply pour éviter une 2e détection (et garantir la cohérence des
 * décisions sur les textes courts).
 *
 * Clé canonique :
 *   - `pageI18n.title` / `pageI18n.description`
 *   - `${sectionId}::${path}` pour les sections
 *
 * Valeur : la `Locale` détectée (jamais `und` — un `und` LLM n'est pas
 * un hint exploitable et n'est pas inséré).
 */
export type PageLanguageHints = Map<string, Locale>

function makeSectionHintKey(sectionId: string, path: string): string {
  return `${sectionId}::${path}`
}

function makePageI18nHintKey(field: 'title' | 'description'): string {
  return `pageI18n.${field}`
}

/**
 * Construit la `PageLanguageHints` depuis un résultat de scan deep.
 *
 * Seules les entrées dont `detectedLocale` est définie ET fait partie du
 * périmètre supporté contribuent. Les entrées sans détection (ou en `und`)
 * sont laissées hors de la map → l'apply retombe sur sa décision locale.
 */
export function buildLanguageHintsFromScan(
  scan: PageLanguageScanResult,
): PageLanguageHints {
  const hints: PageLanguageHints = new Map()
  for (const e of scan.entries) {
    const loc = e.detectedLocale
    if (!loc) continue
    if (e.scope === 'page_i18n') {
      const field = e.path === 'pageI18n.title' ? 'title' : 'description'
      hints.set(makePageI18nHintKey(field), loc)
    } else if (e.sectionId) {
      hints.set(makeSectionHintKey(e.sectionId, e.path), loc)
    }
  }
  return hints
}

/* -------------------------------------------------------------------------- */
/* SCAN — DEEP (avec affinage LLM des champs ambigus)                         */
/* -------------------------------------------------------------------------- */

/**
 * Critère d'éligibilité d'une entrée au raffinage LLM.
 *
 * On envoie au LLM uniquement les cas où l'heuristique locale s'avoue
 * incapable :
 *   - `NEEDS_REVIEW` (texte court, indéterminé, hors fra/eng/ita)
 *   - `WRONG_LANGUAGE` / `OK` à très faible confiance (< 0.5)
 *
 * Les `MIXED_LANGUAGE` et `MISSING` / `NON_TRANSLATABLE` sont exclus :
 * MIXED est intrinsèquement multilingue (le LLM ne tranchera pas), les
 * autres ne sont pas traduisibles.
 */
function isLLMRefineCandidate(entry: PageLanguageScanEntry): boolean {
  if (entry.status === 'NEEDS_REVIEW') return true
  if (
    (entry.status === 'OK' || entry.status === 'WRONG_LANGUAGE') &&
    entry.confidence < 0.5
  ) {
    return true
  }
  return false
}

/**
 * Recalcule le statut d'une entrée à partir d'une langue détectée par LLM.
 *
 * Conserve la sémantique de `classifyTextForTargetLocale` :
 *   - locale détectée === target  → `OK`
 *   - locale détectée ≠ target    → `WRONG_LANGUAGE` avec `detectedLocale`
 *   - `und`                       → laisse l'entrée intacte (pas un hint)
 */
function applyLLMResultToEntry(
  entry: PageLanguageScanEntry,
  llm: { locale: Locale | 'und'; confidence: number },
  targetLocale: Locale,
): boolean {
  if (llm.locale === 'und') return false

  // Confiance LLM faible : on n'écrase pas l'heuristique locale (souvent
  // elle a déjà donné le bon signal). Seuil délibérément bas pour rester
  // utile sur les textes courts (où le LLM hésite naturellement).
  if (llm.confidence < 0.4) return false

  const newDetected = llm.locale
  const newStatus: LinguisticAuditStatus =
    newDetected === targetLocale ? 'OK' : 'WRONG_LANGUAGE'

  // Aucun changement réel → ne compte pas comme « refined ».
  if (
    entry.status === newStatus &&
    entry.detectedLocale === newDetected
  ) {
    return false
  }

  entry.status = newStatus
  entry.detectedLocale = newDetected
  entry.confidence = Math.max(entry.confidence, llm.confidence)

  // Recalcule autoFixEligible avec la nouvelle classification :
  //   - WRONG_LANGUAGE → toujours éligible
  //   - OK → jamais éligible
  if (newStatus === 'WRONG_LANGUAGE') {
    entry.autoFixEligible = true
    entry.suggestedAction = `Langue détectée (${newDetected}) ≠ locale cible (${targetLocale}) — IA.`
  } else {
    entry.autoFixEligible = false
    entry.suggestedAction = undefined
  }
  return true
}

/**
 * Scan deep : scan local synchrone + raffinage LLM **batché** sur les
 * champs ambigus (NEEDS_REVIEW + faibles confiances).
 *
 * Compatible avec `scanPageLanguage` : la sortie a la même forme + un
 * bloc `llmRefinement` pour la traçabilité dans la modale admin.
 *
 * Tolérant aux pannes : si le refiner throw ou retourne `hadError: true`,
 * le scan local est conservé tel quel (zéro régression vs. avant).
 */
export async function scanPageLanguageDeep(
  sections: PageSectionInput[],
  pageI18n: PageI18nInput,
  targetLocale: Locale,
  options?: {
    /** Permet d'injecter un mock dans les tests (par défaut OpenAI batch). */
    refiner?: BatchLanguageRefiner
  },
): Promise<PageLanguageDeepScanResult> {
  const local = scanPageLanguage(sections, pageI18n, targetLocale)
  const refiner = options?.refiner ?? batchClassifyLanguages

  // Sélection des candidats à l'affinage LLM. On déduplique par `(text,
  // path)` — pour éviter d'envoyer 2 fois le même libellé partagé entre
  // sections.
  const candidates: Array<{ entry: PageLanguageScanEntry; key: string }> = []
  const seenTexts = new Set<string>()
  for (const e of local.entries) {
    if (!isLLMRefineCandidate(e)) continue
    const text = e.valueExcerpt
    if (!text || text.length < 1) continue
    // Clé d'unicité : texte exact (les chemins n'influencent pas la langue).
    if (seenTexts.has(text)) continue
    seenTexts.add(text)
    const key = `${candidates.length}-${e.scope}-${e.sectionId ?? 'page'}`
    candidates.push({ entry: e, key })
  }

  const refinement: PageLanguageLLMRefinement = {
    attempted: candidates.length,
    refined: 0,
    tokensUsedApprox: 0,
    callCount: 0,
    hadError: false,
  }

  if (candidates.length === 0) {
    return { ...local, llmRefinement: refinement }
  }

  let outcome
  try {
    const items: BatchClassifyItem[] = candidates.map((c) => ({
      id: c.key,
      text: c.entry.valueExcerpt,
    }))
    outcome = await refiner(items)
  } catch (err) {
    console.error('[scanPageLanguageDeep] refiner threw:', err)
    return {
      ...local,
      llmRefinement: { ...refinement, hadError: true },
    }
  }

  refinement.tokensUsedApprox = outcome.tokensUsedApprox
  refinement.callCount = outcome.callCount
  refinement.hadError = outcome.hadError

  const byKey = new Map(outcome.results.map((r) => [r.id, r]))

  // Applique aux candidats directs.
  const refinedTexts = new Map<string, { locale: Locale | 'und'; confidence: number }>()
  for (const c of candidates) {
    const r = byKey.get(c.key)
    if (!r) continue
    const changed = applyLLMResultToEntry(c.entry, r, targetLocale)
    if (changed) refinement.refined += 1
    refinedTexts.set(c.entry.valueExcerpt, { locale: r.locale, confidence: r.confidence })
  }

  // Diffusion : un même texte peut apparaître dans plusieurs entries (ex :
  // un eyebrow dupliqué entre 2 sections). On propage la décision LLM à
  // toutes les entries qui partagent exactement la même chaîne.
  for (const e of local.entries) {
    if (refinedTexts.has(e.valueExcerpt)) {
      const r = refinedTexts.get(e.valueExcerpt)!
      const changed = applyLLMResultToEntry(e, r, targetLocale)
      if (changed) refinement.refined += 1
    }
  }

  // Recompose `summary.byStatus` depuis les entries (les statuts ont changé).
  const byStatus = emptyByStatus()
  for (const e of local.entries) byStatus[e.status] += 1
  const ok = local.entries.filter((e) => e.status === 'OK').length
  local.summary.byStatus = byStatus
  local.summary.ok = ok
  local.summary.needsAttention = local.entries.length - ok

  return { ...local, llmRefinement: refinement }
}

/* -------------------------------------------------------------------------- */
/* APPLY                                                                      */
/* -------------------------------------------------------------------------- */

/**
 * Retraduit les champs auto-fix éligibles détectés par `scanPageLanguage`.
 *
 * Éligibilité (cf. doc d'en-tête du module pour le rationale) :
 * - `WRONG_LANGUAGE` / `MIXED_LANGUAGE` → toujours retraduits
 * - `NEEDS_REVIEW` sur en-têtes courts (`eyebrow`, `label`, `kicker`,
 *   `title`, `subtitle`) → retraduits en best-effort à partir de
 *   `defaultLocale`, uniquement si `defaultLocale !== targetLocale`.
 * - `OK` / `MISSING` / `NON_TRANSLATABLE` → jamais modifiés.
 *
 * Source de traduction :
 *   - `WRONG_LANGUAGE` avec `detectedLocale` → langue détectée
 *   - sinon → `defaultLocale` (`fr`) — c'est l'hypothèse de travail.
 *
 * Markdown vs plain : déduit du chemin (`*markdown*`, `bodyContent`,
 * `cta.description`).
 *
 * Aucune mutation des entrées : retourne des **clones** patchés.
 */
export async function applyPageLanguageFixesToDraft(
  sections: PageSectionInput[],
  pageI18n: PageI18nInput,
  targetLocale: Locale,
  options?: {
    /**
     * Carte (path canonique → Locale) issue d'un `scanPageLanguageDeep`.
     * Quand un hint est fourni pour un champ, il a la **priorité absolue**
     * sur la classification locale + `decideShortHeaderAction`. Ça permet
     * à l'apply de bénéficier de la détection LLM sans la rejouer.
     */
    languageHints?: PageLanguageHints
  },
): Promise<PageLanguageApplyResult> {
  const patchedSections = new Map<string, Record<string, unknown>>()
  let patchedPageI18n: PageI18nInput = { ...pageI18n }
  const fixedFieldPaths: string[] = []
  const skippedFields: SkippedFieldDiagnostic[] = []
  let tokensUsedApprox = 0
  const hints = options?.languageHints

  /**
   * Décide la sourceLocale + l'éventuel skip pour un champ déjà classifié.
   * Centralise la logique pour éviter la divergence entre PageI18n et sections.
   *
   * Retourne `null` si le champ n'est pas éligible à l'auto-fix (statut OK,
   * MISSING, NON_TRANSLATABLE, ou NEEDS_REVIEW non short-header).
   *
   * Priorité des sources (de la plus fiable à la moins fiable) :
   *   1. `hints` (LLM scan deep) si présent pour ce path
   *   2. `cls.detectedLocale` (franc local)
   *   3. `decideShortHeaderAction` (heuristique courte)
   *   4. `defaultLocale` (best-effort historique)
   */
  function resolveTranslationDecision(
    cls: ReturnType<typeof classifyTextForTargetLocale>,
    fullPath: string,
    value: string,
    hintKey: string,
  ):
    | { action: 'translate'; sourceLocale: Locale }
    | { action: 'skip'; reason: SkippedFieldDiagnostic['reason'] }
    | null {
    const hint = hints?.get(hintKey)

    // Hint LLM disponible → arbitrage prioritaire, peu importe le statut local.
    if (hint != null) {
      if (hint === targetLocale) {
        // Le LLM dit « déjà dans la bonne langue ». Si l'heuristique locale
        // crie WRONG_LANGUAGE / MIXED on fait quand même confiance au LLM
        // (qui voit le contexte) pour éviter une réécriture EN→EN.
        if (cls.status === 'OK' || cls.status === 'MISSING') return null
        return { action: 'skip', reason: 'already_in_target' }
      }
      // hint ≠ target → on traduit, peu importe le statut local.
      return { action: 'translate', sourceLocale: hint }
    }

    if (cls.status === 'WRONG_LANGUAGE') {
      const sourceLocale: Locale = cls.detectedLocale ?? (defaultLocale as Locale)
      // Filet de sécurité : si la "source détectée" est en réalité égale à la
      // cible (cas pathologique très rare), on n'envoie pas EN→EN.
      if (sourceLocale === targetLocale) {
        return { action: 'skip', reason: 'already_in_target' }
      }
      return { action: 'translate', sourceLocale }
    }
    if (cls.status === 'MIXED_LANGUAGE') {
      // Pour le mixte on garde l'hypothèse defaultLocale (rien de plus fiable
      // sans découper le texte) — comportement historique.
      return {
        action: 'translate',
        sourceLocale: defaultLocale as Locale,
      }
    }
    if (cls.status !== 'NEEDS_REVIEW') return null
    if (!isShortHeaderPath(fullPath)) return null
    const decision = decideShortHeaderAction(value, targetLocale)
    if (decision.kind === 'translate') {
      return { action: 'translate', sourceLocale: decision.sourceLocale }
    }
    return { action: 'skip', reason: decision.reason }
  }

  // 1. PageI18n.
  for (const fieldKey of ['title', 'description'] as const) {
    const value = patchedPageI18n[fieldKey]
    if (typeof value !== 'string' || !value.trim()) continue
    const cls = classifyTextForTargetLocale(value, targetLocale)
    const decision = resolveTranslationDecision(
      cls,
      `pageI18n.${fieldKey}`,
      value,
      makePageI18nHintKey(fieldKey),
    )
    if (decision == null) continue
    if (decision.action === 'skip') {
      skippedFields.push({
        path: `pageI18n.${fieldKey}`,
        scope: 'page_i18n',
        status: cls.status,
        reason: decision.reason,
        valueExcerpt: excerpt(value),
      })
      continue
    }

    // PageI18n est traité comme plain texte (pas de markdown structurel).
    const r = await translateText(value, {
      sourceLocale: decision.sourceLocale,
      targetLocale,
    })
    patchedPageI18n = { ...patchedPageI18n, [fieldKey]: r.translated }
    tokensUsedApprox += r.tokensUsed ?? 0
    fixedFieldPaths.push(`pageI18n.${fieldKey}`)
  }

  // 2. Sections.
  for (const section of sections) {
    const canonicalKey = resolveCanonicalSectionKey(section.key)
    const policy = resolveSectionI18nPolicy(section.key, canonicalKey)
    if (policy.kind !== 'translatable') continue

    let workingData: Record<string, unknown> | null = null

    for (const abstractPath of policy.paths) {
      const concretePaths = expandPathForData(section.data, abstractPath)
      for (const fullPath of concretePaths) {
        const original = getStringAtLot1Path(section.data, 'cms_section', fullPath)
        if (typeof original !== 'string' || !original.trim()) continue
        const cls = classifyTextForTargetLocale(original, targetLocale)
        const decision = resolveTranslationDecision(
          cls,
          fullPath,
          original,
          makeSectionHintKey(section.id, fullPath),
        )
        if (decision == null) continue
        if (decision.action === 'skip') {
          skippedFields.push({
            path: fullPath,
            scope: 'section',
            sectionId: section.id,
            sectionKey: section.key,
            status: cls.status,
            reason: decision.reason,
            valueExcerpt: excerpt(original),
          })
          continue
        }

        const kind = detectTextKindFromPath(fullPath, canonicalKey)

        let newText: string
        if (kind === 'markdown' || cls.status === 'MIXED_LANGUAGE') {
          const r = await translateMarkdown(original, {
            sourceLocale: decision.sourceLocale,
            targetLocale,
          })
          newText = r.translated
          tokensUsedApprox += r.tokensUsed ?? 0
        } else {
          const r = await translateText(original, {
            sourceLocale: decision.sourceLocale,
            targetLocale,
          })
          newText = r.translated
          tokensUsedApprox += r.tokensUsed ?? 0
        }

        if (workingData == null) {
          workingData = cloneJson(section.data)
        }
        const ok = setStringAtLot1Path(workingData, 'cms_section', fullPath, newText)
        if (ok) {
          fixedFieldPaths.push(`sections[${section.id}].${fullPath}`)
        }
      }
    }

    if (workingData != null) {
      patchedSections.set(section.id, workingData)
    }
  }

  return {
    patchedSections,
    patchedPageI18n,
    fixedFieldPaths,
    tokensUsedApprox,
    skippedFields,
  }
}
