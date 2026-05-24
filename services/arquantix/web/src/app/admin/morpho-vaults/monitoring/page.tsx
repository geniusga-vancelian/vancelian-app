'use client'

import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { cn } from '@/lib/utils'

type MorphoGlobalStatus = 'healthy' | 'warning' | 'critical'

type MorphoAlert = {
  code: string
  level: 'info' | 'warning' | 'critical'
  message: string
  count?: number
}

type MonitoringSnapshot = {
  globalStatus: MorphoGlobalStatus
  alerts: MorphoAlert[]
  dependencyHealth: {
    morphoGraphql: { ok: boolean; latencyMs?: number; error?: string }
    baseRpc: {
      ok: boolean
      latencyMs?: number
      error?: string
      activeProvider?: string
      usedFallback?: boolean
      publicRpcAsPrimary?: boolean
      providers?: Array<{
        label: string
        ok: boolean
        latencyMs?: number
        error?: string
        isPublic?: boolean
      }>
    }
  }
  beta: {
    betaEnabled: boolean
    depositsDisabled: boolean
    withdrawsDisabled: boolean
    allowlistPersonIdsCount: number
    allowlistEmailsCount: number
    allowAllUsers: boolean
    betaActiveUsersCount: number
    totalDepositedUsdc: number
    totalWithdrawnUsdc: number
    totalAssetsInVaultUsdc: number
    totalEarnedYieldUsdc: number
    pendingTxCount: number
    failedTxCount: number
    mismatchesCount: number
    limits: {
      minDepositUsdc: number
      maxDepositUsdc: number
      maxUserExposureUsdc: number
      maxGlobalExposureUsdc: number
    } | null
  }
  activeVaults: Array<{
    vaultAddress: string
    name: string | null
    assetSymbol: string
    integrationMode: string | null
    lastSyncedAt: string | null
    trackedAssetsRaw: string
  }>
  pendingTransactions: Array<{
    id: string
    personId: string
    vaultAddress: string
    operation: string
    integrationMode: string
    createdAt: string
    idempotencyKey: string
  }>
  pendingThresholdMinutes: number
  costBasisUnknownCount: number
  latestReconciliation: {
    runId: string
    startedAt: string
    finishedAt: string | null
    itemsChecked: number
    matchedCount: number
    mismatchCount: number
    missingOnchainCount: number
    missingLedgerCount: number
    mismatches: Array<{
      id: string
      personId: string
      vaultAddress: string
      walletAddress: string
      status: string
      deltaAssetsRaw: string | null
      integrationMode: string
    }>
  } | null
}

function StatusBadge({ status }: { status: MorphoGlobalStatus }) {
  if (status === 'healthy') {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 font-ui text-sm font-semibold text-emerald-800">
        <CheckCircle2 className="h-4 w-4" /> Healthy
      </span>
    )
  }
  if (status === 'warning') {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 font-ui text-sm font-semibold text-amber-900">
        <AlertTriangle className="h-4 w-4" /> Warning
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-red-100 px-3 py-1 font-ui text-sm font-semibold text-red-900">
      <XCircle className="h-4 w-4" /> Critical
    </span>
  )
}

function alertClass(level: MorphoAlert['level']): string {
  if (level === 'critical') return 'border-red-200 bg-red-50 text-red-950'
  if (level === 'warning') return 'border-amber-200 bg-amber-50 text-amber-950'
  return 'border-slate-200 bg-slate-50 text-slate-800'
}

