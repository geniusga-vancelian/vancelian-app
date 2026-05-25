'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, Wallet } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { Button } from '@/components/ui/button'
import { portalProfileWalletsRoute } from '@/lib/portal/portalRouting'
import {
  createPortalSolanaWallet,
  fetchPortalSolanaWalletStatus,
  resolveSolanaWalletUiState,
  type SolanaWalletPayload,
  type SolanaWalletStatusPayload,
} from '@/lib/portal/solanaWalletClient'

function toLinkedStatus(wallet: SolanaWalletPayload): SolanaWalletStatusPayload {
  return {
    status: 'linked',
    chain_type: 'solana',
    address: wallet.address,
    wallet_id: wallet.wallet_id,
    person_wallet_id: wallet.person_wallet_id,
    created: wallet.created,
  }
}

export function PortalCreateSolanaWalletScreen() {
  const router = useRouter()
  const [walletStatus, setWalletStatus] = useState<SolanaWalletStatusPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const loadWallet = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const row = await fetchPortalSolanaWalletStatus()
      setWalletStatus(row)
      if (row.status === 'linked') {
        router.replace(portalProfileWalletsRoute())
      }
    } catch (err) {
      setWalletStatus(null)
      setError(err instanceof Error ? err.message : 'Unable to load Solana wallet.')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    void loadWallet()
  }, [loadWallet])

  const uiState = useMemo(
    () => resolveSolanaWalletUiState({ loading, error, walletStatus }),
    [error, loading, walletStatus],
  )

  const handleCreateOrLink = useCallback(async () => {
    if (creating) return
    setCreating(true)
    setError('')
    try {
      const created = await createPortalSolanaWallet()
      setWalletStatus(toLinkedStatus(created))
      router.replace(portalProfileWalletsRoute())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create Solana wallet.')
    } finally {
      setCreating(false)
    }
  }, [creating, router])

  const isLinkMode = uiState.status === 'unlinked'

  if (loading) {
    return (
      <PortalPageContainer className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" aria-hidden />
        <span className="sr-only">Loading</span>
      </PortalPageContainer>
    )
  }

  return (
    <PortalPageContainer className="py-8 sm:py-10">
      <div className="mx-auto w-full max-w-lg">
        <div className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card p-6 shadow-v-subtle sm:p-8">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-full bg-v-fg-05">
            <Wallet className="h-6 w-6 text-v-fg" aria-hidden />
          </div>

          <h1 className="m-0 font-ui text-[24px] font-semibold tracking-v-tight text-v-fg">
            {isLinkMode ? 'Link your Solana wallet' : 'Create your Solana wallet'}
          </h1>

          {isLinkMode ? (
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              Your Solana wallet already exists on Privy
              {uiState.address
                ? ` (${uiState.address.slice(0, 4)}…${uiState.address.slice(-4)})`
                : ''}
              . Link it to your Vancelian account to receive SOL and see balances in the app.
            </p>
          ) : (
            <p className="mt-3 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              Create a Privy embedded Solana wallet linked to your Vancelian account — same
              principle as the EVM wallet flow.
            </p>
          )}

          {isLinkMode && uiState.status === 'unlinked' ? (
            <div className="mt-6 rounded-v-input border border-v-fg-10 bg-v-fg-05 px-3 py-3">
              <p className="m-0 font-mono text-[13px] leading-relaxed break-all text-v-fg">
                {uiState.address}
              </p>
            </div>
          ) : null}

          <div className="mt-8">
            <Button
              type="button"
              className="w-full gap-2"
              disabled={creating || uiState.status === 'error'}
              onClick={() => void handleCreateOrLink()}
            >
              {creating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  {isLinkMode ? 'Linking wallet…' : 'Creating wallet…'}
                </>
              ) : (
                <>
                  <Wallet className="h-4 w-4" aria-hidden />
                  {isLinkMode ? 'Link wallet to Vancelian' : 'Create wallet'}
                </>
              )}
            </Button>
            <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
              {isLinkMode
                ? 'Links your existing Privy Solana wallet to Vancelian so deposits and balances appear in the dashboard.'
                : 'Creates an embedded Solana wallet via Privy, linked to your Vancelian account.'}
            </p>
          </div>

          {uiState.status === 'error' ? (
            <div className="mt-6 space-y-3">
              <p className="m-0 font-ui text-[14px] text-v-error">{uiState.message}</p>
              <Button type="button" variant="outline" onClick={() => void loadWallet()}>
                Retry
              </Button>
            </div>
          ) : null}

          {error ? <p className="portal-auth__error mt-6">{error}</p> : null}
        </div>
      </div>
    </PortalPageContainer>
  )
}
