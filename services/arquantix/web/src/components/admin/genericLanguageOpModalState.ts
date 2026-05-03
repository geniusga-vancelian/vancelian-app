/**
 * Helpers d'état modale pour les opérations « Vérifier la langue » /
 * « Corriger la langue » génériques (Footer / Menu / autres domains).
 *
 * Pendant CMS de `pageLanguageOpModalState.ts` mais dégénéricisé : pas de
 * notion de section, pas de DRAFT/PUBLISHED. Groupement optionnel par
 * `groupLabel` quand l'adaptateur en fournit un (ex. menu items).
 */

import type { AdminProgressStep } from '@/components/admin/AdminOperationProgressModal'

export type GenericScanModalPayload = {
  result?: {
    entries?: Array<{
      groupId?: string
      groupLabel?: string
      status?: string
    }>
    summary?: {
      totalFields?: number
      ok?: number
      needsAttention?: number
      byStatus?: Record<string, number>
    }
    llmRefinement?: {
      attempted?: number
      refined?: number
      tokensUsedApprox?: number
      callCount?: number
      hadError?: boolean
    }
  }
}

export type GenericApplyModalPayload = {
  fixedFieldPaths?: string[]
  tokensUsedApprox?: number
  applied?: boolean
  skippedFields?: Array<{
    path?: string
    domain?: string
    groupId?: string
    status?: string
    reason?:
      | 'already_in_target'
      | 'undetectable_short_text_on_default_locale'
      | 'not_eligible'
    valueExcerpt?: string
  }>
  llmRefinement?: {
    attempted?: number
    refined?: number
    tokensUsedApprox?: number
    callCount?: number
    hadError?: boolean
  }
}

const SKIP_REASON_LABEL: Record<
  NonNullable<NonNullable<GenericApplyModalPayload['skippedFields']>[number]['reason']>,
  string
> = {
  already_in_target: 'déjà dans la bonne langue (pas besoin de retraduire)',
  undetectable_short_text_on_default_locale:
    'texte court ambigu et locale cible = locale par défaut (pas de référence sûre)',
  not_eligible: 'champ non éligible à l’auto-correction',
}

function groupEntries(
  entries: NonNullable<GenericScanModalPayload['result']>['entries'],
): Map<string, { total: number; ok: number; needsAttention: number; label: string }> {
  const map = new Map<
    string,
    { total: number; ok: number; needsAttention: number; label: string }
  >()
  for (const e of entries ?? []) {
    const groupKey = e.groupId ?? '__global__'
    const label = e.groupLabel ?? 'Champs globaux'
    const cur = map.get(groupKey) ?? { total: 0, ok: 0, needsAttention: 0, label }
    cur.total += 1
    if (e.status === 'OK') cur.ok += 1
    else cur.needsAttention += 1
    cur.label = label
    map.set(groupKey, cur)
  }
  return map
}

