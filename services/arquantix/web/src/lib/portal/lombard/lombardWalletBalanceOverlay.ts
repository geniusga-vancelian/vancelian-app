import type {
  PortalCryptoPosition,
  PortalCryptoPositionsSummary,
  PortalCryptoWalletDetail,
  PortalLombardWalletPositionOverlay,
} from '@/lib/portal/cryptoWalletTypes'
import {
  formatDetailVolumeAmount,
  formatCryptoVolume,
} from '@/lib/portal/cryptoWalletFormat'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { normalizeLombardCollateralSymbol } from '@/lib/portal/lombard/lombardWalletAsset'

function parseHumanAmount(value: string): number {
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}

function recalcEstimatedValues(
  position: PortalCryptoPosition,
  balance: number,
): Pick<PortalCryptoPosition, 'estimatedValueEur' | 'estimatedValueUsd'> {
  if (position.asset.toUpperCase() === 'USDC') {
    const estimatedUsd = balance
    return {
      estimatedValueUsd: estimatedUsd,
      estimatedValueEur: balance * 0.92,
    }
  }
  return {
    estimatedValueEur:
      position.priceEur != null ? balance * position.priceEur : position.estimatedValueEur,
    estimatedValueUsd:
      position.priceUsd != null ? balance * position.priceUsd : position.estimatedValueUsd,
  }
}

function findLombardLoanForAsset(
  positions: LombardActivePosition[],
  asset: string,
): LombardActivePosition | null {
  const collateral = normalizeLombardCollateralSymbol(asset)
  if (!collateral) return null
  return positions.find((row) => row.collateralSymbol === collateral) ?? null
}

function totalBorrowedUsdc(positions: LombardActivePosition[]): number {
  return positions.reduce((sum, row) => sum + parseHumanAmount(row.borrowAmount), 0)
}

function buildUsdcOverlayPosition(args: {
  balance: number
  borrowedUsdc: number
  simulatePrivyCredit: boolean
}): PortalCryptoPosition {
  const estimatedUsd = args.balance
  const estimatedEur = args.balance * 0.92
  return {
    asset: 'USDC',
    name: 'USD Coin',
    balance: args.balance,
    availableBalance: args.balance,
    priceUsd: 1,
    estimatedValueUsd: estimatedUsd,
    priceEur: 0.92,
    estimatedValueEur: estimatedEur,
    iconKey: 'usdc',
    providerSymbol: 'USDCUSDT',
    portfolioScope: 'privy',
    privyBalance: args.simulatePrivyCredit ? 0 : args.balance,
    platformBalance: 0,
    chainType: 'evm',
    chainId: VANCELIAN_LOMBARD_V1.chainId,
    lombard: {
      lockedCollateralAmount: 0,
      lockedCollateralSymbol: 'USDC',
      borrowedUsdcAmount: args.borrowedUsdc,
      simulatePrivyCredit: args.simulatePrivyCredit,
    },
  }
}

