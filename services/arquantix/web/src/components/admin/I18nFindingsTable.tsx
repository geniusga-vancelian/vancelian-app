'use client'

import Link from 'next/link'
import { Fragment, useMemo, useState } from 'react'

import type { LinguisticAuditFinding, LinguisticAuditStatus } from '@/lib/i18n/integrity/types'
import type { Locale } from '@/config/locales'
import { cn } from '@/lib/utils'

const STATUS_ORDER: Record<string, number> = {
  WRONG_LANGUAGE: 0,
  MIXED_LANGUAGE: 1,
  NEEDS_REVIEW: 2,
  MISSING: 3,
  NON_TRANSLATABLE: 4,
  OK: 5,
}

const ALL_STATUSES: LinguisticAuditStatus[] = [
  'OK',
  'MISSING',
  'WRONG_LANGUAGE',
  'MIXED_LANGUAGE',
  'NEEDS_REVIEW',
  'NON_TRANSLATABLE',
]

export type I18nFindingRow = {
  id: string
  pageSlug: string
  domain: string
  fieldPath: string
  status: string
  detectedLocale?: string | null
  confidence: number
  excerpt: string
  suggestedAction?: string
  builderHref?: string
}

export type I18nFindingsAggregate = {
  /** Nombre total d’entrées analysées (rapport global, hors filtres) */
  total: number
  byStatus: Partial<Record<string, number>>
}

type Props = {
  rows: I18nFindingRow[]
  aggregate?: I18nFindingsAggregate
  /** multi-page : colonne Page + groupement ; single-page : vault courant uniquement */
  layout?: 'multi-page' | 'single-page'
  title?: string
  className?: string
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'OK':
      return 'border-emerald-200 bg-emerald-50 text-emerald-900'
    case 'MISSING':
      return 'border-slate-300 bg-slate-100 text-slate-900'
    case 'WRONG_LANGUAGE':
      return 'border-red-300 bg-red-100 text-red-950'
    case 'MIXED_LANGUAGE':
      return 'border-orange-300 bg-orange-100 text-orange-950'
    case 'NEEDS_REVIEW':
      return 'border-amber-300 bg-amber-100 text-amber-950'
    case 'NON_TRANSLATABLE':
      return 'border-slate-300 bg-slate-100 text-slate-800'
    default:
      return 'border-slate-200 bg-slate-50 text-slate-800'
  }
}

function statusShortLabel(status: string): string {
  if (status === 'NEEDS_REVIEW') return 'REVIEW'
  if (status === 'MIXED_LANGUAGE') return 'MIXED'
  if (status === 'NON_TRANSLATABLE') return 'N/A'
  return status
}

export function I18nFindingStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex max-w-full items-center rounded-md border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        statusBadgeClass(status),
      )}
      title={status}
    >
      {statusShortLabel(status)}
    </span>
  )
}

function domainLabel(domain: string): string {
  if (domain === 'vault') return 'Vault'
  if (domain === 'cms_section') return 'CMS'
  return domain
}

export function linguisticAuditFindingsToRows(
  findings: LinguisticAuditFinding[],
  targetLocale: Locale,
): I18nFindingRow[] {
  return findings.map((f) => ({
    id: f.id,
    pageSlug: f.pageSlug,
    domain: f.domain,
    fieldPath: f.fieldPath,
    status: f.status,
    detectedLocale: f.detectedLocale ?? f.detectedIso6393 ?? null,
    confidence: f.confidence,
    excerpt: f.excerpt,
    suggestedAction: f.suggestedAction,
    builderHref:
      f.domain === 'vault'
        ? `/admin/vault-builder?slug=${encodeURIComponent(f.pageSlug)}&editingLocale=${encodeURIComponent(targetLocale)}`
        : undefined,
  }))
}

type VaultEntry = {
  path?: string
  status?: string
  confidence?: number
  valueExcerpt?: string
  detectedLocale?: string
  suggestedAction?: string
  moduleType?: string
}

