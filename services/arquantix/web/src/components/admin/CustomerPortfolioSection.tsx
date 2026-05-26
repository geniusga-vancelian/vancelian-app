'use client'

import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { RefreshCw, Wallet } from 'lucide-react'
import { toastError, toastSuccess } from '@/lib/admin/toast'

type PortfolioSummary = {
  total_value_eur: string
  fiat_value_eur: string
  crypto_value_eur: string
  privy_value_eur: string
  exclusive_offers_value_eur: string
  bundles_value_eur: string
  positions_count: number
  exclusive_offers_count: number
  bundles_count: number
  transactions_count: number
}

type CryptoRow = {
  asset: string
  name: string
  total_balance: string
  total_available: string
  platform_balance: string
  privy_balance: string
  source: 'platform' | 'privy' | 'merged'
  portfolio_scope: string
  price_eur?: string | null
  estimated_value_eur?: string | null
}

type ExclusiveOfferRow = {
  pool_id: string
  title: string
  asset: string
  status?: string | null
  total_supplied: string
  earning_amount: string
  idle_amount: string
  accrued_interest: string
  value_eur: string
  apy?: number | null
  project_id?: string | null
}

type BundleRow = {
  portfolio_id: string
  name: string
  status: string
  total_value_eur: string
  positions_count: number
  positions: {
    asset: string
    quantity: string
    position_type: string
    market_value_eur?: string | null
  }[]
}

type TransactionRow = {
  id: string
  source: string
  category: string
  direction: string
  asset: string
  amount: string
  currency: string
  status: string
  title: string
  subtitle?: string | null
  reference?: string | null
  created_at: string
}

type PrivyAdmin = {
  identity?: { privy_user_id?: string | null; is_linked?: boolean } | null
  reconcile_available?: boolean
}

type PortfolioPayload = {
  availability: string
  reference_currency?: string | null
  summary: PortfolioSummary
  crypto: CryptoRow[]
  exclusive_offers: ExclusiveOfferRow[]
  bundles: BundleRow[]
  transactions: TransactionRow[]
  privy_admin?: PrivyAdmin
}

const TABS = [
  { id: 'overview', label: 'Vue d’ensemble' },
  { id: 'crypto', label: 'Crypto' },
  { id: 'exclusive', label: 'Offres exclusives' },
  { id: 'bundles', label: 'Bundles' },
  { id: 'transactions', label: 'Transactions' },
] as const

type TabId = (typeof TABS)[number]['id']

function sourceBadge(source: CryptoRow['source']) {
  if (source === 'merged') return <Badge className="bg-indigo-700 text-white hover:bg-indigo-700">PE + Privy</Badge>
  if (source === 'privy') return <Badge variant="secondary">Privy</Badge>
  return <Badge variant="outline">Plateforme</Badge>
}

