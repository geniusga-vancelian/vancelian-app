import type { PortalChain } from '@/config/portalChains'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'

export function shouldShowLombardWalletDashboardCard(args: {
  lombardEnabled: boolean
  chain: PortalChain
  loading: boolean
}): boolean {
  if (args.loading || !args.lombardEnabled || args.chain !== 'base') return false
  return true
}

export function shouldShowLombardActiveLoanCard(positions: LombardActivePosition[]): boolean {
  return positions.length > 0
}

export function shouldShowLombardEmptyState(args: {
  positions: LombardActivePosition[]
  walletPositions: PortalCryptoPosition[]
}): boolean {
  if (args.positions.length > 0) return false
  return args.walletPositions.some((row) => {
    const collateral = normalizeLombardCollateralSymbol(row.asset)
    if (!collateral) return false
    const balance = row.availableBalance ?? row.balance
    return Number.isFinite(balance) && balance > 0
  })
}

export function shouldShowLombardAssetDetailLoanCard(args: {
  asset: string
  lombardEnabled: boolean
  chain: PortalChain
  position: LombardActivePosition | null
}): boolean {
  if (!args.lombardEnabled || args.chain !== 'base') return false
  if (!normalizeLombardCollateralSymbol(args.asset)) return false
  return args.position != null
}

export function resolveLombardAssetDetailLoanPosition(
  positions: LombardActivePosition[],
  asset: string,
): LombardActivePosition | null {
  const collateral = normalizeLombardCollateralSymbol(asset)
  if (!collateral) return null
  return positions.find((row) => row.collateralSymbol === collateral) ?? null
}
