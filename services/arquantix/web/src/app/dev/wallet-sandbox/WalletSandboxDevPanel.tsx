'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'

import {
  fetchExternalWalletMockStatus,
  linkLocalMockExternalWalletDev,
  unlinkLocalMockExternalWalletDev,
} from '@/lib/wallet/externalWalletClient'
import { LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS } from '@/lib/wallet/externalWalletMock'
import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'

type MockStatus = Awaited<ReturnType<typeof fetchExternalWalletMockStatus>>

function StatusRow({ label, value }: { label: string; value: string | number | boolean | null }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-200 py-2 text-sm">
      <span className="text-slate-600">{label}</span>
      <span className="font-mono text-right text-slate-900">{String(value ?? '—')}</span>
    </div>
  )
}

export function WalletSandboxDevPanel() {
  const { selectLocalMockWallet, refreshExternalWallets } = useExecutionWallet()
  const [status, setStatus] = useState<MockStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const next = await fetchExternalWalletMockStatus()
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
    async (key: string, action: () => Promise<void>) => {
      setBusy(key)
      setMessage(null)
      setError(null)
      try {
        await action()
        await refreshExternalWallets()
        await refresh()
        setMessage('Action réussie.')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Action échouée.')
      } finally {
        setBusy(null)
      }
    },
    [refresh, refreshExternalWallets],
  )

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-wide text-amber-700">Dev only</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">Wallet Sandbox (Local Mock)</h1>
        <p className="mt-2 text-sm text-slate-600">
          Tester Morpho et LI.FI avec un wallet externe mocké — sans MetaMask, sans Reown, sans RPC live.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap gap-3">
        <Link href="/app/invest" className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800">
          Go to Invest
        </Link>
        <Link href="/app/swap" className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50">
          Go to Swap
        </Link>
        <Link
          href="/dev/morpho-sandbox"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50"
        >
          Morpho sandbox
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
          <StatusRow label="Mock enabled" value={status.mockEnabled} />
          <StatusRow label="Dev route available" value={status.devRouteAvailable} />
          <StatusRow label="Session authentifiée" value={status.session.authenticated} />
          <StatusRow label="Person ID" value={status.session.personId} />
          <StatusRow label="Mock linked" value={status.linked} />
          <StatusRow label="Mock address" value={status.wallet?.address ?? LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS} />
        </div>
      )}

      <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Actions</h2>

        <button
          type="button"
          disabled={!!busy || !status?.devRouteAvailable}
          onClick={() =>
            void runAction('link', async () => {
              await linkLocalMockExternalWalletDev()
              selectLocalMockWallet()
            })
          }
          className="block w-full rounded-md bg-emerald-700 px-4 py-2 text-sm text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          {busy === 'link' ? 'Liaison…' : 'Link Local Mock Wallet'}
        </button>

        <button
          type="button"
          disabled={!!busy || !status?.linked}
          onClick={() => void runAction('select', async () => selectLocalMockWallet())}
          className="block w-full rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-800 hover:bg-slate-50 disabled:opacity-50"
        >
          {busy === 'select' ? 'Sélection…' : 'Select as execution wallet'}
        </button>

        <button
          type="button"
          disabled={!!busy || !status?.linked}
          onClick={() => void runAction('reset', async () => unlinkLocalMockExternalWalletDev())}
          className="block w-full rounded-md border border-red-300 px-4 py-2 text-sm text-red-800 hover:bg-red-50 disabled:opacity-50"
        >
          {busy === 'reset' ? 'Reset…' : 'Reset mock wallet'}
        </button>
      </div>

      {message && (
        <p className="mt-6 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {message}
        </p>
      )}

      {!status?.session.authenticated && !loading && status?.devRouteAvailable && (
        <p className="mt-6 text-sm text-amber-800">
          Connectez-vous d’abord sur{' '}
          <Link href="/app/login" className="underline">
            /app/login
          </Link>{' '}
          puis revenez ici.
        </p>
      )}

      {!status?.devRouteAvailable && !loading && (
        <p className="mt-6 text-sm text-amber-800">
          Activez{' '}
          <code className="rounded bg-amber-100 px-1">EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true</code> avec{' '}
          <code className="rounded bg-amber-100 px-1">MORPHO_LOCAL_SANDBOX_ENABLED=true</code> ou{' '}
          <code className="rounded bg-amber-100 px-1">LIFI_LOCAL_SANDBOX_ENABLED=true</code>.
        </p>
      )}
    </div>
  )
}
