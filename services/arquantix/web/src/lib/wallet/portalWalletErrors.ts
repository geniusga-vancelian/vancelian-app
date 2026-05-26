import { portalEvmChainLabel } from '@/lib/wallet/portalEvmChain'

export type PortalWalletErrorContext = {
  walletMode?: 'privy_embedded' | 'external_evm'
  chainId?: number
  phase?: 'approve' | 'swap'
  assetSymbol?: string
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  if (error && typeof error === 'object' && 'message' in error) {
    const message = (error as { message?: unknown }).message
    if (typeof message === 'string') return message
  }
  return 'Transaction wallet impossible'
}

function errorDetails(error: unknown): string {
  if (error && typeof error === 'object' && 'details' in error) {
    const details = (error as { details?: unknown }).details
    if (typeof details === 'string') return details
  }
  return ''
}

function chainLabel(context?: PortalWalletErrorContext): string {
  if (context?.chainId !== undefined) {
    return portalEvmChainLabel(context.chainId)
  }
  return 'le réseau attendu'
}

function assetLabel(context?: PortalWalletErrorContext): string {
  return context?.assetSymbol?.trim() || 'jeton'
}

function isExternalWallet(context?: PortalWalletErrorContext): boolean {
  return context?.walletMode === 'external_evm'
}

export function isPortalWalletRequestExpiredError(error: unknown): boolean {
  const haystack = `${errorMessage(error)} ${errorDetails(error)}`.toLowerCase()
  return haystack.includes('request expired')
}

export function isPortalWalletUserRejectedError(error: unknown): boolean {
  const haystack = `${errorMessage(error)} ${errorDetails(error)}`.toLowerCase()
  return (
    haystack.includes('user rejected') ||
    haystack.includes('user denied') ||
    haystack.includes('rejected the request')
  )
}

function formatExecutionRevertedError(context?: PortalWalletErrorContext): string {
  const chain = chainLabel(context)
  const asset = assetLabel(context)

  if (context?.phase === 'approve') {
    if (isExternalWallet(context)) {
      return `Approbation ${asset} refusée sur ${chain}. Vérifiez MetaMask (réseau ${chain}) puis réessayez.`
    }
    return `Approbation ${asset} impossible sur ${chain}. Vérifiez le gas sponsorship Privy sur ce réseau (dashboard Privy → Gas sponsorship) puis réessayez.`
  }

  if (context?.phase === 'swap') {
    if (isExternalWallet(context)) {
      return `Swap LI.FI refusé sur ${chain}. Vérifiez que l’approbation ${asset} a bien été signée dans MetaMask, puis refaites une estimation.`
    }
    return `Swap LI.FI refusé sur ${chain}. L’approbation ${asset} vers le routeur LI.FI n’a probablement pas abouti — refaites une estimation puis réessayez.`
  }

  if (isExternalWallet(context)) {
    return `Transaction refusée sur ${chain}. Vérifiez MetaMask puis réessayez.`
  }

  return `Transaction refusée sur ${chain}. Vérifiez le gas sponsorship Privy sur ce réseau puis réessayez.`
}

export function formatPortalWalletError(
  error: unknown,
  context?: PortalWalletErrorContext,
): string {
  if (isPortalWalletUserRejectedError(error)) {
    if (isExternalWallet(context)) {
      return 'Transaction refusée dans MetaMask.'
    }
    return 'Transaction refusée dans le wallet Vancelian.'
  }

  if (isPortalWalletRequestExpiredError(error)) {
    const chain = chainLabel(context)
    const asset = assetLabel(context)
    if (isExternalWallet(context)) {
      return `MetaMask n’a pas reçu votre signature à temps. Basculez sur ${chain}, signez l’approbation ${asset} puis relancez depuis l’étape montant.`
    }
    return `Le wallet Vancelian n’a pas pu finaliser la transaction à temps sur ${chain}. Réessayez depuis l’étape montant.`
  }

  const message = errorMessage(error)
  const lower = message.toLowerCase()

  if (lower.includes('chain') && lower.includes('match')) {
    if (isExternalWallet(context)) {
      return `Le réseau MetaMask ne correspond pas au swap. Sélectionnez ${chainLabel(context)} puis réessayez.`
    }
    return `Le wallet Vancelian n’est pas sur ${chainLabel(context)}. Changez de réseau dans la navbar puis réessayez.`
  }

  if (lower.includes('execution reverted') || lower.includes('transfer_from_failed')) {
    return formatExecutionRevertedError(context)
  }

  return message
}
