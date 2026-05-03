import type { AdminProgressStep } from '@/components/admin/AdminOperationProgressModal'

type ScanPayload = {
  contentLayerRead?: string
  result?: {
    entries?: Array<{
      moduleType?: string
      status?: string
    }>
    summary?: {
      totalFields?: number
      ok?: number
      needsAttention?: number
      byStatus?: Record<string, number>
    }
    integrity?: {
      suspiciousCount?: number
      byStatus?: Record<string, number>
    }
  }
}

function groupEntriesByModule(
  entries: NonNullable<ScanPayload['result']>['entries'],
): Map<string, { total: number; ok: number; needsAttention: number }> {
  const map = new Map<string, { total: number; ok: number; needsAttention: number }>()
  for (const e of entries ?? []) {
    const key = e.moduleType ?? 'Métadonnées / PageI18n'
    const cur = map.get(key) ?? { total: 0, ok: 0, needsAttention: 0 }
    cur.total += 1
    if (e.status === 'OK') cur.ok += 1
    else cur.needsAttention += 1
    map.set(key, cur)
  }
  return map
}

export function buildVaultScanSuccessModal(
  payload: ScanPayload,
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
  const layer =
    payload.contentLayerRead === 'published'
      ? 'Version publiée (pas de brouillon)'
      : payload.contentLayerRead === 'draft'
        ? 'Brouillon'
        : 'Contenu'
  const totalFields = summary?.totalFields ?? entries.length
  const ok = summary?.ok ?? 0
  const needsAttention = summary?.needsAttention ?? Math.max(0, totalFields - ok)
  const byStatus = summary?.byStatus

  const moduleMap = groupEntriesByModule(entries)
  const moduleNames = [...moduleMap.keys()].sort((a, b) => a.localeCompare(b, 'fr'))
  const MAX_MODULE_ROWS = 18
  const shown = moduleNames.slice(0, MAX_MODULE_ROWS)
  const hidden = moduleNames.slice(MAX_MODULE_ROWS)
  let hiddenAgg = { total: 0, ok: 0, needsAttention: 0 }
  for (const name of hidden) {
    const g = moduleMap.get(name)!
    hiddenAgg = {
      total: hiddenAgg.total + g.total,
      ok: hiddenAgg.ok + g.ok,
      needsAttention: hiddenAgg.needsAttention + g.needsAttention,
    }
  }

  const steps: AdminProgressStep[] = [
    {
      id: 'read',
      label: 'Chargement du brouillon cible',
      detail: `${layer} — locale ${localeLabel}`,
      status: 'success',
    },
    {
      id: 'fields',
      label: 'Lecture et classification des champs',
      detail: `${totalFields} champ(s) allowlisté(s) analysé(s)`,
      status: 'success',
    },
  ]

  for (const name of shown) {
    const g = moduleMap.get(name)!
    const st: AdminProgressStep['status'] = g.needsAttention === 0 ? 'success' : 'warning'
    steps.push({
      id: `mod-${name}`,
      label: `Module ${name}`,
      detail:
        g.needsAttention === 0
          ? `${g.total} champ(s) — tout OK`
          : `${g.total} champ(s) — ${g.needsAttention} à surveiller / hors OK`,
      status: st,
    })
  }

  if (hidden.length > 0) {
    steps.push({
      id: 'mod-more',
      label: `Autres modules (${hidden.length} type(s))`,
      detail:
        hiddenAgg.needsAttention === 0
          ? `${hiddenAgg.total} champ(s) — tout OK`
          : `${hiddenAgg.total} champ(s) — ${hiddenAgg.needsAttention} à surveiller`,
      status: hiddenAgg.needsAttention === 0 ? 'success' : 'warning',
    })
  }

  const integSusp = result?.integrity?.suspiciousCount ?? 0
  steps.push({
    id: 'integrity',
    label: "Vérification d'intégrité (vault)",
    detail:
      integSusp > 0
        ? `${integSusp} point(s) signalé(s) (hors statut OK)`
        : 'Aucun écart structurel signalé',
    status: integSusp > 0 ? 'warning' : 'success',
  })

  steps.push({
    id: 'done',
    label: 'Synthèse',
    detail: 'Analyse terminée — voir le résumé ci-dessous',
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

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Rapport détaillé : section « Langue des modules » sur cette page (slug ${pageSlug}).`
      : 'Rapport détaillé : section « Langue des modules » sur cet écran.',
  }
}

type ApplyPayload = {
  fixedFieldPaths?: string[]
  tokensUsedApprox?: number
  scanAfter?: ScanPayload['result']
  verifyAfter?: { suspiciousCount?: number }
}

export function buildVaultApplySuccessModal(
  payload: ApplyPayload,
  localeLabel: string,
  pageSlug?: string,
): { steps: AdminProgressStep[]; summaryLines: string[]; footerHint?: string } {
  const fixed = Array.isArray(payload.fixedFieldPaths) ? payload.fixedFieldPaths.length : 0
  const tokens = typeof payload.tokensUsedApprox === 'number' ? payload.tokensUsedApprox : 0
  const scanAfter = payload.scanAfter
  const afterSusp = scanAfter?.summary?.needsAttention ?? 0
  const verifySusp = payload.verifyAfter?.suspiciousCount

  const steps: AdminProgressStep[] = [
    {
      id: 'read',
      label: 'Lecture du brouillon source',
      detail: `Locale ${localeLabel} — champs éligibles uniquement`,
      status: 'success',
    },
    {
      id: 'fix',
      label: 'Retraduction des champs détectés',
      detail:
        fixed > 0
          ? `${fixed} champ(s) retraduit(s) (WRONG_LANGUAGE / MIXED_LANGUAGE)`
          : 'Aucun champ éligible — rien à modifier',
      status: fixed > 0 ? 'success' : 'warning',
    },
    {
      id: 'tokens',
      label: 'Contrôle des appels de traduction',
      detail: tokens > 0 ? `≈ ${tokens} tokens (estimation)` : 'Pas d’appel facturé',
      status: 'success',
    },
    {
      id: 'save',
      label: 'Enregistrement du brouillon',
      detail: 'DRAFT + PageI18n — PUBLISHED inchangé',
      status: 'success',
    },
    {
      id: 'rescan',
      label: 'Scan post-correction',
      detail:
        afterSusp > 0
          ? `${afterSusp} champ(s) encore à surveiller (dont NEEDS_REVIEW non modifiés)`
          : 'Aucun point bloquant restant dans le scan',
      status: afterSusp > 0 ? 'warning' : 'success',
    },
  ]

  if (typeof verifySusp === 'number') {
    steps.push({
      id: 'verify',
      label: 'Vérification d’intégrité post-correction',
      detail:
        verifySusp > 0
          ? `${verifySusp} point(s) à relire (cohérence vault)`
          : 'Cohérence : RAS',
      status: verifySusp > 0 ? 'warning' : 'success',
    })
  }

  const summaryLines = [
    `Correction terminée pour ${localeLabel}.`,
    `${fixed} champ(s) retraduit(s).`,
    `${afterSusp} champ(s) encore signalé(s) par le scan (relecture possible).`,
  ]

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Brouillon rechargé — slug ${pageSlug}. Les champs NEEDS_REVIEW trop courts ne sont pas modifiés automatiquement.`
      : 'Les champs NEEDS_REVIEW trop courts ne sont pas modifiés automatiquement.',
  }
}

type AutoTranslatePayload = {
  phases?: {
    copy?: { frSource?: string }
    translate?: { fieldsTranslated?: number; tokensUsedApprox?: number }
    verify?: {
      suspiciousCount?: number
      totalFindings?: number
      sampleFindings?: Array<{ fieldPath?: string; status?: string }>
    }
  }
}

export function buildAutoTranslateSuccessModal(
  payload: AutoTranslatePayload,
  localeLabel: string,
  pageSlug?: string,
): { steps: AdminProgressStep[]; summaryLines: string[]; footerHint?: string } {
  const copy = payload.phases?.copy
  const tr = payload.phases?.translate
  const vf = payload.phases?.verify
  const nFields = typeof tr?.fieldsTranslated === 'number' ? tr.fieldsTranslated : 0
  const tokens = typeof tr?.tokensUsedApprox === 'number' ? tr.tokensUsedApprox : 0
  const susp = typeof vf?.suspiciousCount === 'number' ? vf.suspiciousCount : 0
  const totalFind = typeof vf?.totalFindings === 'number' ? vf.totalFindings : 0
  const frKind = copy?.frSource === 'published' ? 'FR publié (pas de brouillon FR)' : 'FR brouillon'

  const steps: AdminProgressStep[] = [
    {
      id: 'copy',
      label: 'Lecture du contenu français source',
      detail: frKind,
      status: 'success',
    },
    {
      id: 'translate',
      label: 'Traduction OpenAI (allowlist)',
      detail:
        nFields > 0
          ? `${nFields} champ(s) traduit(s)${tokens > 0 ? ` — ≈ ${tokens} tokens` : ''}`
          : 'Aucun champ traduit (contenu déjà vide ou filtré)',
      status: nFields > 0 ? 'success' : 'warning',
    },
    {
      id: 'verify',
      label: 'Vérification linguistique automatique',
      detail:
        susp > 0
          ? `${susp} point(s) à relire sur ${totalFind} contrôle(s)`
          : 'Aucune ambiguïté signalée',
      status: susp > 0 ? 'warning' : 'success',
    },
    {
      id: 'persist',
      label: 'Enregistrement du brouillon cible',
      detail: `Locale ${localeLabel} — DRAFT uniquement`,
      status: 'success',
    },
  ]

  const summaryLines = [
    `Auto-traduction FR → ${localeLabel} terminée.`,
    `${nFields} champ(s) traduit(s).`,
    `${susp} point(s) à relire (vérification auto).`,
  ]

  const samples = vf?.sampleFindings?.slice(0, 3) ?? []
  if (samples.length) {
    summaryLines.push(
      `Exemples : ${samples.map((s) => `${s.fieldPath ?? '?'} (${s.status ?? '?'})`).join(' ; ')}.`,
    )
  }

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Brouillon ${localeLabel} mis à jour — ${pageSlug}. Relecture humaine recommandée.`
      : 'Relecture humaine recommandée.',
  }
}

export function initialScanRunningSteps(localeLabel: string): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: 'Lecture du brouillon cible',
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'scan',
      label: 'Classification linguistique par champ',
      detail: 'Parcours de tous les champs allowlistés',
      status: 'pending',
    },
    {
      id: 'integrity',
      label: "Vérification d'intégrité",
      detail: 'Cohérence du vault',
      status: 'pending',
    },
  ]
}

export function initialApplyRunningSteps(localeLabel: string): AdminProgressStep[] {
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

export function initialAutoTranslateRunningSteps(localeLabel: string): AdminProgressStep[] {
  return [
    {
      id: 'copy',
      label: 'Lecture du contenu FR',
      status: 'running',
    },
    {
      id: 'translate',
      label: 'Traduction des champs autorisés',
      detail: `Cible ${localeLabel}`,
      status: 'pending',
    },
    {
      id: 'verify',
      label: 'Vérification linguistique',
      status: 'pending',
    },
    {
      id: 'persist',
      label: 'Enregistrement du brouillon',
      status: 'pending',
    },
  ]
}
