/**
 * Helpers d'état pour la modale de progression du Page Editor
 * « Vérifier la langue » + « Corriger le brouillon ».
 *
 * Pendant CMS du fichier `vaultLanguageOpModalState.ts` (Vault Builder), mais
 * groupement par **section** (clé) au lieu de **module** (type) pour coller
 * au modèle Page + Section[].
 */

import type { AdminProgressStep } from '@/components/admin/AdminOperationProgressModal'

type PageScanPayload = {
  contentLayerSummary?: {
    draftSections?: number
    publishedSections?: number
    missingSections?: number
  }
  result?: {
    entries?: Array<{
      sectionKey?: string
      scope?: string
      status?: string
    }>
    summary?: {
      totalFields?: number
      ok?: number
      needsAttention?: number
      byStatus?: Record<string, number>
      sectionsScanned?: number
      sectionsMissingPolicy?: Array<{ sectionKey?: string; sectionId?: string }>
    }
    /**
     * Diagnostic du raffinage LLM (présent uniquement quand le scan a fait
     * appel à OpenAI pour reclassifier les champs ambigus).
     */
    llmRefinement?: {
      attempted?: number
      refined?: number
      tokensUsedApprox?: number
      callCount?: number
      hadError?: boolean
    }
  }
}

function groupEntriesBySection(
  entries: NonNullable<PageScanPayload['result']>['entries'],
): Map<string, { total: number; ok: number; needsAttention: number }> {
  const map = new Map<string, { total: number; ok: number; needsAttention: number }>()
  for (const e of entries ?? []) {
    const key =
      e.scope === 'page_i18n'
        ? 'Métadonnées de page (PageI18n)'
        : (e.sectionKey ?? 'Section inconnue')
    const cur = map.get(key) ?? { total: 0, ok: 0, needsAttention: 0 }
    cur.total += 1
    if (e.status === 'OK') cur.ok += 1
    else cur.needsAttention += 1
    map.set(key, cur)
  }
  return map
}

