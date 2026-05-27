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
