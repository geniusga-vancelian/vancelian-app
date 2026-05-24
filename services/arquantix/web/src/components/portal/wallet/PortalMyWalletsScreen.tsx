'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Wallet } from 'lucide-react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalSettingsCard, PortalSettingsRow } from '@/components/portal/profile/PortalProfileUi'
import { Button } from '@/components/ui/button'
import { formatEvmNetworkShort } from '@/lib/portal/evmNetworkLabel'
import {
  findEvmPersonWallet,
  fetchPortalPersonCryptoWallets,
  type PortalPersonCryptoWallet,
} from '@/lib/portal/privyWalletClient'
import {
  PORTAL_ROUTES,
  portalWalletCreateRoute,
} from '@/lib/portal/portalRouting'
import {
  fetchPortalSolanaWalletStatus,
  type SolanaWalletStatusPayload,
} from '@/lib/portal/solanaWalletClient'

function formatWalletAddress(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

function WalletCreateAction({ chain }: { chain: 'evm' | 'solana' }) {
  return (
    <Button type="button" size="sm" className="shrink-0" asChild>
      <PortalNavLink href={portalWalletCreateRoute(chain)}>Create wallet</PortalNavLink>
    </Button>
  )
}

type WalletRowProps = {
  title: string
  loading: boolean
  created: boolean
  address?: string
  networkLabel?: string
  depositHref?: string
  createChain: 'evm' | 'solana'
  emptyHint: string
}

function WalletRow({
  title,
  loading,
  created,
  address,
  networkLabel,
  depositHref,
  createChain,
  emptyHint,
}: WalletRowProps) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 px-4 py-4 sm:px-5">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-v-fg-05">
          <Loader2 className="h-4 w-4 animate-spin text-v-fg-muted" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-ui text-[16px] font-medium text-v-fg">{title}</span>
          <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">Loading…</span>
        </span>
      </div>
    )
  }

  if (!created) {
    return (
      <div className="flex items-center gap-3 px-4 py-4 sm:px-5">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-v-fg-05">
          <Wallet className="h-5 w-5 text-v-fg-muted" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block font-ui text-[16px] font-medium text-v-fg">{title}</span>
          <span className="mt-0.5 block font-ui text-[13px] leading-snug text-v-fg-muted">
            {emptyHint}
          </span>
        </span>
        <WalletCreateAction chain={createChain} />
      </div>
    )
  }

  const subtitle = [networkLabel, address ? formatWalletAddress(address) : null]
    .filter(Boolean)
    .join(' · ')

  return (
    <PortalSettingsRow
      title={title}
      subtitle={subtitle || undefined}
      href={depositHref}
      leading={
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-v-fg-05">
          <Wallet className="h-5 w-5 text-v-fg" aria-hidden />
        </span>
      }
    />
  )
}

export function PortalMyWalletsScreen() {
  const [evmWallet, setEvmWallet] = useState<PortalPersonCryptoWallet | null>(null)
  const [solanaStatus, setSolanaStatus] = useState<SolanaWalletStatusPayload | null>(null)
  const [loadingEvm, setLoadingEvm] = useState(true)
  const [loadingSolana, setLoadingSolana] = useState(true)
  const [error, setError] = useState('')

  const loadWallets = useCallback(async () => {
    setError('')
    setLoadingEvm(true)
    setLoadingSolana(true)

    const [evmResult, solanaResult] = await Promise.allSettled([
      fetchPortalPersonCryptoWallets(),
      fetchPortalSolanaWalletStatus(),
    ])

    const errors: string[] = []

    if (evmResult.status === 'fulfilled') {
      setEvmWallet(findEvmPersonWallet(evmResult.value))
    } else {
      setEvmWallet(null)
      errors.push(
        evmResult.reason instanceof Error ? evmResult.reason.message : 'Unable to load EVM wallet.',
      )
    }
    setLoadingEvm(false)

    if (solanaResult.status === 'fulfilled') {
      setSolanaStatus(solanaResult.value)
    } else {
      setSolanaStatus(null)
      errors.push(
        solanaResult.reason instanceof Error
          ? solanaResult.reason.message
          : 'Unable to load Solana wallet.',
      )
    }
    setLoadingSolana(false)

    if (errors.length > 0) {
      setError(errors[0] ?? '')
    }
  }, [])

  useEffect(() => {
    void loadWallets()
  }, [loadWallets])

  const solanaLinked = solanaStatus?.status === 'linked' && Boolean(solanaStatus.address?.trim())

  return (
    <PortalPageContainer className="py-8 sm:py-10">
      <div className="mx-auto w-full max-w-lg">
        <h1 className="m-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg">My wallets</h1>
        <p className="mt-2 mb-6 font-ui text-[15px] leading-relaxed text-v-fg-body">
          Privy embedded wallets linked to your Vancelian account.
        </p>

        <PortalSettingsCard>
          <WalletRow
            title="EVM"
            loading={loadingEvm}
            created={Boolean(evmWallet?.address)}
            address={evmWallet?.address}
            networkLabel={
              evmWallet ? formatEvmNetworkShort(evmWallet.chain_id) : 'Ethereum · ERC-20'
            }
            depositHref={PORTAL_ROUTES.walletDeposit}
            createChain="evm"
            emptyHint="Create an EVM wallet to receive ETH and ERC-20 tokens."
          />
          <WalletRow
            title="Solana"
            loading={loadingSolana}
            created={solanaLinked}
            address={solanaStatus?.address}
            networkLabel="Solana · SOL"
            depositHref={PORTAL_ROUTES.walletDepositSol}
            createChain="solana"
            emptyHint="Create a Solana wallet to receive SOL on Solana."
          />
        </PortalSettingsCard>

        {error ? (
          <div className="mt-4 space-y-3">
            <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
            <Button type="button" variant="outline" onClick={() => void loadWallets()}>
              Retry
            </Button>
          </div>
        ) : null}
      </div>
    </PortalPageContainer>
  )
}
