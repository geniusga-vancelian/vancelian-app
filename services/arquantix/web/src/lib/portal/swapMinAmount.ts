/** Aligné sur `lifi_validation_service.validate_quote_request` (swap.amount_below_min). */

export function parseSwapCatalogMinAmount(minAmount: string | undefined | null): number | null {
  if (minAmount == null || !minAmount.trim()) return null
  const parsed = Number(minAmount.replace(',', '.'))
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

export function isSwapAmountBelowCatalogMin(
  amount: number,
  minAmount: string | undefined | null,
): boolean {
  if (!Number.isFinite(amount) || amount <= 0) return false
  const min = parseSwapCatalogMinAmount(minAmount)
  if (min == null) return false
  return amount < min
}

/** Même libellé que le backend : `Montant minimum : {min} {asset}`. */
export function formatSwapMinAmountError(asset: string, minAmount: string): string {
  return `Montant minimum : ${minAmount.trim()} ${asset}`
}