/** Applique garantie locked + USDC empruntés sur le hub wallet (live + mock). */
export function applyLombardWalletBalanceOverlay(args: {
  summary: PortalCryptoPositionsSummary
  lombardPositions: LombardActivePosition[]
  simulatePrivyBalances: boolean
}): PortalCryptoPositionsSummary {
  if (args.lombardPositions.length === 0) return args.summary

  const borrowedUsdcTotal = totalBorrowedUsdc(args.lombardPositions)
  const positions = args.summary.positions.map((position) => {
    const loan = findLombardLoanForAsset(args.lombardPositions, position.asset)
    if (!loan) return position

    const locked = parseHumanAmount(loan.collateralAmount)
    if (locked <= 0) return position

    const walletFree = position.privyBalance ?? position.balance
    const available = args.simulatePrivyBalances
      ? Math.max(0, walletFree - locked)
      : walletFree
    const totalExposure = args.simulatePrivyBalances ? walletFree : walletFree + locked

    const overlay: PortalLombardWalletPositionOverlay = {
      lockedCollateralAmount: locked,
      lockedCollateralSymbol: loan.collateralSymbol,
      borrowedUsdcAmount: parseHumanAmount(loan.borrowAmount),
      simulatePrivyCredit: args.simulatePrivyBalances,
    }

    return {
      ...position,
      balance: totalExposure,
      availableBalance: available,
      ...recalcEstimatedValues(position, totalExposure),
      lombard: overlay,
    }
  })

  if (borrowedUsdcTotal > 0) {
    const usdcIndex = positions.findIndex((row) => row.asset.toUpperCase() === 'USDC')
    const privyUsdc =
      usdcIndex >= 0 ? positions[usdcIndex].privyBalance ?? positions[usdcIndex].balance : 0
    const displayUsdc = args.simulatePrivyBalances ? privyUsdc + borrowedUsdcTotal : privyUsdc
    const lombardUsdcMeta: PortalLombardWalletPositionOverlay = {
      lockedCollateralAmount: 0,
      lockedCollateralSymbol: 'USDC',
      borrowedUsdcAmount: borrowedUsdcTotal,
      simulatePrivyCredit: args.simulatePrivyBalances,
    }

    if (usdcIndex >= 0) {
      const existing = positions[usdcIndex]
      const existingChainId = existing.chainId ?? null
      const existingOnBase =
        existingChainId == null || existingChainId === VANCELIAN_LOMBARD_V1.chainId

      if (!existingOnBase && args.simulatePrivyBalances) {
        positions.push(
          buildUsdcOverlayPosition({
            balance: borrowedUsdcTotal,
            borrowedUsdc: borrowedUsdcTotal,
            simulatePrivyCredit: true,
          }),
        )
      } else {
        positions[usdcIndex] = {
          ...existing,
          balance: displayUsdc,
          availableBalance: displayUsdc,
          chainType: 'evm',
          chainId: VANCELIAN_LOMBARD_V1.chainId,
          ...recalcEstimatedValues(existing, displayUsdc),
          lombard: lombardUsdcMeta,
        }
      }
    } else if (displayUsdc > 0) {
      positions.push(
        buildUsdcOverlayPosition({
          balance: displayUsdc,
          borrowedUsdc: borrowedUsdcTotal,
          simulatePrivyCredit: args.simulatePrivyBalances,
        }),
      )
    }
  }

  positions.sort(
    (a, b) =>
      (b.estimatedValueEur ?? b.estimatedValueUsd ?? 0) -
      (a.estimatedValueEur ?? a.estimatedValueUsd ?? 0),
  )

  const totalValueEur = positions.reduce((sum, row) => sum + (row.estimatedValueEur ?? 0), 0)
  const totalValueUsd = positions.reduce((sum, row) => sum + (row.estimatedValueUsd ?? 0), 0)

  return {
    ...args.summary,
    positions,
    positionsCount: positions.length,
    totalValueEur,
    totalValueUsd: totalValueUsd > 0 ? totalValueUsd : undefined,
  }
}

export function buildLombardWalletDetailFields(
  position: PortalCryptoPosition,
): Pick<
  PortalCryptoWalletDetail,
  'lombard' | 'availableVolume' | 'lockedVolume' | 'volume' | 'totalValueEur' | 'totalValueUsd'
> {
  const totalValueEur =
    position.estimatedValueEur ??
    (position.priceEur != null ? position.balance * position.priceEur : 0)
  const totalValueUsd =
    position.estimatedValueUsd ??
    (position.priceUsd != null ? position.balance * position.priceUsd : undefined)

  return {
    volume: formatDetailVolumeAmount(position.balance, position.asset),
    totalValueEur,
    totalValueUsd,
    availableVolume: formatDetailVolumeAmount(position.availableBalance, position.asset),
    lockedVolume:
      position.lombard && position.lombard.lockedCollateralAmount > 0
        ? formatDetailVolumeAmount(position.lombard.lockedCollateralAmount, position.asset)
        : undefined,
    lombard: position.lombard,
  }
}

export function formatLombardPositionSubtitle(position: PortalCryptoPosition): string | null {
  const lombard = position.lombard
  if (!lombard) return null

  if (lombard.lockedCollateralAmount > 0) {
    const availableStr = formatCryptoVolume(position.availableBalance, position.asset)
    const lockedStr = formatCryptoVolume(
      lombard.lockedCollateralAmount,
      lombard.lockedCollateralSymbol,
    )
    return `${availableStr} available · ${lockedStr} locked`
  }

  if (position.asset.toUpperCase() === 'USDC' && lombard.borrowedUsdcAmount > 0) {
    const volumeStr = formatCryptoVolume(position.balance, position.asset)
    if (lombard.simulatePrivyCredit) {
      return `${volumeStr} · incl. ${lombard.borrowedUsdcAmount.toFixed(0)} USDC Lombard`
    }
    return `${volumeStr} · Lombard borrow`
  }

  return null
}
