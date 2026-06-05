/** Garde-fou montant swap wallet Privy — solde affiché / ledger. */
export function isSwapAmountOverPrivyBalance(parsed: number, sourceBalance: number): boolean {
  if (!Number.isFinite(parsed) || parsed <= 0) return false
  if (!Number.isFinite(sourceBalance) || sourceBalance <= 0) return true
  return parsed > sourceBalance
}

/** Solde spendable swap = min(ledger, on-chain) quand les deux sont connus. */
export function resolveSpendableSwapBalance(position: {
  availableBalance?: number
  balance?: number
  onChainBalance?: number
}): number {
  const ledger = position.availableBalance ?? position.balance ?? 0
  const onChain = position.onChainBalance
  if (onChain == null || !Number.isFinite(onChain)) return ledger
  if (ledger <= 0) return onChain
  return Math.min(ledger, onChain)
}

/** Solde source swap à jour depuis les positions wallet (évite un state figé à 0). */
export function resolveLiveSwapSourceBalance(
  fromAsset: string,
  positions: Array<{ asset: string; availableBalance?: number; balance?: number; onChainBalance?: number }>,
  fallbackBalance = 0,
): number {
  const needle = fromAsset.trim().toUpperCase()
  if (!needle) return fallbackBalance
  const position = positions.find((row) => row.asset.toUpperCase() === needle)
  if (!position) return fallbackBalance
  return resolveSpendableSwapBalance(position)
}
