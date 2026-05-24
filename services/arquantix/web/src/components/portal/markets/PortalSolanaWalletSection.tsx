'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Check, Copy, ExternalLink, Wallet } from 'lucide-react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { Button } from '@/components/ui/button'
import {
  createPortalSolanaWallet,
  fetchPortalSolanaWalletStatus,
  resolveSolanaExplorerAddressUrl,
  resolveSolanaWalletUiState,
  type SolanaWalletPayload,
  type SolanaWalletStatusPayload,
} from '@/lib/portal/solanaWalletClient'
import { portalCryptoWalletAssetRoute, portalDedicatedDepositRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  className?: string
}

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

export function PortalSolanaWalletSection({ className }: Props) {
  const [walletStatus, setWalletStatus] = useState<SolanaWalletStatusPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  const loadWallet = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const row = await fetchPortalSolanaWalletStatus()
      setWalletStatus(row)
    } catch (err) {
      setWalletStatus(null)
      setError(err instanceof Error ? err.message : 'Unable to load Solana wallet.')
    } finally {
      setLoading(false)
    }
  }, [])

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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to create Solana wallet.')
    } finally {
      setCreating(false)
    }
  }, [creating])

  const handleCopy = useCallback(async (address: string) => {
    try {
      await navigator.clipboard.writeText(address)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setError('Unable to copy address.')
    }
  }, [])

  const isLinkMode = uiState.status === 'unlinked'

  return (
    <section
      className={cn(
        'rounded-v-card border border-v-fg-10 bg-v-card p-5 sm:p-6',
        className,
      )}
    >
      <div className="mb-4 flex items-center gap-2">
        <Wallet className="h-5 w-5 text-v-fg-muted" aria-hidden />
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">Solana wallet</h2>
      </div>

      {uiState.status === 'loading' ? (
        <p className="m-0 font-ui text-[14px] text-v-fg-muted">Loading wallet…</p>
      ) : null}

      {uiState.status === 'missing' ? (
        <div className="space-y-3">
          <p className="m-0 font-ui text-[14px] text-v-fg-body">
            Create your Privy Solana wallet to receive SOL on Solana and link it to your Vancelian
            account.
          </p>
          <Button type="button" onClick={() => void handleCreateOrLink()} disabled={creating}>
            {creating ? 'Creating…' : 'Create wallet'}
          </Button>
        </div>
      ) : null}

      {uiState.status === 'unlinked' ? (
        <div className="space-y-3">
          <p className="m-0 font-ui text-[14px] text-v-fg-body">
            Your Solana wallet already exists on Privy
            {uiState.address
              ? ` (${uiState.address.slice(0, 4)}…${uiState.address.slice(-4)})`
              : ''}
            . Link it to your Vancelian account to see balances and deposit addresses in the app.
          </p>
          <div className="rounded-v-input border border-v-fg-10 bg-v-fg-05 px-3 py-3">
            <p className="m-0 font-mono text-[13px] leading-relaxed break-all text-v-fg">
              {uiState.address}
            </p>
          </div>
          <Button type="button" onClick={() => void handleCreateOrLink()} disabled={creating}>
            {creating ? 'Linking wallet…' : 'Link wallet to Vancelian'}
          </Button>
        </div>
      ) : null}

      {uiState.status === 'error' ? (
        <div className="space-y-3">
          <p className="m-0 font-ui text-[14px] text-v-error">{uiState.message}</p>
          <Button type="button" variant="outline" onClick={() => void loadWallet()}>
            Retry
          </Button>
        </div>
      ) : null}

      {uiState.status === 'ready' ? (
        <div className="space-y-3">
          <p className="m-0 font-ui text-[13px] text-v-fg-muted">
            {uiState.wallet.created
              ? 'Your Solana wallet was linked to your Vancelian account.'
              : 'Your Solana wallet is linked to your Vancelian account.'}
          </p>
          <div className="rounded-v-input border border-v-fg-10 bg-v-fg-05 px-3 py-3">
            <p className="m-0 font-mono text-[13px] leading-relaxed break-all text-v-fg">
              {uiState.wallet.address}
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <Button
              type="button"
              variant="outline"
              className="gap-2"
              onClick={() => void handleCopy(uiState.wallet.address)}
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  Copy address
                </>
              )}
            </Button>
            <Button type="button" variant="outline" className="gap-2" asChild>
              <a
                href={resolveSolanaExplorerAddressUrl(uiState.wallet.address)}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink className="h-4 w-4" />
                Verify on-chain
              </a>
            </Button>
            <Button type="button" className="gap-2" asChild>
              <PortalNavLink href={portalDedicatedDepositRoute('sol')!}>
                <Wallet className="h-4 w-4" />
                Recevoir des SOL
              </PortalNavLink>
            </Button>
            <Button type="button" variant="outline" className="gap-2" asChild>
              <PortalNavLink href={portalCryptoWalletAssetRoute('sol')}>
                Voir ma position SOL
              </PortalNavLink>
            </Button>
          </div>
        </div>
      ) : null}

      {!loading && uiState.status !== 'error' && uiState.status !== 'ready' ? (
        <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
          {isLinkMode
            ? 'Links your existing Privy Solana wallet to Vancelian so deposits and balances appear in the dashboard.'
            : 'Creates an embedded Solana wallet via Privy, linked to your Vancelian account — same principle as the EVM wallet flow.'}
        </p>
      ) : null}
    </section>
  )
}
