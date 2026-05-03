'use client'

import { useCallback, useMemo, useState } from 'react'

import {
  I18nFindingsTable,
  linguisticAuditFindingsToRows,
} from '@/components/admin/I18nFindingsTable'
import { supportedLocales, type Locale } from '@/config/locales'
import type { LinguisticAuditReport, PrepareFixesReport } from '@/lib/i18n/integrity/types'
import { toastError } from '@/lib/admin/toast'

export default function AdminI18nIntegrityPage() {
  const [locale, setLocale] = useState<Locale>('en')
  const [loading, setLoading] = useState(false)
  const [loadingPrepare, setLoadingPrepare] = useState(false)
  const [report, setReport] = useState<LinguisticAuditReport | null>(null)
  const [prepareReport, setPrepareReport] = useState<PrepareFixesReport | null>(null)

  const runScan = useCallback(async () => {
    setLoading(true)
    setReport(null)
    setPrepareReport(null)
    try {
      const res = await fetch(
        `/api/admin/i18n/integrity/scan?targetLocale=${encodeURIComponent(locale)}`,
        { credentials: 'include' },
      )
      if (res.status === 401) {
        window.location.href = '/admin/login'
        return
      }
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(typeof j.error === 'string' ? j.error : `Erreur ${res.status}`)
      }
      const data = (await res.json()) as LinguisticAuditReport
      setReport(data)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Scan impossible')
    } finally {
      setLoading(false)
    }
  }, [locale])

  const integrityRows = useMemo(
    () => (report ? linguisticAuditFindingsToRows(report.findings, report.targetLocale) : []),
    [report],
  )

  const integrityAggregate = useMemo(
    () =>
      report
        ? {
            total: report.summary.totalFindings,
            byStatus: report.summary.byStatus,
          }
        : undefined,
    [report],
  )

  const runPrepare = useCallback(async () => {
    setLoadingPrepare(true)
    setPrepareReport(null)
    try {
      const res = await fetch(
        `/api/admin/i18n/integrity/prepare?targetLocale=${encodeURIComponent(locale)}`,
        { credentials: 'include' },
      )
      if (res.status === 401) {
        window.location.href = '/admin/login'
        return
      }
      if (!res.ok) {
        const j = await res.json().catch(() => ({}))
        throw new Error(typeof j.error === 'string' ? j.error : `Erreur ${res.status}`)
      }
      const data = (await res.json()) as PrepareFixesReport
      setPrepareReport(data)
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Préparation impossible')
    } finally {
      setLoadingPrepare(false)
    }
  }, [locale])

  return (
    <div className="max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Intégrité linguistique (Lots 1 &amp; 2)</h1>
        <p className="text-sm text-gray-600 mt-1">
          <strong>Lot 1</strong> : audit lecture seule sur brouillons (<span className="font-mono">DRAFT</span>).{' '}
          <strong>Lot 2</strong> : propositions de correction (preview, provider mock) —{' '}
          <span className="text-amber-800 font-medium">aucune écriture en base</span>. Docs :{' '}
          <code className="rounded bg-gray-100 px-1 text-xs">docs/arquantix/I18N_INTEGRITY_LOT1.md</code>,{' '}
          <code className="rounded bg-gray-100 px-1 text-xs">docs/arquantix/I18N_INTEGRITY_LOT2.md</code>.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Locale cible</label>
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {supportedLocales.map((l) => (
              <option key={l} value={l}>
                {l.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={runScan}
          disabled={loading || loadingPrepare}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Analyse…' : 'Lancer le scan (Lot 1)'}
        </button>
        <button
          type="button"
          onClick={runPrepare}
          disabled={loading || loadingPrepare}
          className="rounded-md border border-indigo-600 bg-white px-4 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50 disabled:opacity-50"
        >
          {loadingPrepare ? 'Préparation…' : 'Générer les propositions (Lot 2)'}
        </button>
      </div>

      {report && (
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm">
            <p className="font-medium text-gray-900">Périmètre Lot 1</p>
            <ul className="mt-2 text-gray-700 space-y-1 list-disc list-inside text-xs">
              <li>Vaults parcourus : {report.summary.vaultPagesScanned}</li>
              <li>Sections CMS (hero / hero_secondary / cta) avec brouillon : {report.summary.cmsSectionsScanned}</li>
            </ul>
            <p className="text-xs text-gray-500 mt-2">{report.meta.scopeDescription}</p>
          </div>

          <I18nFindingsTable
            layout="multi-page"
            title={`Constats (locale ${report.targetLocale.toUpperCase()})`}
            rows={integrityRows}
            aggregate={integrityAggregate}
          />

          <details className="rounded-lg border border-gray-200 bg-white p-3">
            <summary className="cursor-pointer text-sm font-medium text-gray-800">
              JSON audit brut (debug)
            </summary>
            <pre className="mt-2 max-h-64 overflow-auto text-[10px] text-gray-700">
              {JSON.stringify(report, null, 2)}
            </pre>
          </details>
        </div>
      )}

      {prepareReport && (
        <div className="space-y-4 border-t border-gray-200 pt-6">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
            <p className="font-medium text-amber-950">Plan de correction (Lot 2 — preview)</p>
            <p className="text-amber-900/90 mt-1 text-xs">{prepareReport.meta.scopeDescription}</p>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {(['copy-as-is', 'translate-from-source', 'needs-review', 'skip'] as const).map((s) => (
                <span
                  key={s}
                  className="inline-flex rounded-full bg-white/80 px-2 py-0.5 font-mono text-amber-950 ring-1 ring-amber-200"
                >
                  {s}: {prepareReport.summary[s] ?? 0}
                </span>
              ))}
            </div>
          </div>

          <div>
            <p className="text-sm font-medium text-gray-900 mb-2">
              Propositions ({prepareReport.proposals.length})
            </p>
            <div className="max-h-[560px] overflow-auto rounded-lg border border-gray-200 bg-white">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-gray-100">
                  <tr className="border-b border-gray-200 text-gray-700">
                    <th className="py-2 px-2">Stratégie</th>
                    <th className="py-2 px-2">Page / champ</th>
                    <th className="py-2 px-2">Avant</th>
                    <th className="py-2 px-2">Après (proposé)</th>
                    <th className="py-2 px-2">Source</th>
                    <th className="py-2 px-2">Conf.</th>
                  </tr>
                </thead>
                <tbody>
                  {prepareReport.proposals.map((p) => (
                    <tr key={p.id} className="border-b border-gray-100 align-top">
                      <td className="py-2 px-2 font-mono text-[10px] whitespace-nowrap">{p.strategy}</td>
                      <td className="py-2 px-2">
                        <div className="font-mono text-[10px] text-gray-800">{p.pageSlug}</div>
                        <div className="font-mono text-[10px] text-gray-500">{p.fieldPath}</div>
                        <div className="text-[10px] text-gray-400 mt-0.5">audit: {p.auditStatus}</div>
                      </td>
                      <td className="py-2 px-2 text-gray-700 max-w-[180px] break-words">
                        {p.currentText || '—'}
                      </td>
                      <td className="py-2 px-2 text-indigo-900 max-w-[220px] break-words">
                        {p.proposedText ?? '—'}
                      </td>
                      <td className="py-2 px-2 text-gray-600 max-w-[140px]">
                        {p.sourceLocale ? (
                          <span className="font-mono">{p.sourceLocale}</span>
                        ) : (
                          '—'
                        )}
                        {p.sourceTextExcerpt ? (
                          <div className="text-[10px] text-gray-500 mt-0.5">{p.sourceTextExcerpt}</div>
                        ) : null}
                      </td>
                      <td className="py-2 px-2 whitespace-nowrap">{p.confidence.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs space-y-3">
            <p className="font-medium text-gray-800">Détail par proposition</p>
            {prepareReport.proposals.map((p) => (
              <div key={`${p.id}-detail`} className="border-l-2 border-indigo-300 pl-3">
                <p className="font-mono text-[10px] text-gray-600">{p.pageSlug} · {p.fieldPath}</p>
                <p className="text-gray-800 mt-1">{p.rationale}</p>
                <p className="text-indigo-800 mt-1">
                  <span className="font-medium">Action recommandée :</span> {p.recommendedAction}
                </p>
              </div>
            ))}
          </div>

          <details className="rounded-lg border border-gray-200 bg-white p-3">
            <summary className="cursor-pointer text-sm font-medium text-gray-800">JSON plan Lot 2</summary>
            <pre className="mt-2 max-h-64 overflow-auto text-[10px] text-gray-700">
              {JSON.stringify(prepareReport, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  )
}
