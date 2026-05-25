import type { PortalChain } from '@/config/portalChains'
import type { PortalPersonCryptoWallet } from '@/lib/portal/privyWalletClient'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
import type { SolanaWalletStatusPayload } from '@/lib/portal/solanaWalletClient'
import type { ExternalWalletConnector, VerifiedExternalWallet } from '@/lib/wallet/executionWalletTypes'

const CONNECTOR_LABELS: Record<ExternalWalletConnector, string> = {
  metamask: 'MetaMask',
  walletconnect: 'WalletConnect',
  injected: 'Wallet injecté',
  local_mock: 'Mock dev',
}

export function formatPortalWalletAddressShort(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

function buildPrivyScope(wallet: PortalPersonCryptoWallet, chainType: 'evm' | 'solana'): PortalWalletScope {
  return {
    id: `privy:${wallet.id}`,
    kind: 'privy_embedded',
    label: 'Wallet Vancelian (Privy)',
    shortLabel: 'Privy',
    address: wallet.address,
    personWalletId: wallet.id,
    chainType,
  }
}

function buildSolanaPrivyScope(status: SolanaWalletStatusPayload): PortalWalletScope | null {
  const address = status.address?.trim()
  const personWalletId = status.person_wallet_id?.trim()
  if (!address || !personWalletId) return null
  return {
    id: `privy:${personWalletId}`,
    kind: 'privy_embedded',
    label: 'Wallet Vancelian (Privy)',
    shortLabel: 'Privy',
    address,
    personWalletId,
    chainType: 'solana',
  }
}

function buildExternalScope(wallet: VerifiedExternalWallet): PortalWalletScope {
  const providerLabel = CONNECTOR_LABELS[wallet.walletProvider] ?? 'Externe'
  const addressShort = formatPortalWalletAddressShort(wallet.address)
  return {
    id: `external:${wallet.id}`,
    kind: 'external_evm',
    label: `${providerLabel} · ${addressShort}`,
    shortLabel: providerLabel,
    address: wallet.address,
    externalWalletId: wallet.id,
    chainType: 'evm',
  }
}

/** Wallets disponibles pour l’écosystème sélectionné (navbar). */
export function buildPortalWalletScopes(args: {
  chain: PortalChain
  personWallets: PortalPersonCryptoWallet[]
  externalWallets: VerifiedExternalWallet[]
  solanaStatus: SolanaWalletStatusPayload | null
}): PortalWalletScope[] {
  if (args.chain === 'solana') {
    if (args.solanaStatus?.status === 'linked') {
      const scope = buildSolanaPrivyScope(args.solanaStatus)
      return scope ? [scope] : []
    }
    return []
  }

  const scopes: PortalWalletScope[] = []

  const privyEvm = args.personWallets.find(
    (wallet) =>
      wallet.provider.trim().toLowerCase() === 'privy' &&
      wallet.chain_type.trim().toLowerCase() === 'evm',
  )
  if (privyEvm) {
    scopes.push(buildPrivyScope(privyEvm, 'evm'))
  }

  for (const external of args.externalWallets) {
    scopes.push(buildExternalScope(external))
  }

  return scopes
}
