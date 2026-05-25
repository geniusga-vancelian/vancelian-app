import type { ExecutionWalletMode } from '@/lib/wallet/useExecutionWallet'

export type SwapSigningWalletQuoteParams = {
  signing_wallet_mode: ExecutionWalletMode
  signing_wallet_address?: string
}

/** Paramètres quote LI.FI alignés sur le wallet d'exécution sélectionné. */
export function buildSwapSigningWalletQuoteParams(args: {
  mode: ExecutionWalletMode
  privyEmbeddedAddress: string | null
  externalWalletAddress: string | null
}): SwapSigningWalletQuoteParams {
  if (args.mode === 'external_evm') {
    const address = args.externalWalletAddress?.trim()
    if (!address) {
      throw new Error(
        'Aucun wallet externe vérifié. Connectez MetaMask depuis Mon wallet et signez le message de vérification.',
      )
    }
    return {
      signing_wallet_mode: 'external_evm',
      signing_wallet_address: address,
    }
  }

  if (!args.privyEmbeddedAddress?.trim()) {
    throw new Error('Wallet Vancelian (Privy) requis — créez votre wallet crypto depuis Mon wallet.')
  }

  return {
    signing_wallet_mode: 'privy_embedded',
  }
}

export function formatSwapSigningWalletShort(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}
