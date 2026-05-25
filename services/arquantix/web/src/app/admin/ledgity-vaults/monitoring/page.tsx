'use client'

import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { cn } from '@/lib/utils'

type LedgityGlobalStatus = 'healthy' | 'warning' | 'critical'

type LedgityAlert = {
  code: string
  level: 'info' | 'warning' | 'critical'
  message: string
  count?: number
}

type MonitoringSnapshot = {
  globalStatus: LedgityGlobalStatus
  alerts: LedgityAlert[]
  dependencyHealth: {
    baseRpc: {
      ok: boolean
      latencyMs?: number
      error?: string
      activeProvider?: string
      usedFallback?: boolean
      publicRpcAsPrimary?: boolean
    }
  }
  runtimeMode: {
    vaultsEnabled: boolean
    betaEnabled: boolean
    depositsDisabled: boolean
    withdrawsDisabled: boolean
    sandboxEnabled: boolean
    mode: 'sandbox' | 'live' | 'read_only'
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
    label: string | null
    assetSymbol: string
    shareSymbol: string
    integrationMode: string
    netApy: number | null
    pricePerShare: number | null
    tvlUsd: number | null
    liquidityBufferRaw: string | null
    liquidityLow: boolean
    withdrawAvailability: string
    paused: boolean | null
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
  failedTransactions: Array<{
    id: string
    personId: string
    vaultAddress: string
    operation: string
    status: string
    errorMessage: string | null
    createdAt: string
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
    ppsUnavailableCount: number
    liquidityWarningCount: number
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

function StatusBadge({ status }: { status: LedgityGlobalStatus }) {
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

function alertClass(level: LedgityAlert['level']): string {
  if (level === 'critical') return 'border-red-200 bg-red-50 text-red-950'
  if (level === 'warning') return 'border-amber-200 bg-amber-50 text-amber-950'
  return 'border-slate-200 bg-slate-50 text-slate-800'
}

export default function AdminLedgityVaultMonitoringPage() {
  const [snapshot, setSnapshot] = useState<MonitoringSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/ledgity-vaults/monitoring', { cache: 'no-store' })
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

  const runReconcile = useCallback(async () => {
    setRunning('reconcile')
    try {
      const res = await fetch('/api/admin/ledgity-vaults/monitoring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reconcile' }),
      })
      if (!res.ok) throw new Error('Réconciliation impossible.')
      toastSuccess('Réconciliation Ledgity lancée.')
      await load()
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erreur réconciliation.')
    } finally {
      setRunning(null)
    }
  }, [load])

  const recon = snapshot?.latestReconciliation

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="m-0 font-ui text-2xl font-semibold text-slate-900">Monitoring Ledgity Vaults</h1>
            {snapshot ? <StatusBadge status={snapshot.globalStatus} /> : null}
          </div>
          <p className="m-0 mt-1 font-ui text-sm text-slate-500">
            Liquidité RWA, réconciliation ledger ↔ lyToken, PPS et retraits différés.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={loading || running !== null} onClick={() => void load()}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Actualiser
          </Button>
          <Button type="button" disabled={running !== null} onClick={() => void runReconcile()}>
            {running === 'reconcile' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
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
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Mode runtime</p>
              <p className="m-0 mt-2 font-ui text-lg font-semibold capitalize text-slate-900">{snapshot.runtimeMode.mode}</p>
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
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">Tx failed</p>
              <p className="m-0 mt-2 text-2xl font-semibold text-slate-900">{snapshot.failedTransactions.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="m-0 text-xs uppercase tracking-wide text-slate-500">RPC Base</p>
              <p className={cn('m-0 mt-2 font-ui text-sm font-semibold', snapshot.dependencyHealth.baseRpc.ok ? 'text-emerald-700' : 'text-red-700')}>
                {snapshot.dependencyHealth.baseRpc.ok
                  ? `OK (${snapshot.dependencyHealth.baseRpc.latencyMs ?? '?'} ms)`
                  : snapshot.dependencyHealth.baseRpc.error ?? 'KO'}
              </p>
              {snapshot.dependencyHealth.baseRpc.activeProvider ? (
                <p className="m-0 mt-1 text-xs text-slate-500">{snapshot.dependencyHealth.baseRpc.activeProvider}</p>
              ) : null}
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="m-0 font-ui text-lg font-semibold text-slate-900">Flags production</h2>
            <dl className="mt-3 grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-slate-500">LEDGITY_VAULTS_ENABLED</dt>
                <dd className="font-semibold">{snapshot.runtimeMode.vaultsEnabled ? 'true' : 'false'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">LEDGITY_DEPOSITS_DISABLED</dt>
                <dd className="font-semibold">{snapshot.runtimeMode.depositsDisabled ? 'true' : 'false'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">LEDGITY_WITHDRAWS_DISABLED</dt>
                <dd className="font-semibold">{snapshot.runtimeMode.withdrawsDisabled ? 'true' : 'false'}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Sandbox local</dt>
                <dd className="font-semibold">{snapshot.runtimeMode.sandboxEnabled ? 'actif' : 'inactif'}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <h2 className="m-0 font-ui text-lg font-semibold text-slate-900">Vaults Ledgity</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-2 py-2">Vault</th>
                    <th className="px-2 py-2">Asset / Share</th>
                    <th className="px-2 py-2">PPS</th>
                    <th className="px-2 py-2">TVL</th>
                    <th className="px-2 py-2">Liquidité</th>
                    <th className="px-2 py-2">Retrait</th>
                    <th className="px-2 py-2">Ledger tracked</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.activeVaults.map((vault) => (
                    <tr key={vault.vaultAddress} className="border-b border-slate-100">
                      <td className="px-2 py-2 font-mono text-xs">{vault.vaultAddress}</td>
                      <td className="px-2 py-2">
                        {vault.assetSymbol} / {vault.shareSymbol}
                      </td>
                      <td className="px-2 py-2">{vault.pricePerShare ?? '—'}</td>
                      <td className="px-2 py-2">{vault.tvlUsd != null ? `${vault.tvlUsd.toLocaleString()} $` : '—'}</td>
                      <td className="px-2 py-2">
                        {vault.liquidityLow ? (
                          <span className="text-amber-700">Faible</span>
                        ) : (
                          <span className="text-emerald-700">OK</span>
                        )}
                      </td>
                      <td className="px-2 py-2 capitalize">{vault.withdrawAvailability}</td>
                      <td className="px-2 py-2 font-mono text-xs">{vault.trackedAssetsRaw}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {recon ? (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="m-0 font-ui text-lg font-semibold text-slate-900">Dernière réconciliation</h2>
              <p className="m-0 mt-1 text-sm text-slate-500">
                {recon.startedAt} — matched {recon.matchedCount} / {recon.itemsChecked} — mismatch {recon.mismatchCount} — PPS indispo{' '}
                {recon.ppsUnavailableCount} — liquidité {recon.liquidityWarningCount}
              </p>
              {recon.mismatches.length > 0 ? (
                <div className="mt-3 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                        <th className="px-2 py-2">Status</th>
                        <th className="px-2 py-2">Vault</th>
                        <th className="px-2 py-2">Wallet</th>
                        <th className="px-2 py-2">Delta raw</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recon.mismatches.map((row) => (
                        <tr key={row.id} className="border-b border-slate-100">
                          <td className="px-2 py-2">{row.status}</td>
                          <td className="px-2 py-2 font-mono text-xs">{row.vaultAddress}</td>
                          <td className="px-2 py-2 font-mono text-xs">{row.walletAddress}</td>
                          <td className="px-2 py-2 font-mono text-xs">{row.deltaAssetsRaw ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="m-0 mt-3 text-sm text-emerald-700">Aucun écart non résolu.</p>
              )}
            </section>
          ) : (
            <section className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
              Aucune réconciliation exécutée — lancer <code>pnpm ledgity:reconcile</code> ou le bouton ci-dessus.
            </section>
          )}
        </>
      ) : null}
    </div>
  )
}
