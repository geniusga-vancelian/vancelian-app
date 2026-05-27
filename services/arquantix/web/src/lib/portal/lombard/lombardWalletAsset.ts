import type { LombardCollateralSymbol } from '@/lib/portal/lombard/lombardConfig'
import { findLombardMarketConfig } from '@/lib/portal/lombard/lombardConfig'

const WALLET_ASSET_ALIASES: Record<string, LombardCollateralSymbol> = {
  CBBTC: 'cbBTC',
  CBTC: 'cbBTC',
  cbbtc: 'cbBTC',
  CBETH: 'cbETH',
  cbeth: 'cbETH',
}

export function normalizeLombardCollateralSymbol(asset: string): LombardCollateralSymbol | null {
  const trimmed = asset.trim()
  if (!trimmed) return null

  const direct = findLombardMarketConfig(trimmed)
  if (direct) return direct.collateral

  const alias = WALLET_ASSET_ALIASES[trimmed] ?? WALLET_ASSET_ALIASES[trimmed.toUpperCase()]
  return alias ?? null
}

export function isLombardWalletCollateralAsset(asset: string): boolean {
  return normalizeLombardCollateralSymbol(asset) != null
}

export function lombardGuaranteeTagline(collateral: LombardCollateralSymbol): string {
  if (collateral === 'cbBTC') return 'Use your Bitcoin as a guarantee'
  return 'Use your Ethereum as a guarantee'
}

export function lombardDepositCtaLabel(collateral: LombardCollateralSymbol): string {
  return `Deposit ${collateral} to borrow USDC`
}
