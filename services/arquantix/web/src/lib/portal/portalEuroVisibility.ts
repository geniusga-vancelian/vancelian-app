/**
 * Visibilité Euro sur le portail web (compte fiat + stablecoin EURC).
 * Désactivé par défaut — réactivation : NEXT_PUBLIC_PORTAL_EURO_ENABLED=true
 */
export function isPortalEuroFeaturesEnabled(): boolean {
  return process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED?.trim().toLowerCase() === 'true'
}

export function isPortalEuroStablecoinSymbol(symbol: string): boolean {
  const upper = symbol.trim().toUpperCase()
  return upper === 'EURC' || upper === 'EUR'
}

export function filterPortalEuroStablecoinSymbols<T extends string>(
  symbols: readonly T[],
): T[] {
  if (isPortalEuroFeaturesEnabled()) return [...symbols]
  return symbols.filter((symbol) => !isPortalEuroStablecoinSymbol(symbol))
}

export function filterPortalWalletRows<T extends { id: string }>(rows: T[]): T[] {
  if (isPortalEuroFeaturesEnabled()) return rows
  return rows.filter((row) => row.id !== 'euro')
}

/** Libellé court pour les actifs éligibles au swap (étape « from »). */
export function resolvePortalSwapEligibleAssetsLabel(): string {
  if (isPortalEuroFeaturesEnabled()) {
    return 'USDC, EURC, ETH, etc.'
  }
  return 'USDC, ETH, etc.'
}

/** Libellé pour l’étape achat swap (« Pay with … »). */
export function resolvePortalSwapPayWithLabel(chainLabel: string, toAsset: string): string {
  if (isPortalEuroFeaturesEnabled()) {
    return `Pay with USDC, EURC or ETH on ${chainLabel} to buy ${toAsset}.`
  }
  return `Pay with USDC or ETH on ${chainLabel} to buy ${toAsset}.`
}

/** Actifs cités sur la page dépôt EVM (hors Solana). */
export function resolvePortalEvmDepositAssetsLabel(): string {
  if (isPortalEuroFeaturesEnabled()) {
    return 'ETH, USDC, USDT ou EURC'
  }
  return 'ETH, USDC ou USDT'
}
