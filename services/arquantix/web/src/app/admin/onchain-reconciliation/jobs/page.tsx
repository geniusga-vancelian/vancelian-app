'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError } from '@/lib/admin/toast'
import { ONCHAIN_RECONCILIATION_BFF_BASE } from '@/lib/admin/onchainReconciliationApi'

type JobRun = {
  id: string
  job_name: string
  status: string
  started_at?: string | null
  finished_at?: string | null
  duration_seconds?: number | null
  summary_json?: Record<string, unknown> | null
  error_json?: Record<string, unknown> | null
}

function statusBadge(status: string): string {
  switch (status) {
    case 'success':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'degraded':
      return 'bg-amber-100 text-amber-900 border-amber-200'
    case 'timeout_degraded':
      return 'bg-orange-100 text-orange-900 border-orange-200'
    case 'error':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'skipped_locked':
      return 'bg-slate-100 text-slate-700 border-slate-300'
    case 'running':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'skipped_locked':
      return 'skipped (lock)'
    case 'timeout_degraded':
      return 'timeout'
    default:
      return status
  }
}

function extractIndexerEvents(summary: Record<string, unknown> | null | undefined): string {
  const indexer = summary?.indexer as Record<string, unknown> | undefined
  if (!indexer) return '—'
  const erc20 = indexer.erc20 as Record<string, unknown> | undefined
  const inserted = erc20?.inserted ?? indexer.events_inserted
  if (inserted != null) return String(inserted)
  if (indexer.skipped) return 'skipped'
  if (indexer.error) return 'error'
  return '—'
}

function extractDiscrepanciesCreated(summary: Record<string, unknown> | null | undefined): string {
  const stale = summary?.stale_reconcile as Record<string, unknown> | undefined
  const users = summary?.users as Record<string, unknown> | undefined
  const staleW = stale?.discrepancies_written ?? 0
  const userW = users?.total_discrepancies_written ?? 0
  const total = Number(staleW) + Number(userW)
  return total > 0 ? String(total) : '0'
}

function extractRpcErrors(summary: Record<string, unknown> | null | undefined): string {
  const indexer = summary?.indexer as Record<string, unknown> | undefined
  const errors = indexer?.errors
  if (Array.isArray(errors) && errors.length > 0) return String(errors.length)
  if (indexer?.error) return '1'
  return '0'
}

export default function DefiObservabilityJobsPage() {
  const [items, setItems] = useState<JobRun[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<JobRun | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(
        `${ONCHAIN_RECONCILIATION_BFF_BASE}/jobs?limit=30`,
        { cache: 'no-store' },
      )
      if (!res.ok) throw new Error(await res.text())
      const data = (await res.json()) as { items: JobRun[]; total: number }
      setItems(data.items)
      setTotal(data.total)
      if (data.items.length > 0 && !selected) setSelected(data.items[0])
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erreur chargement jobs')
    } finally {
      setLoading(false)
    }
  }, [selected])

  useEffect(() => {
    load()
  }, [load])

  const alerts = (selected?.summary_json?.alerts as Array<Record<string, unknown>>) || []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link href="/admin/onchain-reconciliation">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Réconciliation
          </Button>
        </Link>
        <h1 className="text-2xl font-semibold">Jobs observabilité DeFi</h1>
        <Link href="/admin/onchain-reconciliation/health">
          <Button variant="outline" size="sm">
            Santé intents
          </Button>
        </Link>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualiser
        </Button>
      </div>

      <p className="text-sm text-muted-foreground">
        Historique des ticks <code className="text-xs">defi_observability_tick</code> — cron
        externe uniquement.
      </p>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Démarré</TableHead>
            <TableHead>Statut</TableHead>
            <TableHead>Durée</TableHead>
            <TableHead>Events indexés</TableHead>
            <TableHead>Disc. créées</TableHead>
            <TableHead>Err. RPC</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((row) => (
            <TableRow
              key={row.id}
              className={selected?.id === row.id ? 'bg-muted/50 cursor-pointer' : 'cursor-pointer'}
              onClick={() => setSelected(row)}
            >
              <TableCell className="text-xs">
                {row.started_at
                  ? new Date(row.started_at).toLocaleString('fr-FR')
                  : '—'}
              </TableCell>
              <TableCell>
                <Badge variant="outline" className={statusBadge(row.status)}>
                  {statusLabel(row.status)}
                </Badge>
              </TableCell>
              <TableCell>{row.duration_seconds != null ? `${row.duration_seconds}s` : '—'}</TableCell>
              <TableCell>{extractIndexerEvents(row.summary_json)}</TableCell>
              <TableCell>{extractDiscrepanciesCreated(row.summary_json)}</TableCell>
              <TableCell>{extractRpcErrors(row.summary_json)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {selected && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Détail run {selected.id.slice(0, 8)}…</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{selected.job_name}</Badge>
              <Badge variant="outline" className={statusBadge(selected.status)}>
                {statusLabel(selected.status)}
              </Badge>
              {Boolean((selected.summary_json as Record<string, unknown>)?.dry_run) && (
                <Badge variant="secondary">dry-run</Badge>
              )}
            </div>
            {alerts.length > 0 && (
              <div>
                <p className="text-muted-foreground text-xs mb-2">Alertes ops</p>
                <ul className="space-y-1">
                  {alerts.map((a, i) => (
                    <li key={i} className="text-xs">
                      <Badge variant="outline" className="mr-2">
                        {String(a.level)}
                      </Badge>
                      {String(a.message)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-96">
              {JSON.stringify(selected.summary_json, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <p className="text-sm text-muted-foreground">{total} run(s) enregistré(s)</p>
    </div>
  )
}
