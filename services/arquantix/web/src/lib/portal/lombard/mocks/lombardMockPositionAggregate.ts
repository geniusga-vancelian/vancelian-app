import type { LombardCollateralSymbol } from '@/lib/portal/lombard/lombardConfig'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'

export type LombardMockOpenLoanLedgerSlice = {
  marketId: string
  market: (typeof VANCELIAN_LOMBARD_V1.markets)[number]
  borrowRaw: bigint
  collateralRaw: bigint
}

function findMarketConfig(collateral: string) {
  return (
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral === collateral) ??
    VANCELIAN_LOMBARD_V1.markets.find(
      (row) => row.collateral.toLowerCase() === collateral.trim().toLowerCase(),
    ) ??
    null
  )
}

/** Agrège plusieurs open_loan mock sur le même marché Morpho (ex. 3 draws cbBTC/USDC). */
export function aggregateMockOpenLoansByMarket(
  rows: Array<{
    lombardOperation?: string | null
    collateral?: string | null
    borrowRaw: bigint
    collateralRaw: bigint
  }>,
): LombardMockOpenLoanLedgerSlice[] {
  const aggregated = new Map<string, LombardMockOpenLoanLedgerSlice>()

  for (const row of rows) {
    if (row.lombardOperation !== 'open_loan') continue
    const collateral = row.collateral?.trim()
    const market = collateral ? findMarketConfig(collateral) : null
    if (!market) continue
    if (row.borrowRaw <= BigInt(0) && row.collateralRaw <= BigInt(0)) continue

    const current = aggregated.get(market.marketId)
    if (current) {
      current.borrowRaw += row.borrowRaw
      current.collateralRaw += row.collateralRaw
    } else {
      aggregated.set(market.marketId, {
        marketId: market.marketId,
        market,
        borrowRaw: row.borrowRaw,
        collateralRaw: row.collateralRaw,
      })
    }
  }

  return [...aggregated.values()].sort((a, b) =>
    a.market.collateral.localeCompare(b.market.collateral),
  )
}

export function computeMockAggregateLtvWad(args: {
  collateral: LombardCollateralSymbol
  borrowRaw: bigint
  collateralRaw: bigint
  loanDecimals: number
  collateralDecimals: number
  collateralUsdPrice: number
}): bigint {
  if (args.borrowRaw <= BigInt(0) || args.collateralRaw <= BigInt(0)) {
    return BigInt(50 * 1e16)
  }
  const borrowUsd = Number(args.borrowRaw) / 10 ** args.loanDecimals
  const collateralUsd =
    (Number(args.collateralRaw) / 10 ** args.collateralDecimals) * args.collateralUsdPrice
  if (!Number.isFinite(collateralUsd) || collateralUsd <= 0) {
    return BigInt(50 * 1e16)
  }
  const ltv = Math.min(1, borrowUsd / collateralUsd)
  return BigInt(Math.round(ltv * 1e18))
}