export default function AdminMorphoVaultMonitoringPage() {
  const [snapshot, setSnapshot] = useState<MonitoringSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/morpho-vaults/monitoring', { cache: 'no-store' })
      if (!res.ok) throw new Error('Chargement monitoring impossible.')
      setSnapshot((await res.json()) as MonitoringSnapshot)
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erreur monitoring.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const runAction = useCallback(
    async (action: 'sync_registry' | 'reconcile') => {
      setRunning(action)
      try {
        const res = await fetch('/api/admin/morpho-vaults/monitoring', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action }),
        })
        if (!res.ok) throw new Error('Action impossible.')
        toastSuccess(action === 'sync_registry' ? 'Registry synchronisé.' : 'Réconciliation lancée.')
        await load()
      } catch (error) {
        toastError(error instanceof Error ? error.message : 'Erreur action.')
      } finally {
        setRunning(null)
      }
    },
    [load],
  )

  const recon = snapshot?.latestReconciliation

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="m-0 font-ui text-2xl font-semibold text-slate-900">Monitoring Morpho Vaults</h1>
            {snapshot ? <StatusBadge status={snapshot.globalStatus} /> : null}
          </div>
          <p className="m-0 mt-1 font-ui text-sm text-slate-500">
            Réconciliation ledger ↔ on-chain, dépendances Morpho/RPC, txs pending.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={loading || running !== null} onClick={() => void load()}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Actualiser
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={running !== null}
            onClick={() => void runAction('sync_registry')}
          >
            Sync registry
          </Button>
          <Button type="button" disabled={running !== null} onClick={() => void runAction('reconcile')}>
            {running === 'reconcile' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            Lancer réconciliation
          </Button>
        </div>
      </header>

      {loading && !snapshot ? (
        <p className="font-ui text-sm text-slate-500">Chargement…</p>
      ) : snapshot ? (
        <>
          {snapshot.alerts.length > 0 ? (
            <section className="space-y-2">
              {snapshot.alerts.map((alert) => (
                <div
                  key={alert.code}
                  className={cn('rounded-lg border px-4 py-3 font-ui text-sm', alertClass(alert.level))}
                >
                  <strong className="uppercase tracking-wide">{alert.code}</strong>
                  <p className="m-0 mt-1">{alert.message}</p>
                </div>
              ))}
            </section>
          ) : null}

          <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Statut global</p>
              <p className="m-0 mt-2 font-ui text-lg font-semibold capitalize text-slate-900">{snapshot.globalStatus}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Vaults actifs</p>
              <p className="m-0 mt-2 text-2xl font-semibold text-slate-900">{snapshot.activeVaults.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Tx pending &gt; {snapshot.pendingThresholdMinutes} min</p>
              <p className="m-0 mt-2 text-2xl font-semibold text-slate-900">{snapshot.pendingTransactions.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Morpho GraphQL</p>
              <p className={cn('m-0 mt-2 font-ui text-sm font-semibold', snapshot.dependencyHealth.morphoGraphql.ok ? 'text-emerald-700' : 'text-red-700')}>
                {snapshot.dependencyHealth.morphoGraphql.ok
                  ? `OK (${snapshot.dependencyHealth.morphoGraphql.latencyMs ?? '?'} ms)`
                  : snapshot.dependencyHealth.morphoGraphql.error ?? 'KO'}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">RPC Base</p>
              <p className={cn('m-0 mt-2 font-ui text-sm font-semibold', snapshot.dependencyHealth.baseRpc.ok ? 'text-emerald-700' : 'text-red-700')}>
                {snapshot.dependencyHealth.baseRpc.ok
                  ? `OK (${snapshot.dependencyHealth.baseRpc.latencyMs ?? '?'} ms) · ${snapshot.dependencyHealth.baseRpc.activeProvider ?? '—'}`
                  : snapshot.dependencyHealth.baseRpc.error ?? 'KO'}
              </p>
              {snapshot.dependencyHealth.baseRpc.usedFallback ? (
                <p className="m-0 mt-1 font-ui text-xs text-amber-700">Failover RPC actif</p>
              ) : null}
              {snapshot.dependencyHealth.baseRpc.publicRpcAsPrimary ? (
                <p className="m-0 mt-1 font-ui text-xs text-red-700">RPC public en primary — configurer Alchemy</p>
              ) : null}
            </div>
          </section>

          {snapshot.dependencyHealth.baseRpc.providers && snapshot.dependencyHealth.baseRpc.providers.length > 0 ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="m-0 mb-3 font-ui text-base font-semibold text-slate-900">Providers RPC Base</h2>
              <ul className="m-0 list-none space-y-2 p-0 font-ui text-sm">
                {snapshot.dependencyHealth.baseRpc.providers.map((provider) => (
                  <li
                    key={provider.label}
                    className={cn(
                      'rounded border px-3 py-2',
                      provider.ok ? 'border-emerald-200 bg-emerald-50 text-emerald-950' : 'border-red-200 bg-red-50 text-red-950',
                    )}
                  >
                    <strong>{provider.label}</strong>
                    {provider.isPublic ? ' (public)' : ''} —{' '}
                    {provider.ok ? `OK ${provider.latencyMs ?? '?'} ms` : provider.error ?? 'KO'}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="rounded-lg border border-indigo-200 bg-indigo-50/60 p-4">
            <h2 className="m-0 mb-3 font-ui text-base font-semibold text-indigo-950">Beta Morpho USDC</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Beta activée</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.betaEnabled ? 'Oui' : 'Non'}</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Utilisateurs actifs</p>
                <p className="m-0 mt-1 text-xl font-semibold text-slate-900">{snapshot.beta.betaActiveUsersCount}</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Accès beta</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">
                  {snapshot.beta.allowAllUsers
                    ? 'Tous les utilisateurs'
                    : `Allowlist ${snapshot.beta.allowlistPersonIdsCount} / ${snapshot.beta.allowlistEmailsCount}`}
                </p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Kill switch</p>
                <p className="m-0 mt-1 font-ui text-sm text-slate-900">
                  Dépôts {snapshot.beta.depositsDisabled ? 'OFF' : 'ON'} · Retraits{' '}
                  {snapshot.beta.withdrawsDisabled ? 'OFF' : 'ON'}
                </p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Total déposé</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.totalDepositedUsdc.toFixed(2)} USDC</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Total retiré</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.totalWithdrawnUsdc.toFixed(2)} USDC</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Assets en vault</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.totalAssetsInVaultUsdc.toFixed(2)} USDC</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Yield estimé</p>
                <p className="m-0 mt-1 font-semibold text-emerald-700">{snapshot.beta.totalEarnedYieldUsdc.toFixed(2)} USDC</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Tx failed / reverted</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.failedTxCount}</p>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-white p-3">
                <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Mismatches (dernier run)</p>
                <p className="m-0 mt-1 font-semibold text-slate-900">{snapshot.beta.mismatchesCount}</p>
              </div>
            </div>
          </section>

          {recon ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center gap-2">
                <Activity className="h-4 w-4 text-slate-600" />
                <h2 className="m-0 font-ui text-base font-semibold text-slate-900">Dernière réconciliation</h2>
              </div>
              <p className="m-0 font-ui text-sm text-slate-600">
                Run {recon.runId.slice(0, 8)}… · {recon.itemsChecked} items · matched {recon.matchedCount} · mismatch{' '}
                {recon.mismatchCount} · missing on-chain {recon.missingOnchainCount} · missing ledger{' '}
                {recon.missingLedgerCount}
              </p>
              <p className="m-0 mt-1 font-ui text-xs text-slate-500">
                {recon.startedAt} → {recon.finishedAt ?? '—'}
              </p>
            </section>
          ) : null}

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="m-0 mb-3 font-ui text-base font-semibold text-slate-900">Vaults actifs</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left font-ui text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-slate-500">
                    <th className="py-2 pr-4">Vault</th>
                    <th className="py-2 pr-4">Mode</th>
                    <th className="py-2 pr-4">Assets trackés (raw)</th>
                    <th className="py-2">Dernière sync</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.activeVaults.map((row) => (
                    <tr key={row.vaultAddress} className="border-b border-slate-50">
                      <td className="py-2 pr-4">
                        <div className="font-medium text-slate-900">{row.name ?? row.vaultAddress.slice(0, 10)}…</div>
                        <div className="font-mono text-xs text-slate-500">{row.vaultAddress}</div>
                      </td>
                      <td className="py-2 pr-4">{row.integrationMode ?? '—'}</td>
                      <td className="py-2 pr-4 font-mono text-xs">{row.trackedAssetsRaw}</td>
                      <td className="py-2 text-xs text-slate-500">{row.lastSyncedAt ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {snapshot.pendingTransactions.length > 0 ? (
            <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <div className="mb-3 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-700" />
                <h2 className="m-0 font-ui text-base font-semibold text-amber-950">Transactions pending</h2>
              </div>
              <ul className="m-0 list-none space-y-2 p-0 font-ui text-sm text-amber-950">
                {snapshot.pendingTransactions.map((tx) => (
                  <li key={tx.id} className="rounded border border-amber-200 bg-white/70 px-3 py-2">
                    {tx.operation} · {tx.integrationMode} · person {tx.personId.slice(0, 8)}… · {tx.createdAt}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {recon && recon.mismatches.length > 0 ? (
            <section className="rounded-lg border border-red-200 bg-red-50 p-4">
              <h2 className="m-0 mb-3 font-ui text-base font-semibold text-red-950">Mismatches réconciliation</h2>
              <ul className="m-0 list-none space-y-2 p-0 font-ui text-sm">
                {recon.mismatches.map((row) => (
                  <li key={row.id} className="rounded border border-red-200 bg-white/70 px-3 py-2 text-red-950">
                    [{row.status}] person {row.personId.slice(0, 8)}… · vault {row.vaultAddress.slice(0, 10)}… · delta{' '}
                    {row.deltaAssetsRaw ?? '—'}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