export function buildPageScanSuccessModal(
  payload: PageScanPayload,
  localeLabel: string,
  pageSlug?: string,
): {
  steps: AdminProgressStep[]
  summaryLines: string[]
  footerHint?: string
} {
  const result = payload.result
  const entries = result?.entries ?? []
  const summary = result?.summary
  const layers = payload.contentLayerSummary
  const draftN = layers?.draftSections ?? 0
  const publishedN = layers?.publishedSections ?? 0
  const missingN = layers?.missingSections ?? 0
  const layerLabel =
    draftN > 0 && publishedN === 0
      ? `${draftN} section(s) brouillon`
      : publishedN > 0 && draftN === 0
        ? `${publishedN} section(s) publiées (pas de brouillon)`
        : `${draftN} brouillon · ${publishedN} publié`

  const totalFields = summary?.totalFields ?? entries.length
  const ok = summary?.ok ?? 0
  const needsAttention = summary?.needsAttention ?? Math.max(0, totalFields - ok)
  const byStatus = summary?.byStatus
  const sectionsMissingPolicy = summary?.sectionsMissingPolicy ?? []

  const sectionMap = groupEntriesBySection(entries)
  const sectionNames = [...sectionMap.keys()].sort((a, b) => a.localeCompare(b, 'fr'))
  const MAX_ROWS = 18
  const shown = sectionNames.slice(0, MAX_ROWS)
  const hidden = sectionNames.slice(MAX_ROWS)
  let hiddenAgg = { total: 0, ok: 0, needsAttention: 0 }
  for (const name of hidden) {
    const g = sectionMap.get(name)!
    hiddenAgg = {
      total: hiddenAgg.total + g.total,
      ok: hiddenAgg.ok + g.ok,
      needsAttention: hiddenAgg.needsAttention + g.needsAttention,
    }
  }

  const llm = result?.llmRefinement
  const llmAttempted = llm?.attempted ?? 0
  const llmRefined = llm?.refined ?? 0
  const llmTokens = llm?.tokensUsedApprox ?? 0
  const llmCalls = llm?.callCount ?? 0
  const llmHadError = llm?.hadError === true

  const steps: AdminProgressStep[] = [
    {
      id: 'read',
      label: 'Chargement des sections de la page',
      detail: `${layerLabel} — locale ${localeLabel}${
        missingN > 0 ? ` · ${missingN} section(s) sans contenu pour cette locale` : ''
      }`,
      status: 'success',
    },
    {
      id: 'fields',
      label: 'Lecture et classification des champs traduisibles',
      detail: `${totalFields} champ(s) analysé(s) (allowlist sectionI18nPolicy)`,
      status: 'success',
    },
  ]

  // Étape « affinage IA » — visible quand le scan a fait au moins un appel
  // OpenAI (cas standard sur une page avec au moins un texte court ambigu).
  // Statut :
  //   - warning  → l'appel OpenAI a échoué, scan retombé sur l'heuristique
  //   - success  → reclassification réussie
  // L'absence d'étape signifie qu'aucun champ ambigu n'a été trouvé (rien
  // à raffiner) — auquel cas le scan local est suffisant à 100 %.
  if (llm && llmAttempted > 0) {
    let detail: string
    if (llmHadError) {
      detail = `Appel OpenAI en échec — ${llmAttempted} champ(s) ambigu(s) gardent leur classification heuristique locale.`
    } else if (llmRefined > 0) {
      detail = `${llmAttempted} champ(s) ambigu(s) envoyé(s) à OpenAI (${llmCalls} appel(s) batché(s), ≈ ${llmTokens} tokens) — ${llmRefined} reclassifié(s).`
    } else {
      detail = `${llmAttempted} champ(s) ambigu(s) envoyé(s) à OpenAI (${llmCalls} appel(s) batché(s), ≈ ${llmTokens} tokens) — heuristique locale confirmée.`
    }
    steps.push({
      id: 'llm-refine',
      label: 'Affinage IA des champs ambigus',
      detail,
      status: llmHadError ? 'warning' : 'success',
    })
  }

  for (const name of shown) {
    const g = sectionMap.get(name)!
    const st: AdminProgressStep['status'] = g.needsAttention === 0 ? 'success' : 'warning'
    steps.push({
      id: `sec-${name}`,
      label: `Section ${name}`,
      detail:
        g.needsAttention === 0
          ? `${g.total} champ(s) — tout OK`
          : `${g.total} champ(s) — ${g.needsAttention} à surveiller / hors OK`,
      status: st,
    })
  }

  if (hidden.length > 0) {
    steps.push({
      id: 'sec-more',
      label: `Autres sections (${hidden.length} type(s))`,
      detail:
        hiddenAgg.needsAttention === 0
          ? `${hiddenAgg.total} champ(s) — tout OK`
          : `${hiddenAgg.total} champ(s) — ${hiddenAgg.needsAttention} à surveiller`,
      status: hiddenAgg.needsAttention === 0 ? 'success' : 'warning',
    })
  }

  if (sectionsMissingPolicy.length > 0) {
    steps.push({
      id: 'missing-policy',
      label: 'Politiques i18n manquantes',
      detail: `${sectionsMissingPolicy.length} clé(s) sans entrée dans sectionI18nPolicy.ts (champs ignorés du scan)`,
      status: 'warning',
    })
  }

  steps.push({
    id: 'done',
    label: 'Synthèse',
    detail: 'Analyse terminée — voir le rapport ci-dessous',
    status: 'success',
  })

  const summaryLines: string[] = [
    `Analyse terminée pour ${localeLabel}.`,
    `${totalFields} champ(s) parcourus (${ok} OK).`,
    `${needsAttention} champ(s) hors OK (à surveiller ou relecture).`,
  ]
  if (byStatus && typeof byStatus === 'object') {
    const parts = Object.entries(byStatus)
      .filter(([, n]) => typeof n === 'number' && n > 0)
      .map(([k, n]) => `${k}: ${n}`)
    if (parts.length) summaryLines.push(`Répartition : ${parts.join(', ')}.`)
  }
  if (llm && llmAttempted > 0) {
    if (llmHadError) {
      summaryLines.push(
        `Affinage IA partiel : OpenAI indisponible — ${llmAttempted} champ(s) ambigu(s) gardent leur classification heuristique.`,
      )
    } else {
      summaryLines.push(
        `Affinage IA : ${llmRefined} champ(s) reclassifié(s) sur ${llmAttempted} candidat(s) (≈ ${llmTokens} tokens).`,
      )
    }
  }

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Rapport détaillé : section « Langue de la page » sur cette page (slug ${pageSlug}).`
      : 'Rapport détaillé : section « Langue de la page » sur cet écran.',
  }
}

type PageApplyPayload = {
  fixedFieldPaths?: string[]
  tokensUsedApprox?: number
  patchedSectionCount?: number
  /**
   * Champs détectés par le scan mais NON corrigés par l'apply, avec raison.
   * Permet d'expliquer à l'opérateur pourquoi un champ « visible côté scan »
   * n'a pas bougé (cf. `SkippedFieldDiagnostic` dans `pageCheckLanguage.ts`).
   */
  skippedFields?: Array<{
    path?: string
    scope?: string
    sectionId?: string
    sectionKey?: string
    status?: string
    reason?:
      | 'already_in_target'
      | 'undetectable_short_text_on_default_locale'
      | 'not_eligible'
    valueExcerpt?: string
  }>
  scanAfter?: PageScanPayload['result']
  /**
   * Diagnostic du raffinage LLM utilisé pour piloter les hints scan→apply
   * (cf. `scanPageLanguageDeep`). Affiché dans la modale d'apply pour
   * expliquer la qualité de la classification utilisée.
   */
  llmRefinement?: {
    attempted?: number
    refined?: number
    tokensUsedApprox?: number
    callCount?: number
    hadError?: boolean
  }
}

const SKIP_REASON_LABEL: Record<
  NonNullable<NonNullable<PageApplyPayload['skippedFields']>[number]['reason']>,
  string
> = {
  already_in_target:
    'déjà dans la bonne langue (pas besoin de retraduire)',
  undetectable_short_text_on_default_locale:
    'texte court ambigu et locale cible = locale par défaut (pas de référence sûre)',
  not_eligible: 'champ non éligible à l’auto-correction',
}

export function buildPageApplySuccessModal(
  payload: PageApplyPayload,
  localeLabel: string,
  pageSlug?: string,
): { steps: AdminProgressStep[]; summaryLines: string[]; footerHint?: string } {
  const fixed = Array.isArray(payload.fixedFieldPaths) ? payload.fixedFieldPaths.length : 0
  const patchedSections =
    typeof payload.patchedSectionCount === 'number' ? payload.patchedSectionCount : 0
  const tokens = typeof payload.tokensUsedApprox === 'number' ? payload.tokensUsedApprox : 0
  const scanAfter = payload.scanAfter
  const afterAttention = scanAfter?.summary?.needsAttention ?? 0
  const skipped = Array.isArray(payload.skippedFields) ? payload.skippedFields : []

  // Comptage par raison pour synthétiser l'étape « ignorés » sans noyer
  // l'opérateur sous une longue liste de chemins.
  const skippedByReason = new Map<string, number>()
  for (const s of skipped) {
    if (!s.reason) continue
    skippedByReason.set(s.reason, (skippedByReason.get(s.reason) ?? 0) + 1)
  }

  const llm = payload.llmRefinement
  const llmAttempted = llm?.attempted ?? 0
  const llmRefined = llm?.refined ?? 0
  const llmTokens = llm?.tokensUsedApprox ?? 0
  const llmHadError = llm?.hadError === true

  const steps: AdminProgressStep[] = [
    {
      id: 'read',
      label: 'Lecture des sections + PageI18n source',
      detail: `Locale ${localeLabel} — champs éligibles uniquement`,
      status: 'success',
    },
  ]

  // Étape « affinage IA » exposée AVANT la retraduction : c'est cette
  // détection LLM qui pilote le sens des traductions (sourceLocale).
  // Indispensable pour la traçabilité « pourquoi cet apply a-t-il choisi
  // de traduire X en partant de Y ? ».
  if (llm && llmAttempted > 0) {
    let detail: string
    if (llmHadError) {
      detail = `Appel OpenAI en échec — apply a utilisé l'heuristique locale comme source pour ${llmAttempted} champ(s) ambigu(s).`
    } else if (llmRefined > 0) {
      detail = `${llmRefined} champ(s) ambigu(s) reclassifié(s) par OpenAI sur ${llmAttempted} candidat(s) (≈ ${llmTokens} tokens) — utilisé comme hint d'orientation.`
    } else {
      detail = `${llmAttempted} champ(s) ambigu(s) envoyé(s) à OpenAI (≈ ${llmTokens} tokens) — heuristique locale confirmée.`
    }
    steps.push({
      id: 'llm-refine',
      label: 'Détection IA pour orienter la retraduction',
      detail,
      status: llmHadError ? 'warning' : 'success',
    })
  }

  steps.push({
    id: 'fix',
    label: 'Retraduction des champs détectés',
    detail:
      fixed > 0
        ? `${fixed} champ(s) retraduit(s) sur ${patchedSections} section(s) (WRONG_LANGUAGE / MIXED_LANGUAGE / en-têtes courts éligibles)`
        : 'Aucun champ éligible — rien à modifier',
    status: fixed > 0 ? 'success' : 'warning',
  })

  if (skipped.length > 0) {
    const reasonParts = [...skippedByReason.entries()].map(
      ([reason, n]) =>
        `${n} × ${SKIP_REASON_LABEL[reason as keyof typeof SKIP_REASON_LABEL] ?? reason}`,
    )
    steps.push({
      id: 'skipped',
      label: 'Champs ignorés (diagnostic)',
      detail: `${skipped.length} champ(s) détecté(s) côté scan mais non modifié(s) — ${reasonParts.join(' · ')}`,
      status: 'warning',
    })
  }

  steps.push(
    {
      id: 'tokens',
      label: 'Contrôle des appels de traduction',
      detail: tokens > 0 ? `≈ ${tokens} tokens (estimation)` : 'Pas d’appel facturé',
      status: 'success',
    },
    {
      id: 'save',
      label: 'Enregistrement du brouillon',
      detail: 'DRAFT (SectionContent + PageI18n) — PUBLISHED inchangé',
      status: 'success',
    },
    {
      id: 'rescan',
      label: 'Scan post-correction',
      detail:
        afterAttention > 0
          ? `${afterAttention} champ(s) encore à surveiller (dont NEEDS_REVIEW non modifiés)`
          : 'Aucun point bloquant restant dans le scan',
      status: afterAttention > 0 ? 'warning' : 'success',
    },
  )

  const summaryLines = [
    `Correction terminée pour ${localeLabel}.`,
    `${fixed} champ(s) retraduit(s) sur ${patchedSections} section(s).`,
    `${afterAttention} champ(s) encore signalé(s) par le scan (relecture possible).`,
  ]
  if (skipped.length > 0) {
    summaryLines.push(
      `${skipped.length} champ(s) ignoré(s) avec raison (voir étape « Champs ignorés »).`,
    )
  }

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Brouillon mis à jour — slug ${pageSlug}. Les champs NEEDS_REVIEW trop courts ne sont pas modifiés automatiquement.`
      : 'Les champs NEEDS_REVIEW trop courts ne sont pas modifiés automatiquement.',
  }
}

export function initialPageScanRunningSteps(localeLabel: string): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: 'Lecture des sections de la page',
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'scan',
      label: 'Classification linguistique par champ',
      detail: 'Parcours de tous les champs allowlistés (sectionI18nPolicy)',
      status: 'pending',
    },
    {
      id: 'llm-refine',
      label: 'Affinage IA des champs ambigus',
      detail:
        'Appel OpenAI batché pour les textes courts / faibles confiances (le cas échéant)',
      status: 'pending',
    },
    {
      id: 'done',
      label: 'Synthèse',
      detail: 'Préparation du rapport',
      status: 'pending',
    },
  ]
}

export function initialPageApplyRunningSteps(localeLabel: string): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: 'Lecture du brouillon',
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'fix',
      label: 'Retraduction des champs éligibles',
      detail: 'WRONG_LANGUAGE / MIXED_LANGUAGE uniquement',
      status: 'pending',
    },
    {
      id: 'save',
      label: 'Enregistrement du brouillon',
      status: 'pending',
    },
    {
      id: 'rescan',
      label: 'Scan post-correction',
      status: 'pending',
    },
  ]
}
