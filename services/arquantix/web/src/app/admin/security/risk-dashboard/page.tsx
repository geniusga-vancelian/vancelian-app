'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

type Summary = {
  window_hours: number
  sample_size: number
  avg_risk_score: number | null
  distribution: Record<string, number>
  step_up_rate: number | null
  reauth_rate: number | null
  allow_rate: number | null
  anomaly_detection_rate: number | null
}

export default function RiskDashboardPage() {
  const [hours, setHours] = useState('24')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [factors, setFactors] = useState<any>(null)
  const [segments, setSegments] = useState<any>(null)
  const [experiments, setExperiments] = useState<any>(null)
  const [alerts, setAlerts] = useState<any>(null)
  const [recent, setRecent] = useState<any>(null)
  const [calibration, setCalibration] = useState<any>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setErr(null)
    const q = `window_hours=${hours}`
    try {
      const [s, f, seg, ex, al, rc, cal] = await Promise.all([
        fetch(`/api/admin/security/risk-dashboard/summary?${q}`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/factors?${q}`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/segments?${q}`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/experiments?${q}`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/alerts?${q}`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/recent?limit=30`, { credentials: 'include' }),
        fetch(`/api/admin/security/risk-dashboard/calibration-suggestions`, {
          credentials: 'include',
        }),
      ])
      const parse = async (r: Response) => {
        const t = await r.text()
        try {
          return JSON.parse(t)
        } catch {
          return { error: t }
        }
      }
      if (!s.ok) throw new Error((await parse(s)).detail || s.statusText)
      setSummary(await parse(s))
      setFactors(await parse(f))
      setSegments(await parse(seg))
      setExperiments(await parse(ex))
      setAlerts(await parse(al))
      setRecent(await parse(rc))
      setCalibration(await parse(cal))
    } catch (e: any) {
      setErr(e?.message || 'Erreur chargement')
    } finally {
      setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    load()
  }, [load])

  const distData = summary
    ? Object.entries(summary.distribution || {}).map(([name, value]) => ({ name, value }))
    : []

  const segRows = segments?.by_segment
    ? Object.entries(segments.by_segment).map(([k, v]: [string, any]) => ({
        segment: k,
        ...v,
      }))
    : []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Risk engine — dashboard produit</h1>
          <p className="text-sm text-gray-600 mt-1">
            Métriques en mémoire du processus API (dev / single-instance). Fenêtre glissante.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={hours} onValueChange={setHours}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Fenêtre" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="6">6 h</SelectItem>
              <SelectItem value="24">24 h</SelectItem>
              <SelectItem value="72">72 h</SelectItem>
              <SelectItem value="168">7 j</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={load} disabled={loading} variant="outline">
            {loading ? '…' : 'Rafraîchir'}
          </Button>
        </div>
      </div>

      {err && (
        <div className="rounded-md bg-red-50 text-red-800 px-4 py-2 text-sm border border-red-100">
          {err}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Échantillon</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.sample_size ?? '—'}</div>
            <p className="text-xs text-gray-500 mt-1">évaluations risque</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Score moyen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary?.avg_risk_score ?? '—'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Friction</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            <div>allow: {summary?.allow_rate != null ? `${(summary.allow_rate * 100).toFixed(1)}%` : '—'}</div>
            <div>step_up: {summary?.step_up_rate != null ? `${(summary.step_up_rate * 100).toFixed(1)}%` : '—'}</div>
            <div>reauth: {summary?.reauth_rate != null ? `${(summary.reauth_rate * 100).toFixed(1)}%` : '—'}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500">Signaux</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            <div>
              anomalies comportement:{' '}
              {summary?.anomaly_detection_rate != null
                ? `${(summary.anomaly_detection_rate * 100).toFixed(1)}%`
                : '—'}
            </div>
            <div>
              feedback fraude:{' '}
              {factors?.fraud_feedback_rate != null
                ? `${(factors.fraud_feedback_rate * 100).toFixed(1)}%`
                : '—'}
            </div>
            <div>
              faux positifs:{' '}
              {factors?.false_positive_rate != null
                ? `${(factors.false_positive_rate * 100).toFixed(1)}%`
                : '—'}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Répartition risk_level</CardTitle>
          </CardHeader>
          <CardContent className="h-72">
            {distData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-gray-500">Pas encore de données.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alertes</CardTitle>
          </CardHeader>
          <CardContent>
            {alerts?.alerts?.length ? (
              <ul className="space-y-2 text-sm">
                {alerts.alerts.map((a: any) => (
                  <li
                    key={a.id}
                    className={
                      a.severity === 'critical'
                        ? 'text-red-700 bg-red-50 p-2 rounded'
                        : 'text-amber-800 bg-amber-50 p-2 rounded'
                    }
                  >
                    {a.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">Aucune alerte sur la fenêtre.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Segments (Phase 5E)</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-4">Segment</th>
                <th className="py-2 pr-4">n</th>
                <th className="py-2 pr-4">avg score</th>
                <th className="py-2 pr-4">allow</th>
                <th className="py-2 pr-4">step_up</th>
                <th className="py-2 pr-4">reauth</th>
              </tr>
            </thead>
            <tbody>
              {segRows.map((row: any) => (
                <tr key={row.segment} className="border-b border-gray-100">
                  <td className="py-2 font-mono text-xs">{row.segment}</td>
                  <td>{row.sample_size}</td>
                  <td>{row.avg_risk_score ?? '—'}</td>
                  <td>{row.allow_rate != null ? `${(row.allow_rate * 100).toFixed(1)}%` : '—'}</td>
                  <td>{row.step_up_rate != null ? `${(row.step_up_rate * 100).toFixed(1)}%` : '—'}</td>
                  <td>{row.reauth_rate != null ? `${(row.reauth_rate * 100).toFixed(1)}%` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!segRows.length && <p className="text-sm text-gray-500 py-4">Pas de données segmentées.</p>}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Facteurs (fréquence)</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="text-sm space-y-1 max-h-64 overflow-y-auto">
              {(factors?.top_factors_by_frequency || []).slice(0, 15).map((x: any) => (
                <li key={x.factor_code} className="flex justify-between gap-4">
                  <span className="font-mono text-xs truncate">{x.factor_code}</span>
                  <span>{x.count}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Expériences A/B</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 pr-2">exp</th>
                  <th className="py-2 pr-2">variant</th>
                  <th className="py-2 pr-2">n</th>
                  <th className="py-2 pr-2">allow</th>
                  <th className="py-2 pr-2">reauth</th>
                  <th className="py-2 pr-2">avg</th>
                </tr>
              </thead>
              <tbody>
                {(experiments?.variants || []).map((row: any, i: number) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-1 font-mono text-xs">{row.experiment_id}</td>
                    <td>{row.variant}</td>
                    <td>{row.sample_size}</td>
                    <td>{row.allow_rate != null ? `${(row.allow_rate * 100).toFixed(0)}%` : '—'}</td>
                    <td>{row.reauth_rate != null ? `${(row.reauth_rate * 100).toFixed(0)}%` : '—'}</td>
                    <td>{row.avg_risk_score ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!(experiments?.variants || []).length && (
              <p className="text-sm text-gray-500 py-4">Aucune évaluation avec RISK_EXPERIMENT_ID.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Décisions récentes</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-2">action</th>
                <th className="py-2 pr-2">score</th>
                <th className="py-2 pr-2">level</th>
                <th className="py-2 pr-2">outcome</th>
                <th className="py-2 pr-2">segment</th>
                <th className="py-2 pr-2">variant</th>
              </tr>
            </thead>
            <tbody>
              {(recent?.decisions || []).map((d: any, i: number) => (
                <tr key={i} className="border-b border-gray-50">
                  <td className="py-1 truncate max-w-[120px]">{d.action_key}</td>
                  <td>{d.risk_score}</td>
                  <td>{d.risk_level}</td>
                  <td>{d.recommended_outcome}</td>
                  <td>{d.user_segment}</td>
                  <td>{d.variant}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Suggestions calibration (Phase 5F)</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="text-sm space-y-2">
            {(calibration?.suggestions || []).map((s: any) => (
              <li key={s.factor_code} className="border rounded p-2 bg-gray-50">
                <div className="font-mono text-xs">{s.factor_code}</div>
                <div>
                  {s.current_weight} → {s.suggested_weight} (conf {s.confidence})
                </div>
                <div className="text-gray-600 text-xs mt-1">{s.reason}</div>
              </li>
            ))}
          </ul>
          {!(calibration?.suggestions || []).length && (
            <p className="text-sm text-gray-500">Pas assez de feedbacks ou pas de suggestion.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
