import type { PortalPersonCryptoWallet } from '@/lib/portal/privyWalletClient'
import type { PortalWalletScope } from '@/lib/portal/portalWalletScopeTypes'
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

function findPrivyEvmWallet(
  personWallets: PortalPersonCryptoWallet[],
): PortalPersonCryptoWallet | undefined {
  return personWallets.find(
    (wallet) =>
      wallet.provider.trim().toLowerCase() === 'privy' &&
      wallet.chain_type.trim().toLowerCase() === 'evm',
  )
}

/** Wallet crypto intégré Vancelian (scope par défaut, hors sélecteur navbar). */
export function buildEmbeddedVancelianWalletScope(
  personWallets: PortalPersonCryptoWallet[],
): PortalWalletScope | null {
  const privyEvm = findPrivyEvmWallet(personWallets)
  if (!privyEvm) return null

  return {
    id: `privy:${privyEvm.id}`,
    kind: 'privy_embedded',
    label: 'Wallet crypto',
    shortLabel: 'Crypto',
    address: privyEvm.address,
    personWalletId: privyEvm.id,
    chainType: 'evm',
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

/** Wallets externes affichés dans le sélecteur navbar (pas le wallet intégré). */
export function buildSwitchablePortalWalletScopes(args: {
  externalWallets: VerifiedExternalWallet[]
}): PortalWalletScope[] {
  return args.externalWallets.map(buildExternalScope)
}

/** @deprecated Préférer `buildEmbeddedVancelianWalletScope` + `buildSwitchablePortalWalletScopes`. */
export function buildPortalWalletScopes(args: {
  personWallets: PortalPersonCryptoWallet[]
  externalWallets: VerifiedExternalWallet[]
}): PortalWalletScope[] {
  const scopes: PortalWalletScope[] = []
  const embedded = buildEmbeddedVancelianWalletScope(args.personWallets)
  if (embedded) scopes.push(embedded)
  scopes.push(...buildSwitchablePortalWalletScopes(args))
  return scopes
}
