import { bundleTargetWeightToPct } from '@/lib/portal/bundleProductFormat'

export { bundleTargetWeightToPct } from '@/lib/portal/bundleProductFormat'

/** Symboles bundle Base — aligné backend ``display_bundle_asset`` / portail Lombard. */
const BUNDLE_ASSET_DISPLAY: Record<string, string> = {
  CBBTC: 'cbBTC',
  CBETH: 'cbETH',
}

const PE_TO_BUNDLE_LIFI: Record<string, string> = {
  BTC: 'CBBTC',
  ETH: 'CBETH',
}

/** Symbole PE / exchange → symbole canonique bundle Li.FI (CBBTC, CBETH, …). */
export function normalizeBundleAssetSymbol(raw: string): string {
  const upper = raw.trim().toUpperCase()
  if (!upper) return upper
  return PE_TO_BUNDLE_LIFI[upper] ?? upper
}

/** Libellé portail (cbBTC, cbETH) pour une ligne d'allocation bundle. */
export function displayBundleAssetSymbol(raw: string): string {
  const canonical = normalizeBundleAssetSymbol(raw)
  return BUNDLE_ASSET_DISPLAY[canonical] ?? canonical
}

/** Poids décimal PE (0.5) → « 50 % ». */
export function formatBundleTargetWeight(weight: string | number | null | undefined): string {
  const pct = bundleTargetWeightToPct(weight)
  if (pct <= 0) return '—'
  const rounded = Math.round(pct * 10) / 10
  return `${rounded % 1 === 0 ? rounded.toFixed(0) : rounded.toFixed(1)} %`
}

/** Montant USDC (ou entry asset) avec décimales raisonnables. */
export function formatBundleUsdcAmount(raw: string | number | null | undefined): string {
  const n = typeof raw === 'number' ? raw : Number(raw)
  if (!Number.isFinite(n)) return '—'
  if (n === 0) return '0'
  if (n >= 1) return n.toFixed(2)
  return n.toFixed(4)
}
