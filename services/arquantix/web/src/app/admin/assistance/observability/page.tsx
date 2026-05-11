'use client'

/**
 * Admin — Observabilité assistance (PR 4C).
 *
 * Agrégats opérationnels (PR 4B) : KPI, gaps policy, usage outils.
 * Export JSONL : CLI PR 4A (drill-down), commande suggérée alignée sur la période.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  ClipboardCopy,
  LineChart,
  Loader2,
  RefreshCw,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { AssistanceAdminHubNav } from '@/components/admin/AssistanceAdminHubNav'

// ─── Types ──────────────────────────────────────────────────────────────────

type CountBucket = {
  label: string
  count: number
  pct: number
}

type ObservabilitySummaryResponse = {
  period_start: string
  period_end: string
  period_days: number
  total_turns: number
  turns_with_data_need: number
  data_need_gap_count: number
  data_need_gap_rate: number
}

type DataNeedGapsResponse = {
  period_start: string
  period_end: string
  period_days: number
  data_need_gap_count: number
  gap_by_agent: CountBucket[]
  gap_by_data_need: CountBucket[]
  gap_by_day: CountBucket[]
  top_missing_tools: CountBucket[]
}

type ToolUsageResponse = {
  period_start: string
  period_end: string
  period_days: number
  total_tool_calls: number
  tools: CountBucket[]
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatNumber(n: number): string {
  return new Intl.NumberFormat('fr-FR').format(n)
}

function formatRange(start: string, end: string): string {
  try {
    const s = new Date(start)
    const e = new Date(end)
    const fmt = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
    return `${fmt.format(s)} → ${fmt.format(e)}`
  } catch {
    return `${start} → ${end}`
  }
}

function buildExportCommand(periodStartIso: string): string {
  const since = periodStartIso.slice(0, 10)
  return [
    'cd services/arquantix/api && \\',
    'python scripts/export_assistance_golden_traces.py \\',
    `  --since ${since} \\`,
    '  --limit-conversations 50 \\',
    '  -o assistance-traces.jsonl',
  ].join('\n')
}

// ─── KPI card ────────────────────────────────────────────────────────────────

function KpiCard({
  title,
  value,
  hint,
}: {
  title: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {hint ? (
        <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}

// ─── Page ───────────────────────────────────────────────────────────────────

const PERIOD_OPTIONS: { value: string; label: string }[] = [
  { value: '7', label: '7 derniers jours' },
  { value: '14', label: '14 derniers jours' },
  { value: '30', label: '30 derniers jours' },
  { value: '90', label: '90 derniers jours' },
]

export default function AssistanceObservabilityPage() {
  const [periodDays, setPeriodDays] = useState<string>('7')
  const [summary, setSummary] = useState<ObservabilitySummaryResponse | null>(
    null,
  )
  const [gaps, setGaps] = useState<DataNeedGapsResponse | null>(null)
  const [usage, setUsage] = useState<ToolUsageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadAll = useCallback(async (days: string) => {
    setLoading(true)
    setError(null)
    const q = `period_days=${encodeURIComponent(days)}`
    try {
      const [r1, r2, r3] = await Promise.all([
        fetch(`/api/admin/assistance/observability/summary?${q}`, {
          cache: 'no-store',
        }),
        fetch(`/api/admin/assistance/observability/data-need-gaps?${q}`, {
          cache: 'no-store',
        }),
        fetch(`/api/admin/assistance/observability/tool-usage?${q}`, {
          cache: 'no-store',
        }),
      ])
      if (!r1.ok) {
        const t = await r1.text().catch(() => '')
        throw new Error(t || `summary HTTP ${r1.status}`)
      }
      if (!r2.ok) {
        const t = await r2.text().catch(() => '')
        throw new Error(t || `gaps HTTP ${r2.status}`)
      }
      if (!r3.ok) {
        const t = await r3.text().catch(() => '')
        throw new Error(t || `usage HTTP ${r3.status}`)
      }
      setSummary((await r1.json()) as ObservabilitySummaryResponse)
      setGaps((await r2.json()) as DataNeedGapsResponse)
      setUsage((await r3.json()) as ToolUsageResponse)
    } catch (e) {
      const msg =
        e instanceof Error ? e.message : 'Erreur chargement observabilité'
      setError(msg)
      toastError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadAll(periodDays)
  }, [loadAll, periodDays])

  const exportCmd = useMemo(
    () =>
      summary ? buildExportCommand(summary.period_start) : '',
    [summary],
  )

  const copyExport = useCallback(async () => {
    if (!exportCmd) return
    try {
      await navigator.clipboard.writeText(exportCmd)
      toastSuccess('Commande copiée dans le presse-papiers')
    } catch {
      toastError('Copie impossible (navigateur)')
    }
  }, [exportCmd])

  return (
    <div className="space-y-6 p-6">
      <AssistanceAdminHubNav />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
            <LineChart className="h-7 w-7 text-indigo-600" aria-hidden />
            Observabilité assistance
          </h1>
          <p className="text-sm text-muted-foreground">
            Métriques agrégées sur{' '}
            <code className="rounded bg-muted px-1">assistance_agent_decisions</code>{' '}
            (PR 4B). Funnel cognitif :{' '}
            <Link
              href="/admin/assistance/cognitive-funnel"
              className="text-indigo-600 hover:underline"
            >
              voir le funnel
            </Link>
            .
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={periodDays} onValueChange={setPeriodDays}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Période" />
            </SelectTrigger>
            <SelectContent>
              {PERIOD_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => void loadAll(periodDays)}
            disabled={loading}
            aria-label="Rafraîchir"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Fenêtre</CardTitle>
          <CardDescription>
            {summary
              ? formatRange(summary.period_start, summary.period_end)
              : '—'}
          </CardDescription>
        </CardHeader>
      </Card>

      {error && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-start gap-2 py-4 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">Échec du chargement</p>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {loading && !summary && (
        <Card>
          <CardContent className="flex items-center gap-2 py-8 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Chargement des métriques…
          </CardContent>
        </Card>
      )}

      {summary && (
        <>
          <section>
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
              Indicateurs clés
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                title="Total turns (router)"
                value={formatNumber(summary.total_turns)}
                hint="Décisions router_classify sur la période."
              />
              <KpiCard
                title="Turns avec data need"
                value={formatNumber(summary.turns_with_data_need)}
                hint="orchestration.data_need ∈ compte / transactions / KYC."
              />
              <KpiCard
                title="Taux de gap (data need)"
                value={`${summary.data_need_gap_rate.toFixed(1)} %`}
                hint="Gaps policy / tours avec data need (0 si aucun tour)."
              />
              <KpiCard
                title="Appels d’outils"
                value={
                  usage
                    ? formatNumber(usage.total_tool_calls)
                    : '—'
                }
                hint="Hors router_classify et policy_data_need_reads."
              />
            </div>
          </section>

          {gaps && (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Gaps par agent
                  </CardTitle>
                  <CardDescription>
                    Lignes <code>policy_data_need_reads</code> —{' '}
                    {formatNumber(gaps.data_need_gap_count)} sur la période.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {gaps.gap_by_agent.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Aucun gap sur cette fenêtre.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Agent</TableHead>
                          <TableHead className="text-right">Nombre</TableHead>
                          <TableHead className="w-[120px] text-right">
                            Part
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {gaps.gap_by_agent.map((row) => (
                          <TableRow key={row.label}>
                            <TableCell className="font-medium">
                              {row.label}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatNumber(row.count)}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center justify-end gap-2">
                                <span className="text-xs text-muted-foreground">
                                  {row.pct.toFixed(1)}%
                                </span>
                                <Progress
                                  value={row.pct}
                                  className="h-1.5 w-16"
                                />
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Gaps par data need
                  </CardTitle>
                  <CardDescription>
                    Valeur <code>data_need</code> sur l’événement gap.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {gaps.gap_by_data_need.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Aucun gap sur cette fenêtre.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Data need</TableHead>
                          <TableHead className="text-right">Nombre</TableHead>
                          <TableHead className="w-[120px] text-right">
                            Part
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {gaps.gap_by_data_need.map((row) => (
                          <TableRow key={row.label}>
                            <TableCell className="font-medium">
                              {row.label}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {formatNumber(row.count)}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center justify-end gap-2">
                                <span className="text-xs text-muted-foreground">
                                  {row.pct.toFixed(1)}%
                                </span>
                                <Progress
                                  value={row.pct}
                                  className="h-1.5 w-16"
                                />
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {gaps && gaps.top_missing_tools.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top outils (allowlist)</CardTitle>
                <CardDescription>
                  Fréquences des entrées{' '}
                  <code>expected_read_tools</code> sur les gaps — indicateur
                  des lectures attendues quand un gap est enregistré.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {gaps.top_missing_tools.map((t) => (
                    <li
                      key={t.label}
                      className="flex items-center justify-between gap-4 text-sm"
                    >
                      <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                        {t.label}
                      </code>
                      <span className="tabular-nums text-muted-foreground">
                        {formatNumber(t.count)} · {t.pct.toFixed(1)}%
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {gaps && gaps.gap_by_day.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Gaps par jour (UTC)</CardTitle>
                <CardDescription>
                  Répartition quotidienne des événements gap.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Jour</TableHead>
                      <TableHead className="text-right">Nombre</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {gaps.gap_by_day.map((row) => (
                      <TableRow key={row.label}>
                        <TableCell>{row.label}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatNumber(row.count)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {usage && usage.tools.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Usage outils (aperçu)
                </CardTitle>
                <CardDescription>
                  Les 15 premiers outils par volume ; total{' '}
                  {formatNumber(usage.total_tool_calls)} appels.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Outil</TableHead>
                      <TableHead className="text-right">Appels</TableHead>
                      <TableHead className="text-right">%</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usage.tools.slice(0, 15).map((t) => (
                      <TableRow key={t.label}>
                        <TableCell>
                          <code className="text-xs">{t.label}</code>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatNumber(t.count)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {t.pct.toFixed(1)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Export JSONL (drill-down)
              </CardTitle>
              <CardDescription>
                Pas d’endpoint HTTP en PR 4A — utiliser le script côté API.
                La commande ci-dessous reprend la date de début de la fenêtre
                affichée (approximation <code>--since</code>).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <pre className="max-h-48 overflow-x-auto rounded-md border bg-muted/40 p-3 text-xs leading-relaxed">
                {exportCmd}
              </pre>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" onClick={copyExport}>
                  <ClipboardCopy className="mr-2 h-4 w-4" />
                  Copier la commande
                </Button>
                <Button type="button" variant="outline" asChild>
                  <Link href="/admin/assistance">
                    Architecture agents
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
