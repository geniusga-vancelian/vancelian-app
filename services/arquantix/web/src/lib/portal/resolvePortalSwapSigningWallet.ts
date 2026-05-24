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
}): Promise<PortalSwapSigningWallet> {
  const connected = pickConnectedWallet(args.wallets)
  if (connected?.address) {
    return toSigningWallet(connected)
  }

  if (!args.ready) {
    throw new Error('Initialisation Privy en cours. Réessayez dans un instant.')
  }

  const linkedAddress = findEmbeddedEvmAddressFromUser(args.user)
  if (linkedAddress) {
    return { address: linkedAddress as `0x${string}` }
  }

  let hasBackendWallet = false
  try {
    hasBackendWallet = Boolean(findEvmPersonWallet(await fetchPortalPersonCryptoWallets()))
  } catch {
    /* ignore — on continue avec le flux Privy */
  }

  if (!args.authenticated) {
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

  throw privySessionRequiredError(hasBackendWallet)
}
