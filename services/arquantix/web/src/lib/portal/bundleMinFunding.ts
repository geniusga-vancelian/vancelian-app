/** Minimum investissement bundle — aligné backend ``BUNDLE_MIN_FUNDING_USDC``. */
export const BUNDLE_MIN_FUNDING_USDC = 20

export function minimumBundleFundingAmount(fundingAsset: string): number {
  const upper = fundingAsset.trim().toUpperCase()
  if (upper === 'EUR') return 20
  if (upper === 'CBETH') return 0.01
  return BUNDLE_MIN_FUNDING_USDC
}

export function isBundleFundingBelowMin(amount: number, fundingAsset: string): boolean {
  if (!Number.isFinite(amount) || amount <= 0) return true
  return amount < minimumBundleFundingAmount(fundingAsset)
}

export function formatBundleMinFundingError(fundingAsset: string): string {
  const min = minimumBundleFundingAmount(fundingAsset)
  const label = fundingAsset.trim().toUpperCase() === 'CBETH' ? 'cbETH' : fundingAsset
  return `Montant minimum : ${min} ${label}`
}

export function formatBundleMinFundingHint(fundingAsset: string): string {
  return formatBundleMinFundingError(fundingAsset)
}
