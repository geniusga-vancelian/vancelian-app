/** Garde-fou montant swap wallet Privy — solde affiché / ledger. */
export function isSwapAmountOverPrivyBalance(parsed: number, sourceBalance: number): boolean {
  if (!Number.isFinite(parsed) || parsed <= 0) return false
  if (!Number.isFinite(sourceBalance) || sourceBalance <= 0) return true
  return parsed > sourceBalance
}