/** Adapte le rapport scan / apply « check module language » vault. */
export function vaultCheckReportToRows(
  report: unknown,
  pageSlug: string,
  editingLocale: Locale,
  opts?: { exclusiveOfferWorkspace?: boolean },
): I18nFindingRow[] {
  if (report == null || typeof report !== 'object') return []
  const r = report as Record<string, unknown>
  const mode = r.mode
  const result = r.result as { entries?: VaultEntry[] } | undefined
  const scanAfter = r.scanAfter as { entries?: VaultEntry[] } | undefined
  const entries =
    mode === 'afterApply' && Array.isArray(scanAfter?.entries)
      ? scanAfter!.entries!
      : Array.isArray(result?.entries)
        ? result!.entries!
        : Array.isArray(scanAfter?.entries)
          ? scanAfter!.entries!
          : []
  const eo = opts?.exclusiveOfferWorkspace ? '&eo=1' : ''
  const baseBuilder = `/admin/vault-builder?slug=${encodeURIComponent(pageSlug)}&editingLocale=${encodeURIComponent(editingLocale)}${eo}`
  return entries.map((e, i) => ({
    id: `${String(e.path ?? 'row')}-${i}`,
    pageSlug,
    domain: 'vault',
    fieldPath: String(e.path ?? '—'),
    status: String(e.status ?? '—'),
    detectedLocale: e.detectedLocale ?? null,
    confidence: typeof e.confidence === 'number' ? e.confidence : 0,
    excerpt: String(e.valueExcerpt ?? ''),
    suggestedAction: typeof e.suggestedAction === 'string' ? e.suggestedAction : undefined,
    builderHref: baseBuilder,
  }))
}

export function vaultCheckReportAggregate(report: unknown): I18nFindingsAggregate | undefined {
  if (report == null || typeof report !== 'object') return undefined
  const r = report as Record<string, unknown>
  const mode = r.mode
  const result = r.result as { summary?: { totalFields?: number; byStatus?: Record<string, number> } } | undefined
  const scanAfter = r.scanAfter as typeof result
  const summary = mode === 'afterApply' ? scanAfter?.summary : result?.summary
  if (!summary) return undefined
  return {
    total: summary.totalFields ?? 0,
    byStatus: summary.byStatus ?? {},
  }
}

type PageEntry = {
  path?: string
  scope?: string
  status?: string
  confidence?: number
  valueExcerpt?: string
  detectedLocale?: string
  suggestedAction?: string
  sectionId?: string
  sectionKey?: string
}

/**
 * Adapte le rapport scan / apply « check page language » (Page Editor CMS).
 * `builderHref` pointe vers l'éditeur de section concerné, ou la page elle-même
 * pour les entrées `pageI18n`.
 */
export function pageCheckReportToRows(
  report: unknown,
  pageSlug: string,
  editingLocale: Locale,
): I18nFindingRow[] {
  if (report == null || typeof report !== 'object') return []
  const r = report as Record<string, unknown>
  const mode = r.mode
  const result = r.result as { entries?: PageEntry[] } | undefined
  const scanAfter = r.scanAfter as { entries?: PageEntry[] } | undefined
  const entries =
    mode === 'afterApply' && Array.isArray(scanAfter?.entries)
      ? scanAfter!.entries!
      : Array.isArray(result?.entries)
        ? result!.entries!
        : Array.isArray(scanAfter?.entries)
          ? scanAfter!.entries!
          : []
  const pageEditorHref = `/admin/pages/${encodeURIComponent(pageSlug)}?editingLocale=${encodeURIComponent(editingLocale)}`
  return entries.map((e, i) => {
    const isPageI18n = e.scope === 'page_i18n'
    const builderHref =
      isPageI18n
        ? pageEditorHref
        : e.sectionId
          ? `/admin/sections/${encodeURIComponent(e.sectionId)}?locale=${encodeURIComponent(editingLocale)}`
          : pageEditorHref
    return {
      id: `${String(e.path ?? 'row')}-${i}`,
      pageSlug,
      domain: 'cms_section',
      fieldPath: String(e.path ?? '—'),
      status: String(e.status ?? '—'),
      detectedLocale: e.detectedLocale ?? null,
      confidence: typeof e.confidence === 'number' ? e.confidence : 0,
      excerpt: String(e.valueExcerpt ?? ''),
      suggestedAction: typeof e.suggestedAction === 'string' ? e.suggestedAction : undefined,
      builderHref,
    }
  })
}

export function pageCheckReportAggregate(report: unknown): I18nFindingsAggregate | undefined {
  if (report == null || typeof report !== 'object') return undefined
  const r = report as Record<string, unknown>
  const mode = r.mode
  const result = r.result as { summary?: { totalFields?: number; byStatus?: Record<string, number> } } | undefined
  const scanAfter = r.scanAfter as typeof result
  const summary = mode === 'afterApply' ? scanAfter?.summary : result?.summary
  if (!summary) return undefined
  return {
    total: summary.totalFields ?? 0,
    byStatus: summary.byStatus ?? {},
  }
}

