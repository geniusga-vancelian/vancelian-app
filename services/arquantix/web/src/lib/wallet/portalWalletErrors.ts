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

export function formatPortalWalletError(error: unknown): string {
  if (isPortalWalletUserRejectedError(error)) {
    return 'Transaction refusée dans MetaMask.'
  }

  if (isPortalWalletRequestExpiredError(error)) {
    return 'MetaMask n’a pas reçu votre signature à temps. Ouvrez l’extension, basculez sur Ethereum mainnet si demandé, signez l’approbation USDT puis relancez depuis l’étape montant.'
  }

  const message = errorMessage(error)
  const lower = message.toLowerCase()

  if (lower.includes('chain') && lower.includes('match')) {
    return 'Le réseau MetaMask ne correspond pas au swap. Sélectionnez Ethereum mainnet dans MetaMask puis réessayez.'
  }

  return message
}