function fmtEur(value?: string | null) {
  if (!value) return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return value
  return `${n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
}

function fmtDate(value: string) {
  return new Date(value).toLocaleString('fr-FR')
}

async function parseErrorMessage(res: Response) {
  try {
    const data = (await res.json()) as { detail?: string; message?: string; error?: string }
    return data.detail || data.message || data.error || `HTTP ${res.status}`
  } catch {
    return `HTTP ${res.status}`
  }
}

export function CustomerPortfolioSection({ personId }: { personId: string }) {
  const [tab, setTab] = useState<TabId>('overview')
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<PortfolioPayload | null>(null)
  const [simAmount, setSimAmount] = useState('100')
  const [simAsset, setSimAsset] = useState('USDC')
  const [simulating, setSimulating] = useState(false)
  const [syncingWallets, setSyncingWallets] = useState(false)
  const [reconcilingBalances, setReconcilingBalances] = useState(false)
  const [backfilling, setBackfilling] = useState(false)
  const [backfillTxHash, setBackfillTxHash] = useState('')
  const [backfillChainId, setBackfillChainId] = useState('8453')
  const [lastReconMessage, setLastReconMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(
        `/api/admin/customers/${encodeURIComponent(personId)}/portfolio?tx_limit=100`,
        { cache: 'no-store' },
      )
      if (!res.ok) throw new Error(await parseErrorMessage(res))
      const json = (await res.json()) as PortfolioPayload
      setData(json)
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Impossible de charger le portefeuille')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [personId])

  useEffect(() => {
    void load()
  }, [load])

  const handleSimulate = async () => {
    if (!simAmount.trim()) return
    setSimulating(true)
    try {
      const res = await fetch('/api/admin/privy-wallet/simulate-deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_id: personId,
          amount: simAmount.trim(),
          asset: simAsset.trim().toUpperCase(),
        }),
      })
      if (!res.ok) throw new Error(await parseErrorMessage(res))
      const result = (await res.json()) as { message?: string }
      toastSuccess(result.message || 'Dépôt simulé')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Simulation échouée')
    } finally {
      setSimulating(false)
    }
  }

  const handleSyncWallets = async () => {
    setSyncingWallets(true)
    try {
      const res = await fetch('/api/admin/privy-wallet/reconcile-wallets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person_id: personId }),
      })
      if (!res.ok) throw new Error(await parseErrorMessage(res))
      const result = (await res.json()) as { message?: string }
      toastSuccess(result.message || 'Adresses Privy synchronisées')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Sync adresses échouée')
    } finally {
      setSyncingWallets(false)
    }
  }

  const handleReconcileBalances = async () => {
    setReconcilingBalances(true)
    setLastReconMessage(null)
    try {
      const res = await fetch('/api/admin/privy-wallet/reconciliation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person_id: personId, auto_heal: true }),
      })
      if (!res.ok) throw new Error(await parseErrorMessage(res))
      const result = (await res.json()) as {
        message?: string
        healed_count?: number
        replayed_webhooks?: number
        unresolved_count?: number
      }
      setLastReconMessage(result.message || 'Réconciliation terminée')
      toastSuccess(result.message || 'Réconciliation soldes terminée')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Réconciliation soldes échouée')
    } finally {
      setReconcilingBalances(false)
    }
  }

  const handleBackfillDeposit = async () => {
    const txHash = backfillTxHash.trim()
    if (!txHash) return
    setBackfilling(true)
    try {
      const res = await fetch('/api/admin/privy-wallet/backfill-deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_id: personId,
          chain_id: Number(backfillChainId) || 8453,
          tx_hash: txHash,
        }),
      })
      if (!res.ok) throw new Error(await parseErrorMessage(res))
      const result = (await res.json()) as { message?: string }
      toastSuccess(result.message || 'Backfill appliqué')
      setBackfillTxHash('')
      await load()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Backfill échoué')
    } finally {
      setBackfilling(false)
    }
  }

  if (loading && !data) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-sm text-slate-500">
        Chargement du portefeuille…
      </div>
    )
  }

  if (!data) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-600">
        Portefeuille indisponible pour ce client.
        <Button variant="outline" size="sm" className="ml-3" onClick={() => void load()}>
          Réessayer
        </Button>
      </div>
    )
  }

  const s = data.summary

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Wallet className="h-5 w-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-slate-900">Portefeuille client</h2>
          {data.reference_currency ? (
            <Badge variant="outline">Devise ref. {data.reference_currency}</Badge>
          ) : null}
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t.id
                ? 'bg-indigo-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SummaryCard label="Patrimoine total (EUR)" value={fmtEur(s.total_value_eur)} highlight />
          <SummaryCard label="Cash / fiat" value={fmtEur(s.fiat_value_eur)} />
          <SummaryCard label="Crypto (PE + Privy)" value={fmtEur(s.crypto_value_eur)} />
          <SummaryCard label="Dont Privy on-chain" value={fmtEur(s.privy_value_eur)} />
          <SummaryCard label="Offres exclusives" value={fmtEur(s.exclusive_offers_value_eur)} />
          <SummaryCard label="Bundles" value={fmtEur(s.bundles_value_eur)} />
        </div>
      ) : null}

      {tab === 'crypto' ? (
        <div className="space-y-4">
          <DataTable
            empty="Aucun actif crypto."
            headers={['Actif', 'Solde total', 'Plateforme', 'Privy', 'Valorisation EUR', 'Source']}
            rows={data.crypto.map((row) => [
              <span key="a" className="font-medium">{row.asset} <span className="text-slate-400">{row.name}</span></span>,
              `${row.total_balance} (dispo. ${row.total_available})`,
              row.platform_balance,
              row.privy_balance,
              fmtEur(row.estimated_value_eur),
              sourceBadge(row.source),
            ])}
          />

          {data.privy_admin?.identity?.is_linked ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 space-y-4">
              <p className="text-xs font-semibold uppercase text-slate-500">Outils admin Privy</p>
              <div className="flex flex-wrap gap-2 items-end">
                <div>
                  <label className="text-xs text-slate-500">Montant</label>
                  <Input value={simAmount} onChange={(e) => setSimAmount(e.target.value)} className="w-28" />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Actif</label>
                  <Input value={simAsset} onChange={(e) => setSimAsset(e.target.value)} className="w-24" />
                </div>
                <Button size="sm" onClick={() => void handleSimulate()} disabled={simulating}>
                  Simuler dépôt
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => void handleSyncWallets()}
                  disabled={syncingWallets}
                >
                  Sync adresses Privy
                </Button>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => void handleReconcileBalances()}
                  disabled={reconcilingBalances}
                >
                  Réconcilier soldes
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 items-end border-t border-slate-200 pt-3">
                <div>
                  <label className="text-xs text-slate-500">Tx hash (backfill)</label>
                  <Input
                    value={backfillTxHash}
                    onChange={(e) => setBackfillTxHash(e.target.value)}
                    placeholder="0x…"
                    className="w-72 font-mono text-xs"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500">Chain ID</label>
                  <Input
                    value={backfillChainId}
                    onChange={(e) => setBackfillChainId(e.target.value)}
                    className="w-24"
                  />
                </div>
                <Button size="sm" variant="secondary" onClick={() => void handleBackfillDeposit()} disabled={backfilling}>
                  Backfill dépôt
                </Button>
              </div>
              {lastReconMessage ? (
                <p className="text-xs text-slate-600">{lastReconMessage}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}

      {tab === 'exclusive' ? (
        <DataTable
          empty="Aucune offre exclusive."
          headers={['Offre', 'Actif', 'Statut', 'Engagé', 'En earning', 'Idle', 'Intérêts', 'Valeur EUR', 'APY']}
          rows={data.exclusive_offers.map((row) => [
            row.title,
            row.asset,
            row.status ?? '—',
            row.total_supplied,
            row.earning_amount,
            row.idle_amount,
            row.accrued_interest,
            fmtEur(row.value_eur),
            row.apy != null ? `${row.apy.toFixed(2)} %` : '—',
          ])}
        />
      ) : null}

      {tab === 'bundles' ? (
        <div className="space-y-4">
          {data.bundles.length === 0 ? (
            <p className="text-sm text-slate-500">Aucun bundle actif.</p>
          ) : (
            data.bundles.map((bundle) => (
              <div key={bundle.portfolio_id} className="rounded-lg border border-slate-200 overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-50 px-4 py-3">
                  <div>
                    <p className="font-medium text-slate-900">{bundle.name}</p>
                    <p className="text-xs text-slate-500">
                      {bundle.status} · {bundle.positions_count} actif(s) · {fmtEur(bundle.total_value_eur)}
                    </p>
                  </div>
                </div>
                <table className="min-w-full text-xs">
                  <thead className="bg-white text-left text-slate-600">
                    <tr>
                      <th className="px-4 py-2 font-medium">Actif</th>
                      <th className="px-4 py-2 font-medium">Quantité</th>
                      <th className="px-4 py-2 font-medium">Type</th>
                      <th className="px-4 py-2 font-medium">Valeur EUR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bundle.positions.map((p, idx) => (
                      <tr key={`${bundle.portfolio_id}-${idx}`} className="border-t border-slate-100">
                        <td className="px-4 py-2">{p.asset}</td>
                        <td className="px-4 py-2">{p.quantity}</td>
                        <td className="px-4 py-2">{p.position_type}</td>
                        <td className="px-4 py-2">{fmtEur(p.market_value_eur)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))
          )}
        </div>
      ) : null}

      {tab === 'transactions' ? (
        <DataTable
          empty="Aucune transaction."
          headers={['Date', 'Titre', 'Source', 'Sens', 'Montant', 'Statut', 'Référence']}
          rows={data.transactions.map((row) => [
            fmtDate(row.created_at),
            <span key="t">{row.title}{row.subtitle ? <span className="block text-slate-400">{row.subtitle}</span> : null}</span>,
            row.source,
            row.direction,
            `${row.amount} ${row.asset}`,
            row.status,
            <span key="r" className="font-mono text-[10px] truncate max-w-[120px] inline-block" title={row.reference ?? ''}>{row.reference ?? '—'}</span>,
          ])}
        />
      ) : null}
    </div>
  )
}

function SummaryCard({
  label,
  value,
  highlight,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div
      className={`rounded-xl border p-4 ${
        highlight ? 'border-indigo-200 bg-indigo-50/40' : 'border-slate-200 bg-white'
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-xl font-semibold ${highlight ? 'text-indigo-900' : 'text-slate-900'}`}>{value}</p>
    </div>
  )
}

function DataTable({
  headers,
  rows,
  empty,
}: {
  headers: string[]
  rows: ReactNode[][]
  empty: string
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-slate-500">{empty}</p>
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-3 py-2 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, ri) => (
            <tr key={ri} className="border-t border-slate-100 align-top">
              {cells.map((cell, ci) => (
                <td key={ci} className="px-3 py-2 text-slate-800">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
