/** Tolérance réconciliation ledger ↔ on-chain (raw units, ex. USDC 6 decimals). */
export function getMorphoReconciliationToleranceRaw(): bigint {
  const raw = process.env.MORPHO_RECONCILIATION_TOLERANCE_RAW?.trim()
  if (!raw) return BigInt(10)
  try {
    const value = BigInt(raw)
    return value >= BigInt(0) ? value : BigInt(10)
  } catch {
    return BigInt(10)
  }
}

/** Seuil alerte mismatch significatif — défaut 1 USDC (1_000_000 raw). */
export function getMorphoAlertMismatchToleranceRaw(): bigint {
  const raw = process.env.MORPHO_ALERT_MISMATCH_TOLERANCE_RAW?.trim()
  if (!raw) return BigInt(1_000_000)
  try {
    return BigInt(raw)
  } catch {
    return BigInt(1_000_000)
  }
}

export const MORPHO_DEFAULT_PENDING_ALERT_MINUTES = 15

export function getMorphoPendingAlertMinutes(): number {
  const raw = Number(process.env.MORPHO_PENDING_ALERT_MINUTES ?? MORPHO_DEFAULT_PENDING_ALERT_MINUTES)
  return Number.isFinite(raw) && raw > 0 ? raw : MORPHO_DEFAULT_PENDING_ALERT_MINUTES
}
