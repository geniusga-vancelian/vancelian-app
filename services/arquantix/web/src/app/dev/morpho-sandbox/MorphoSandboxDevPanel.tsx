'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'

type SandboxStatus = {
  sandboxEnabled: boolean
  devRouteAvailable: boolean
  session: { authenticated: boolean; personId: string | null }
  wallet: { address: string | null; privyWalletId: string | null }
  seed: {
    vaultConfigsPublished: number
    registryActive: number
    userSeeded: boolean
    userPositionCount: number
    userSandboxTxCount: number
  }
  counts: { vaults: number; positions: number; latestTransactions: number }
  monitoring: {
    globalStatus: string
    provider: string | null
    morphoGraphqlMocked: boolean
    baseRpcMocked: boolean
  }
}

async function devFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'include',
    cache: 'no-store',
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const message =
      typeof data === 'object' && data && 'message' in data && typeof data.message === 'string'
        ? data.message
        : `HTTP ${res.status}`
    throw new Error(message)
  }
  return data as T
}

function StatusRow({ label, value }: { label: string; value: string | number | boolean | null }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-200 py-2 text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-mono text-right text-slate-900">{String(value ?? '—')}</span>
    </div>
  )
}

export function MorphoSandboxDevPanel() {
  const [status, setStatus] = useState<SandboxStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [yieldAmount, setYieldAmount] = useState('1.25')

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const next = await devFetch<SandboxStatus>('/api/dev/morpho-sandbox/status')
      setStatus(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger le statut.')
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const runAction = useCallback(
    async (key: string, url: string, init?: RequestInit) => {
      setBusy(key)
      setMessage(null)
      setError(null)
      try {
        const data = await devFetch<{ ok?: boolean; result?: unknown }>(url, init)
        setMessage(JSON.stringify(data.result ?? data, null, 2))
        await refresh()
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Action échouée.')
      } finally {
        setBusy(null)
      }
    },
    [refresh],
  )

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-wide text-amber-700">Dev only</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">Morpho Local Sandbox</h1>
        <p className="mt-2 text-sm text-slate-600">
          Outil de confort pour tester Earn Morpho USDC sans blockchain réelle. Nécessite une session portail
          (Privy) active.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-3">
        <Link href="/app/invest" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800">
          Ouvrir /app/invest
        </Link>
        <Link
          href="/dev/wallet-sandbox"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50"
        >
          Wallet mock sandbox
        </Link>
        <Link
          href="/admin/morpho-vaults/monitoring"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50"
        >
          Monitoring admin
        </Link>
        <button
          type="button"
          onClick={() => void refresh()}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50"
          disabled={loading}
        >
          Rafraîchir
        </button>
      </div>

      {loading && <p className="text-sm text-slate-500">Chargement…</p>}
      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      )}

      {status && (
        <div className="mb-8 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Statut</h2>
          <StatusRow label="Sandbox enabled" value={status.sandboxEnabled} />
          <StatusRow label="Dev route available" value={status.devRouteAvailable} />
          <StatusRow label="Session authentifiée" value={status.session.authenticated} />
          <StatusRow label="Person ID" value={status.session.personId} />
          <StatusRow label="Wallet address" value={status.wallet.address} />
          <StatusRow label="Privy wallet ID" value={status.wallet.privyWalletId} />
          <StatusRow label="Vaults publiés (sandbox)" value={status.counts.vaults} />
          <StatusRow label="Positions (sandbox vaults)" value={status.counts.positions} />
          <StatusRow label="Tx utilisateur (sandbox)" value={status.seed.userSandboxTxCount} />
          <StatusRow label="User seeded" value={status.seed.userSeeded} />
          <StatusRow label="Monitoring global" value={status.monitoring.globalStatus} />
          <StatusRow label="Provider RPC" value={status.monitoring.provider} />
        </div>
      )}

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Actions</h2>

        <button
          type="button"
          disabled={!!busy}
          onClick={() => void runAction('seed', '/api/dev/morpho-sandbox/seed-current-user', { method: 'POST' })}
          className="block w-full rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          {busy === 'seed' ? 'Seed en cours…' : 'Seed my current user'}
        </button>

        <button
          type="button"
          disabled={!!busy}
          onClick={() => void runAction('reset', '/api/dev/morpho-sandbox/reset-current-user', { method: 'POST' })}
          className="block w-full rounded-md border border-red-300 px-4 py-2 text-sm text-red-800 hover:bg-red-50 disabled:opacity-50"
        >
          {busy === 'reset' ? 'Reset en cours…' : 'Reset my sandbox position'}
        </button>

        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            value={yieldAmount}
            onChange={(event) => setYieldAmount(event.target.value)}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="1.25"
          />
          <button
            type="button"
            disabled={!!busy}
            onClick={() =>
              void runAction('yield', '/api/dev/morpho-sandbox/add-yield', {
                method: 'POST',
                body: JSON.stringify({ amountUsdc: yieldAmount }),
              })
            }
            className="rounded-md bg-indigo-700 px-4 py-2 text-sm text-white hover:bg-indigo-600 disabled:opacity-50"
          >
            {busy === 'yield' ? 'Ajout…' : 'Add mock yield'}
          </button>
        </div>
      </div>

      {message && (
        <pre className="mt-6 overflow-x-auto rounded-md bg-slate-950 p-4 text-xs text-emerald-200">{message}</pre>
      )}

      {!status?.session.authenticated && !loading && (
        <p className="mt-6 text-sm text-amber-800">
          Connectez-vous d’abord sur{' '}
          <Link href="/app/login" className="underline">
            /app/login
          </Link>{' '}
          puis revenez ici pour seed votre utilisateur.
        </p>
      )}
    </div>
  )
}
