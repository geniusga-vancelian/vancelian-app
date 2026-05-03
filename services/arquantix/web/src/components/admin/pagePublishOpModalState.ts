/**
 * Helpers d'état pour la modale de progression du Page Editor « Publier la
 * page (locale) ».
 *
 * Aligné sur `pageLanguageOpModalState.ts` (même UX, mêmes étapes lisibles)
 * mais pour l'opération de publication (DRAFT → PUBLISHED).
 */

import type { AdminProgressStep } from '@/components/admin/AdminOperationProgressModal'

type PagePublishPayload = {
  targetLocale?: string
  totalSections?: number
  publishedSectionsCount?: number
  skippedSectionsCount?: number
  sectionsPublished?: Array<{ id: string; key: string; hadPublishedBefore?: boolean }>
  sectionsSkipped?: Array<{ id: string; key: string; reason?: 'no-draft' | string }>
  warnings?: string[]
}

const MAX_ROWS = 18

function summariseList(
  items: Array<{ key?: string }> | undefined,
): { uniqueCount: number; lines: string[]; hidden: number } {
  const counts = new Map<string, number>()
  for (const it of items ?? []) {
    const k = it?.key ?? '(sans clé)'
    counts.set(k, (counts.get(k) ?? 0) + 1)
  }
  const sortedKeys = [...counts.keys()].sort((a, b) => a.localeCompare(b, 'fr'))
  const shown = sortedKeys.slice(0, MAX_ROWS)
  const hidden = sortedKeys.length - shown.length
  return {
    uniqueCount: sortedKeys.length,
    lines: shown.map((k) => {
      const n = counts.get(k) ?? 1
      return n > 1 ? `${k} (×${n})` : k
    }),
    hidden,
  }
}

export function buildPagePublishSuccessModal(
  payload: PagePublishPayload,
  localeLabel: string,
  pageSlug?: string,
): {
  steps: AdminProgressStep[]
  summaryLines: string[]
  footerHint?: string
} {
  const total = payload.totalSections ?? 0
  const publishedN = payload.publishedSectionsCount ?? 0
  const skippedN = payload.skippedSectionsCount ?? 0
  const newlyPublished = (payload.sectionsPublished ?? []).filter(
    (s) => !s.hadPublishedBefore,
  )

  const publishedSummary = summariseList(payload.sectionsPublished)
  const skippedSummary = summariseList(payload.sectionsSkipped)

  const steps: AdminProgressStep[] = [
    {
      id: 'read',
      label: 'Lecture des sections de la page',
      detail: `${total} section(s) — locale ${localeLabel}`,
      status: 'success',
    },
    {
      id: 'plan',
      label: 'Sélection des brouillons à publier',
      detail:
        publishedN > 0
          ? `${publishedN} section(s) avec brouillon ${localeLabel} prêt à publier`
          : `Aucune section ne possède de brouillon ${localeLabel}`,
      status: publishedN > 0 ? 'success' : 'warning',
    },
  ]

  if (publishedN > 0) {
    steps.push({
      id: 'published',
      label: `Publication ${localeLabel} (DRAFT → PUBLISHED)`,
      detail:
        publishedSummary.lines.join(', ') +
        (publishedSummary.hidden > 0 ? `, +${publishedSummary.hidden} autre(s)` : ''),
      status: 'success',
    })
  }

  if (newlyPublished.length > 0) {
    const firstPublishedSummary = summariseList(newlyPublished)
    steps.push({
      id: 'first-published',
      label: 'Premières mises en ligne',
      detail:
        `${newlyPublished.length} section(s) publiée(s) pour la première fois en ${localeLabel} — ` +
        firstPublishedSummary.lines.join(', ') +
        (firstPublishedSummary.hidden > 0 ? `, +${firstPublishedSummary.hidden} autre(s)` : ''),
      status: 'success',
    })
  }

  if (skippedN > 0) {
    steps.push({
      id: 'skipped',
      label: `Sections ignorées (sans brouillon ${localeLabel})`,
      detail:
        skippedSummary.lines.join(', ') +
        (skippedSummary.hidden > 0 ? `, +${skippedSummary.hidden} autre(s)` : '') +
        ' — leur version publiée reste inchangée',
      status: 'warning',
    })
  }

  for (const w of payload.warnings ?? []) {
    steps.push({
      id: `warn-${steps.length}`,
      label: 'Avertissement',
      detail: w,
      status: 'warning',
    })
  }

  steps.push({
    id: 'done',
    label: 'Publication terminée',
    detail: 'Le site public servira immédiatement la nouvelle version publiée.',
    status: 'success',
  })

  const summaryLines: string[] = [
    `Publication terminée pour ${localeLabel}.`,
    `${publishedN} section(s) publiée(s) sur ${total}.`,
  ]
  if (skippedN > 0) {
    summaryLines.push(
      `${skippedN} section(s) ignorée(s) (aucun brouillon ${localeLabel} à publier).`,
    )
  }
  if (newlyPublished.length > 0) {
    summaryLines.push(
      `${newlyPublished.length} section(s) publiée(s) pour la première fois dans cette langue.`,
    )
  }

  return {
    steps,
    summaryLines,
    footerHint: pageSlug
      ? `Page « ${pageSlug} » — locale ${localeLabel} : la version publique reflète maintenant le brouillon.`
      : `Locale ${localeLabel} publiée. Rafraîchissez la page publique pour voir le résultat.`,
  }
}

export function initialPagePublishRunningSteps(localeLabel: string): AdminProgressStep[] {
  return [
    {
      id: 'read',
      label: 'Lecture des sections de la page',
      detail: `Locale ${localeLabel}`,
      status: 'running',
    },
    {
      id: 'plan',
      label: 'Sélection des brouillons à publier',
      status: 'pending',
    },
    {
      id: 'publish',
      label: 'Publication (DRAFT → PUBLISHED)',
      detail: 'Transaction atomique',
      status: 'pending',
    },
    {
      id: 'done',
      label: 'Synthèse',
      status: 'pending',
    },
  ]
}
