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

/** True si le solde on-chain a été lu pour ce wallet (spendable fiable). */
export function isOnChainBalanceVerified(position: {
  onChainBalance?: number
} | null | undefined): boolean {
  if (!position) return false
  return position.onChainBalance != null && Number.isFinite(position.onChainBalance)
}

/** Montant max signable Privy = min(ledger, on-chain) si on-chain connu. */
export function resolvePrivySwapSpendableCap(position: {
  availableBalance?: number
  balance?: number
  onChainBalance?: number
}): { spendable: number; onChainVerified: boolean; onChainBalance?: number } {
  const ledger = position.availableBalance ?? position.balance ?? 0
  const onChainVerified = isOnChainBalanceVerified(position)
  const onChainBalance = onChainVerified ? position.onChainBalance : undefined
  return {
    spendable: resolveSpendableSwapBalance(position),
    onChainVerified,
    onChainBalance,
  }
}

export function isSwapBlockedPendingOnChainVerification(
  usesPrivyBalance: boolean,
  onChainVerified: boolean,
  balancePending: boolean,
): boolean {
  return usesPrivyBalance && !onChainVerified && !balancePending
}

export function isSwapAmountOverOnChainBalance(
  parsed: number,
  onChainBalance: number | undefined,
  onChainVerified: boolean,
): boolean {
  if (!onChainVerified || onChainBalance == null || !Number.isFinite(onChainBalance)) return false
  if (!Number.isFinite(parsed) || parsed <= 0) return false
  return parsed > onChainBalance
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