export function buildGenericScanSuccessModal(
  payload: GenericScanModalPayload,
  domainLabel: string,
  localeLabel: string,
): { steps: AdminProgressStep[]; summaryLines: string[] } {
  const result = payload.result
  const entries = result?.entries ?? []
  const summary = result?.summary
  const totalFields = summary?.totalFields ?? entries.length
  const ok = summary?.ok ?? 0
  const needsAttention = summary?.needsAttention ?? Math.max(0, totalFields - ok)
  const byStatus = summary?.byStatus

  const groupMap = groupEntries(entries)
  const groupKeys = [...groupMap.keys()].sort((a, b) => {
    if (a === '__global__') return -1
    if (b === '__global__') return 1
    return a.localeCompare(b, 'fr')
  })
  const MAX_ROWS = 12
  const shown = groupKeys.slice(0, MAX_ROWS)
  const hidden = groupKeys.slice(MAX_ROWS)
  let hiddenAgg = { total: 0, ok: 0, needsAttention: 0 }
  for (const k of hidden) {
    const g = groupMap.get(k)!
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
      label: `Lecture du ${domainLabel}`,
      detail: `Locale ${localeLabel}`,
      status: 'success',
    },
    {
      id: 'fields',
      label: 'Lecture et classification des champs traduisibles',
      detail: `${totalFields} champ(s) analysé(s)`,
      status: 'success',
    },
  ]

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

  for (const key of shown) {
    const g = groupMap.get(key)!
    const st: AdminProgressStep['status'] = g.needsAttention === 0 ? 'success' : 'warning'
    steps.push({
      id: `grp-${key}`,
      label: g.label,
      detail:
        g.needsAttention === 0
          ? `${g.total} champ(s) — tout OK`
          : `${g.total} champ(s) — ${g.needsAttention} à surveiller / hors OK`,
      status: st,
    })
  }
  if (hidden.length > 0) {
    steps.push({
      id: 'grp-more',
      label: `Autres groupes (${hidden.length})`,
      detail:
        hiddenAgg.needsAttention === 0
          ? `${hiddenAgg.total} champ(s) — tout OK`
          : `${hiddenAgg.total} champ(s) — ${hiddenAgg.needsAttention} à surveiller`,
      status: hiddenAgg.needsAttention === 0 ? 'success' : 'warning',
    })
  }

  steps.push({
    id: 'done',
    label: 'Synthèse',
    detail: 'Analyse terminée — voir le rapport ci-dessous',
    status: 'success',
  })

  const summaryLines = [
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

  return { steps, summaryLines }
}

export function buildGenericApplySuccessModal(
  payload: GenericApplyModalPayload,
  domainLabel: string,
  localeLabel: string,
): { steps: AdminProgressStep[]; summaryLines: string[]; footerHint?: string } {
  const fixed = Array.isArray(payload.fixedFieldPaths) ? payload.fixedFieldPaths.length : 0
  const tokens = typeof payload.tokensUsedApprox === 'number' ? payload.tokensUsedApprox : 0
  const skipped = Array.isArray(payload.skippedFields) ? payload.skippedFields : []

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
      label: `Lecture du ${domainLabel} source`,
      detail: `Locale ${localeLabel} — champs éligibles uniquement`,
      status: 'success',
    },
  ]

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
        ? `${fixed} champ(s) retraduit(s) (WRONG_LANGUAGE / MIXED_LANGUAGE / en-têtes courts éligibles)`
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
      label: `Enregistrement du ${domainLabel}`,
      detail: 'Persistance immédiate (pas de notion DRAFT/PUBLISHED)',
      status: 'success',
    },
  )

  const summaryLines = [
    `Correction terminée pour ${localeLabel}.`,
    `${fixed} champ(s) retraduit(s).`,
  ]
  if (skipped.length > 0) {
    summaryLines.push(
      `${skipped.length} champ(s) ignoré(s) avec raison (voir étape « Champs ignorés »).`,
    )
  }

  return {
    steps,
    summaryLines,
    footerHint: 'Les champs courts indétectables ne sont pas modifiés automatiquement.',
  }
}

export function initialGenericScanRunningSteps(
  domainLabel: string,
  localeLabel: string,
): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: `Lecture du ${domainLabel}`,
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'scan',
      label: 'Classification linguistique par champ',
      status: 'pending',
    },
    {
      id: 'llm-refine',
      label: 'Affinage IA des champs ambigus',
      detail: 'Appel OpenAI batché pour les textes courts / faibles confiances (le cas échéant)',
      status: 'pending',
    },
    {
      id: 'done',
      label: 'Synthèse',
      status: 'pending',
    },
  ]
}

export function initialGenericApplyRunningSteps(
  domainLabel: string,
  localeLabel: string,
): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: `Lecture du ${domainLabel}`,
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'fix',
      label: 'Retraduction des champs éligibles',
      status: 'pending',
    },
    {
      id: 'save',
      label: `Enregistrement du ${domainLabel}`,
      status: 'pending',
    },
  ]
}