export function I18nFindingsTable({
  rows,
  aggregate,
  layout = 'multi-page',
  title = 'Constats',
  className,
}: Props) {
  const [slugQuery, setSlugQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState<'all' | 'vault' | 'cms_section'>('all')
  const [issuesOnly, setIssuesOnly] = useState(false)
  const [minConfidencePct, setMinConfidencePct] = useState(0)
  const [statusOn, setStatusOn] = useState<Record<LinguisticAuditStatus, boolean>>(() => {
    const init = {} as Record<LinguisticAuditStatus, boolean>
    for (const s of ALL_STATUSES) init[s] = true
    return init
  })

  const filteredSorted = useMemo(() => {
    const q = slugQuery.trim().toLowerCase()
    let list = rows.filter((row) => {
      if (issuesOnly && row.status === 'OK') return false
      const st = row.status as LinguisticAuditStatus
      if (ALL_STATUSES.includes(st) && !statusOn[st]) return false
      if (domainFilter !== 'all') {
        const d = row.domain === 'cms_section' ? 'cms_section' : row.domain === 'vault' ? 'vault' : row.domain
        if (d !== domainFilter) return false
      }
      if (q && !row.pageSlug.toLowerCase().includes(q)) return false
      const pct = row.confidence * 100
      if (pct < minConfidencePct) return false
      return true
    })

    list = [...list].sort((a, b) => {
      const sa = STATUS_ORDER[a.status] ?? 99
      const sb = STATUS_ORDER[b.status] ?? 99
      if (sa !== sb) return sa - sb
      const cmpPage = a.pageSlug.localeCompare(b.pageSlug, 'fr')
      if (cmpPage !== 0) return cmpPage
      return a.fieldPath.localeCompare(b.fieldPath, 'fr')
    })
    return list
  }, [rows, slugQuery, domainFilter, issuesOnly, minConfidencePct, statusOn])

  const grouped = useMemo(() => {
    const map = new Map<string, I18nFindingRow[]>()
    for (const row of filteredSorted) {
      const list = map.get(row.pageSlug) ?? []
      list.push(row)
      map.set(row.pageSlug, list)
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], 'fr'))
  }, [filteredSorted])

  const toggleStatus = (s: LinguisticAuditStatus) => {
    setStatusOn((prev) => ({ ...prev, [s]: !prev[s] }))
  }

  const summary = aggregate

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-gray-900">{title}</p>
        <p className="text-xs text-gray-500">
          {rows.length === 0
            ? 'Aucune entrée'
            : `${filteredSorted.length} ligne(s) affichée(s) sur ${rows.length}`}
        </p>
      </div>

      {summary ? (
        <div className="flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-white p-3">
          <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-medium text-slate-800">
            Total : {summary.total}
          </span>
          {ALL_STATUSES.map((s) => (
            <span
              key={s}
              className={cn(
                'inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium',
                statusBadgeClass(s),
              )}
            >
              {statusShortLabel(s)} : {summary.byStatus[s] ?? 0}
            </span>
          ))}
        </div>
      ) : null}

      {rows.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/60 px-3 py-4 text-sm text-slate-600">
          Aucun champ listé dans ce rapport. Lancez une analyse pour remplir le tableau.
        </p>
      ) : (
      <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 space-y-3">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-600">
            Page (slug)
            <input
              type="search"
              value={slugQuery}
              onChange={(e) => setSlugQuery(e.target.value)}
              placeholder="Filtrer…"
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-900 min-w-[160px]"
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-600">
            Domaine
            <select
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value as 'all' | 'vault' | 'cms_section')}
              className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs"
            >
              <option value="all">Tous</option>
              <option value="vault">Vault</option>
              <option value="cms_section">CMS</option>
            </select>
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-600">
            Confiance min. (%)
            <input
              type="number"
              min={0}
              max={100}
              value={minConfidencePct}
              onChange={(e) => setMinConfidencePct(Math.min(100, Math.max(0, Number(e.target.value) || 0)))}
              className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1.5 text-xs"
            />
          </label>
          <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={issuesOnly}
              onChange={(e) => setIssuesOnly(e.target.checked)}
              className="rounded border-slate-300"
            />
            Masquer OK (problèmes seuls)
          </label>
        </div>

        <div className="flex flex-wrap gap-x-3 gap-y-1.5 items-center border-t border-slate-200/80 pt-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Statuts</span>
          {ALL_STATUSES.map((s) => (
            <label key={s} className="inline-flex items-center gap-1 text-[11px] text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={statusOn[s]}
                onChange={() => toggleStatus(s)}
                className="rounded border-slate-300"
              />
              <I18nFindingStatusBadge status={s} />
            </label>
          ))}
        </div>
      </div>
      )}

      <div
        className={cn(
          'max-h-[min(70vh,560px)] overflow-auto rounded-lg border border-slate-200 bg-white shadow-sm',
          rows.length === 0 && 'hidden',
        )}
      >
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-100 shadow-sm">
            <tr className="text-slate-600">
              {layout === 'multi-page' ? (
                <th className="py-2 px-2 font-semibold w-[120px]">Page / Vault</th>
              ) : null}
              <th className="py-2 px-2 font-semibold w-[72px]">Domaine</th>
              <th className="py-2 px-2 font-semibold min-w-[140px]">Champ</th>
              <th className="py-2 px-2 font-semibold w-[100px]">Statut</th>
              <th className="py-2 px-2 font-semibold w-[72px]">Langue</th>
              <th className="py-2 px-2 font-semibold w-[56px]">Conf.</th>
              <th className="py-2 px-2 font-semibold min-w-[160px]">Extrait</th>
              <th className="py-2 px-2 font-semibold w-[120px]">Action</th>
            </tr>
          </thead>
          <tbody>
            {grouped.length === 0 ? (
              <tr>
                <td
                  colSpan={layout === 'multi-page' ? 8 : 7}
                  className="py-8 text-center text-sm text-slate-500"
                >
                  Aucun constat ne correspond aux filtres.
                </td>
              </tr>
            ) : (
              grouped.map(([pageSlug, pageRows]) => (
                <Fragment key={pageSlug}>
                  <tr className="bg-slate-100/90">
                    <td
                      colSpan={layout === 'multi-page' ? 8 : 7}
                      className="py-1.5 px-2 text-[11px] font-semibold text-slate-700 border-y border-slate-200"
                    >
                      {layout === 'multi-page' ? (
                        <>Page · {pageSlug}</>
                      ) : (
                        <>Vault · {pageSlug}</>
                      )}
                    </td>
                  </tr>
                  {pageRows.map((f) => {
                    const isIssue = f.status !== 'OK'
                    const lang =
                      f.detectedLocale != null && String(f.detectedLocale).trim() !== ''
                        ? String(f.detectedLocale).toUpperCase()
                        : '—'
                    return (
                      <tr
                        key={f.id}
                        className={cn(
                          'border-b border-slate-100 align-top',
                          isIssue ? 'bg-amber-50/40' : 'bg-white',
                        )}
                      >
                        {layout === 'multi-page' ? (
                          <td className="py-1.5 px-2 font-mono text-[10px] text-slate-800 max-w-[120px] truncate" title={f.pageSlug}>
                            {f.pageSlug}
                          </td>
                        ) : null}
                        <td className="py-1.5 px-2 text-slate-700">{domainLabel(f.domain)}</td>
                        <td
                          className="py-1.5 px-2 font-mono text-[10px] text-slate-800 max-w-[220px] truncate"
                          title={f.fieldPath}
                        >
                          {f.fieldPath}
                        </td>
                        <td className="py-1.5 px-2">
                          <I18nFindingStatusBadge status={f.status} />
                        </td>
                        <td className="py-1.5 px-2 text-slate-700 whitespace-nowrap">{lang}</td>
                        <td className="py-1.5 px-2 text-slate-600 tabular-nums" title={`${(f.confidence * 100).toFixed(1)}%`}>
                          {(f.confidence * 100).toFixed(0)}%
                        </td>
                        <td
                          className="py-1.5 px-2 text-slate-700 max-w-[220px] truncate"
                          title={f.excerpt || undefined}
                        >
                          {f.excerpt ? f.excerpt : '—'}
                        </td>
                        <td className="py-1.5 px-2">
                          <div className="flex flex-col gap-1">
                            {f.builderHref ? (
                              <Link
                                href={f.builderHref}
                                className="text-indigo-600 hover:text-indigo-800 font-medium whitespace-nowrap"
                              >
                                Voir builder
                              </Link>
                            ) : null}
                            {f.suggestedAction ? (
                              <span className="text-[10px] text-slate-500 line-clamp-2" title={f.suggestedAction}>
                                {f.suggestedAction}
                              </span>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
