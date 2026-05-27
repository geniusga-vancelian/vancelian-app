import type { ConnectedWallet, User } from '@privy-io/react-auth'
import { getEmbeddedConnectedWallet } from '@privy-io/react-auth'

import { fetchPortalPersonCryptoWallets, findEvmPersonWallet } from '@/lib/portal/privyWalletClient'

export type PortalSwapSigningWallet = {
  address: `0x${string}`
  switchChain?: (chainId: number) => Promise<void>
}

function pickConnectedWallet(wallets: ConnectedWallet[]): ConnectedWallet | null {
  return (
    getEmbeddedConnectedWallet(wallets) ??
    wallets.find((w) => w.walletClientType === 'privy' || w.walletClientType === 'privy-v2') ??
    wallets.find((w) => w.type === 'ethereum' && w.address) ??
    wallets[0] ??
    null
  )
}

function findEmbeddedEvmAddressFromUser(user: User | null | undefined): string | null {
  const accounts = user?.linkedAccounts
  if (!accounts?.length) return null
  for (const account of accounts) {
    if (account.type !== 'wallet') continue
    const wallet = account as { address?: string; chainType?: string; walletClientType?: string; connectorType?: string }
    if (wallet.chainType !== 'ethereum' || !wallet.address) continue
    const client = (wallet.walletClientType || '').toLowerCase()
    const connector = (wallet.connectorType || '').toLowerCase()
    if (client === 'privy' || client === 'privy-v2' || connector === 'embedded') {
      return wallet.address
    }
  }
  return null
}

function toSigningWallet(wallet: ConnectedWallet): PortalSwapSigningWallet {
  return {
    address: wallet.address as `0x${string}`,
    switchChain: (chainId) => wallet.switchChain(chainId),
  }
}

function privySessionRequiredError(hasBackendWallet: boolean): Error {
  if (hasBackendWallet) {
    return new Error(
      'Session wallet Privy requise pour signer. Ouvrez Mon wallet crypto et activez votre wallet embedded (code e-mail), puis réessayez.',
    )
  }
  return new Error(
    'Wallet Privy embedded requis — créez votre wallet crypto depuis Mon wallet, puis relancez le swap.',
  )
}

/**
 * Résout le wallet de signature pour un swap LI.FI.
 * Le portail Vancelian peut avoir un wallet backend sans session SDK Privy active.
 */
export async function resolvePortalSwapSigningWallet(args: {
  ready: boolean
  authenticated: boolean
  user: User | null | undefined
  wallets: ConnectedWallet[]
  createWallet: () => Promise<{ address: string }>
  /** Adresse déjà sélectionnée côté portail (Mon wallet / BFF). */
  expectedAddress?: string | null
}): Promise<PortalSwapSigningWallet> {
  const expected = args.expectedAddress?.trim().toLowerCase() || null

  const connected = pickConnectedWallet(args.wallets)
  if (connected?.address) {
    if (!expected || connected.address.toLowerCase() === expected) {
      return toSigningWallet(connected)
    }
  }

  const linkedAddress = findEmbeddedEvmAddressFromUser(args.user)
  if (linkedAddress) {
    if (!expected || linkedAddress.toLowerCase() === expected) {
      return { address: linkedAddress as `0x${string}` }
    }
  }

  if (expected) {
    try {
      const backendWallet = findEvmPersonWallet(await fetchPortalPersonCryptoWallets())
      if (backendWallet?.address?.toLowerCase() === expected) {
        return { address: backendWallet.address as `0x${string}` }
      }
    } catch {
      /* ignore — on continue avec le flux Privy */
    }
  }

  if (!args.ready) {
    throw new Error('Initialisation Privy en cours. Réessayez dans un instant.')
  }

  if (!args.authenticated) {
    let hasBackendWallet = false
    try {
      hasBackendWallet = Boolean(findEvmPersonWallet(await fetchPortalPersonCryptoWallets()))
    } catch {
      /* ignore */
    }
    throw privySessionRequiredError(hasBackendWallet)
  }

  try {
    const created = await args.createWallet()
    if (created.address) {
      const refreshed = pickConnectedWallet(args.wallets)
      if (refreshed?.address) {
        return toSigningWallet(refreshed)
      }
      return { address: created.address as `0x${string}` }
    }
  } catch {
    const refreshed = pickConnectedWallet(args.wallets)
    if (refreshed?.address) {
      return toSigningWallet(refreshed)
    }
    const recoveredAddress = findEmbeddedEvmAddressFromUser(args.user)
    if (recoveredAddress) {
      return { address: recoveredAddress as `0x${string}` }
    }
  }

  throw privySessionRequiredError(
    Boolean(
      expected ||
        findEmbeddedEvmAddressFromUser(args.user) ||
        pickConnectedWallet(args.wallets),
    ),
  )
}
