/** Tolérances réconciliation Ledgity ledger ↔ on-chain. */

export function getLedgityReconciliationToleranceRaw(): bigint {
  const raw = process.env.LEDGITY_RECONCILIATION_TOLERANCE_RAW?.trim()
  if (!raw) return BigInt(10)
  try {
    const value = BigInt(raw)
    return value >= BigInt(0) ? value : BigInt(10)
  } catch {
    return BigInt(10)
  }
}

/** Seuil alerte mismatch significatif — défaut 1 USDC/EURC (1_000_000 raw). */
export function getLedgityAlertMismatchToleranceRaw(): bigint {
  const raw = process.env.LEDGITY_ALERT_MISMATCH_TOLERANCE_RAW?.trim()
  if (!raw) return BigInt(1_000_000)
  try {
    return BigInt(raw)
  } catch {
    return BigInt(1_000_000)
  }
}

export const LEDGITY_DEFAULT_PENDING_ALERT_MINUTES = 15

export function getLedgityPendingAlertMinutes(): number {
  const raw = Number(process.env.LEDGITY_PENDING_ALERT_MINUTES ?? LEDGITY_DEFAULT_PENDING_ALERT_MINUTES)
  return Number.isFinite(raw) && raw > 0 ? raw : LEDGITY_DEFAULT_PENDING_ALERT_MINUTES
}

/** Seuil liquidité faible — défaut 10 % du TVL on-chain (raw units). */
export function getLedgityLiquidityWarningRatioBps(): number {
  const raw = Number(process.env.LEDGITY_LIQUIDITY_WARNING_RATIO_BPS ?? '1000')
  return Number.isFinite(raw) && raw > 0 ? Math.round(raw) : 1000
}
