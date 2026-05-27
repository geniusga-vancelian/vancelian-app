import type { AccrualPosition } from '@morpho-org/blue-sdk'
import type { Address } from 'viem'

import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { lombardSafetyDetails } from '@/lib/portal/lombard/lombardHealth'
import {
  formatLombardApyPercent,
  formatLombardTokenAmount,
  lltvWadToPercent,
  rawToLombardHumanAmount,
} from '@/lib/portal/lombard/lombardFormat'
import type { ResolvedLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import type { LombardActivePosition, LombardPositionsPayload } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  findLombardPositionByCollateral,
  findLombardPositionByMarketId,
} from '@/lib/portal/lombard/lombardPositionLookup'

function wadRatioToPercent(wad: bigint | null | undefined): number | null {
  if (wad == null) return null
  const value = Number(wad)
  if (!Number.isFinite(value)) return null
  return Math.round((value / 1e16) * 100) / 100
}

export function isLombardOnchainPositionActive(args: {
  collateralRaw: bigint
  borrowRaw: bigint
}): boolean {
  return args.collateralRaw > BigInt(0) || args.borrowRaw > BigInt(0)
}

export function formatLombardLiquidationPrice(args: {
  liquidationPrice: bigint | null
  collateralDecimals: number
  loanDecimals: number
}): string | null {
  if (args.liquidationPrice == null || args.liquidationPrice <= BigInt(0)) return null

  const oracleScale = BigInt(10) ** BigInt(36 + args.loanDecimals - args.collateralDecimals)
  if (oracleScale <= BigInt(0)) return null

  const priceUsd = Number(args.liquidationPrice) / Number(oracleScale)
  if (!Number.isFinite(priceUsd) || priceUsd <= 0) return null

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(priceUsd)
}

export function buildLombardActivePositionRow(args: {
  marketConfig: (typeof VANCELIAN_LOMBARD_V1.markets)[number]
  gql: ResolvedLombardMarket['gql']
  collateralAmountRaw: bigint
  borrowAmountRaw: bigint
  currentLtvWad: bigint | null | undefined
  liquidationPriceRaw: bigint | null
}): LombardActivePosition | null {
  if (
    !isLombardOnchainPositionActive({
      collateralRaw: args.collateralAmountRaw,
      borrowRaw: args.borrowAmountRaw,
    })
  ) {
    return null
  }

  const loanDecimals = args.gql.loanAsset.decimals
  const collateralDecimals = args.gql.collateralAsset.decimals
  const currentLtvPercent = wadRatioToPercent(args.currentLtvWad ?? undefined)
  const ltvRatio = currentLtvPercent != null ? currentLtvPercent / 100 : 0
  const safety = lombardSafetyDetails(ltvRatio)

  const borrowApyPercent =
    args.gql.state?.borrowApy != null && Number.isFinite(args.gql.state.borrowApy)
      ? args.gql.state.borrowApy * 100
      : null

  const collateralValueRaw =
    args.currentLtvWad != null &&
    args.currentLtvWad > BigInt(0) &&
    args.borrowAmountRaw > BigInt(0)
      ? (args.borrowAmountRaw * (BigInt(10) ** BigInt(18))) / args.currentLtvWad
      : null

  return {
    marketId: args.marketConfig.marketId,
    collateralSymbol: args.marketConfig.collateral,
    collateralDisplayName: args.marketConfig.displayName,
    collateralAmount: formatLombardTokenAmount(args.collateralAmountRaw, collateralDecimals),
    collateralAmountRaw: args.collateralAmountRaw.toString(),
    collateralUsdValue:
      collateralValueRaw != null ? rawToLombardHumanAmount(collateralValueRaw, loanDecimals, 2) : null,
    borrowSymbol: 'USDC',
    borrowAmount: formatLombardTokenAmount(args.borrowAmountRaw, loanDecimals),
    borrowAmountRaw: args.borrowAmountRaw.toString(),
    currentLtvPercent,
    maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
    morphoLltvPercent: lltvWadToPercent(BigInt(args.gql.lltv)),
    healthStatus: safety.level,
    healthLabel: safety.label,
    healthMessage: safety.message,
    borrowApyPercent,
    borrowApyLabel: formatLombardApyPercent(borrowApyPercent),
    liquidationPrice: formatLombardLiquidationPrice({
      liquidationPrice: args.liquidationPriceRaw,
      collateralDecimals,
      loanDecimals,
    }),
    protocolLabel: 'Powered by Morpho',
    chainId: VANCELIAN_LOMBARD_V1.chainId,
  }
}

export function mapLombardAccrualPosition(args: {
  resolved: ResolvedLombardMarket
  position: AccrualPosition
}): LombardActivePosition | null {
  return buildLombardActivePositionRow({
    marketConfig: args.resolved.config,
    gql: args.resolved.gql,
    collateralAmountRaw: args.position.collateral,
    borrowAmountRaw: args.position.borrowAssets,
    currentLtvWad: args.position.ltv ?? undefined,
    liquidationPriceRaw: args.position.liquidationPrice,
  })
}

export async function fetchLombardActivePositionsForWallet(
  walletAddress: Address,
): Promise<LombardActivePosition[]> {
  const { isLombardMockEnabled } = await import('@/lib/portal/lombard/lombardMockConfig')
  if (isLombardMockEnabled()) {
    const { fetchLombardMockActivePositionsForWallet } = await import(
      '@/lib/portal/lombard/mocks/lombardLocalMock'
    )
    return fetchLombardMockActivePositionsForWallet(walletAddress)
  }

  const positions: LombardActivePosition[] = []

  for (const market of VANCELIAN_LOMBARD_V1.markets) {
    const resolved = await resolveLombardMarket({ collateral: market.collateral })
    const positionData = await resolved.morphoMarket.getPositionData(walletAddress)
    const mapped = mapLombardAccrualPosition({ resolved, position: positionData })
    if (mapped) positions.push(mapped)
  }

  return positions.sort((a, b) => a.collateralSymbol.localeCompare(b.collateralSymbol))
}

export function buildLombardPositionsPayload(args: {
  walletAddress: string
  positions: LombardActivePosition[]
  enabled: boolean
}): LombardPositionsPayload {
  return {
    enabled: args.enabled,
    walletAddress: args.walletAddress,
    positions: args.positions,
    hasActiveLoan: args.positions.some((row) =>
      isLombardOnchainPositionActive({
        collateralRaw: BigInt(row.collateralAmountRaw || '0'),
        borrowRaw: BigInt(row.borrowAmountRaw || '0'),
      }),
    ),
    maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
    protocolLabel: 'Powered by Morpho',
  }
}

export { findLombardPositionByCollateral, findLombardPositionByMarketId } from '@/lib/portal/lombard/lombardPositionLookup'
