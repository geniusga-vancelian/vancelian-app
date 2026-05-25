'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Wallet } from 'lucide-react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalSettingsCard, PortalSettingsRow, PortalSectionTitle } from '@/components/portal/profile/PortalProfileUi'
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
import { ConnectExternalWalletButton } from '@/components/wallet/ConnectExternalWalletButton'

function formatWalletAddress(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

function WalletCreateAction({ chain }: { chain: 'evm' | 'solana' }) {
  return (
    <Button type="button" size="sm" className="shrink-0" asChild>
      <PortalNavLink href={portalWalletCreateRoute(chain)}>Créer</PortalNavLink>
    </Button>
  )
}

type WalletRowProps = {
  title: string
  loading: boolean
  created: boolean
  address?: string
  networkLabel?: string
  providerLabel?: string
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
  providerLabel,
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
          <span className="mt-0.5 block font-ui text-[13px] text-v-fg-muted">Chargement…</span>
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
          <span className="mt-0.5 block font-ui text-[13px] leading-snug text-v-fg-muted">{emptyHint}</span>
        </span>
        <WalletCreateAction chain={createChain} />
      </div>
    )
  }

  const subtitle = [providerLabel, networkLabel, address ? formatWalletAddress(address) : null]
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

/** Wallets Privy + externes — affichés directement dans le profil. */
export function PortalProfileWalletsSection() {
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
        evmResult.reason instanceof Error ? evmResult.reason.message : 'Impossible de charger le wallet EVM.',
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
          : 'Impossible de charger le wallet Solana.',
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
    <section id="wallets" className="flex scroll-mt-24 flex-col gap-6">
      <div>
        <PortalSectionTitle>Mes wallets</PortalSectionTitle>
        <p className="m-0 mt-2 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          Wallets Vancelian (Privy) et wallets externes (MetaMask) utilisés pour la DeFi et les swaps.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-muted">
          Vancelian (Privy)
        </p>
        <PortalSettingsCard>
          <WalletRow
            title="Wallet EVM"
            loading={loadingEvm}
            created={Boolean(evmWallet?.address)}
            address={evmWallet?.address}
            providerLabel="Privy embedded"
            networkLabel={evmWallet ? formatEvmNetworkShort(evmWallet.chain_id) : 'Ethereum · ERC-20'}
            depositHref={PORTAL_ROUTES.walletDeposit}
            createChain="evm"
            emptyHint="Créez un wallet EVM pour recevoir ETH et tokens ERC-20."
          />
          <WalletRow
            title="Wallet Solana"
            loading={loadingSolana}
            created={solanaLinked}
            address={solanaStatus?.address}
            providerLabel="Privy embedded"
            networkLabel="Solana · SOL"
            depositHref={PORTAL_ROUTES.walletDepositSol}
            createChain="solana"
            emptyHint="Créez un wallet Solana pour recevoir du SOL."
          />
        </PortalSettingsCard>
      </div>

      <div className="flex flex-col gap-3">
        <p className="m-0 font-ui text-[13px] font-semibold uppercase tracking-wide text-v-fg-muted">
          Externes (MetaMask)
        </p>
        <PortalSettingsCard>
          <div className="px-4 py-4 sm:px-5">
            <ConnectExternalWalletButton compact />
          </div>
        </PortalSettingsCard>
      </div>

      {error ? (
        <div className="space-y-3">
          <p className="m-0 font-ui text-[14px] text-v-error">{error}</p>
          <Button type="button" variant="outline" size="sm" onClick={() => void loadWallets()}>
            Réessayer
          </Button>
        </div>
      ) : null}
    </section>
  )
}
