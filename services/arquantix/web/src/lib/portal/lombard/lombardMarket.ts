import { MarketParams } from '@morpho-org/blue-sdk'
import { MorphoClient } from '@morpho-org/morpho-sdk'
import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import {
  findLombardMarketById,
  findLombardMarketConfig,
  lombardMaxUserLtvWad,
  VANCELIAN_LOMBARD_V1,
} from '@/lib/portal/lombard/lombardConfig'
import { fetchLombardMorphoMarket } from '@/lib/portal/lombard/lombardGraphql'
import type { LombardMarketSummary } from '@/lib/portal/lombard/lombardTypes'
import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'

export class LombardMarketError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'LombardMarketError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

export type ResolvedLombardMarket = {
  config: (typeof VANCELIAN_LOMBARD_V1.markets)[number]
  marketParams: MarketParams
  gql: NonNullable<Awaited<ReturnType<typeof fetchLombardMorphoMarket>>>
  morphoMarket: ReturnType<MorphoClient['marketV1']>
}

function normalizeCollateralSymbol(value: string): string {
  return value.trim()
}

function wadToPercent(wad: bigint): number {
  return Number(wad) / 1e16
}

export async function resolveLombardMarket(args: {
  collateral?: string
  marketId?: string
}): Promise<ResolvedLombardMarket> {
  const config =
    (args.marketId ? findLombardMarketById(args.marketId) : null) ??
    (args.collateral ? findLombardMarketConfig(args.collateral) : null)

  if (!config) {
    throw new LombardMarketError('lombard.market_not_configured', 'Market not supported.')
  }

  const gql = await fetchLombardMorphoMarket({
    marketId: config.marketId,
    chainId: VANCELIAN_LOMBARD_V1.chainId,
  })

  if (!gql) {
    throw new LombardMarketError(
      'lombard.market_not_found',
      'Market unavailable on Morpho. Please try again later.',
      404,
    )
  }

  const gqlCollateral = normalizeCollateralSymbol(gql.collateralAsset.symbol)
  const expectedCollateral = normalizeCollateralSymbol(config.collateral)
  if (gqlCollateral.toLowerCase() !== expectedCollateral.toLowerCase()) {
    throw new LombardMarketError(
      'lombard.market_collateral_mismatch',
      `Configured market collateral (${expectedCollateral}) does not match Morpho market (${gqlCollateral}).`,
      409,
    )
  }

  if (gql.loanAsset.symbol.toUpperCase() !== VANCELIAN_LOMBARD_V1.borrowAsset) {
    throw new LombardMarketError('lombard.market_loan_mismatch', 'Only USDC borrowing is supported in V1.', 409)
  }

  const marketParams = new MarketParams({
    loanToken: gql.loanAsset.address as Address,
    collateralToken: gql.collateralAsset.address as Address,
    oracle: gql.oracle.address as Address,
    irm: gql.irmAddress as Address,
    lltv: BigInt(gql.lltv),
  })

  if (marketParams.id.toLowerCase() !== config.marketId.toLowerCase()) {
    throw new LombardMarketError(
      'lombard.market_id_mismatch',
      'Morpho market parameters do not match the configured market id.',
      409,
    )
  }

  const publicClient = createBasePublicClient({ side: 'server' })
  const morpho = new MorphoClient(publicClient, { supportSignature: false })
  const morphoMarket = morpho.marketV1(marketParams, VANCELIAN_LOMBARD_V1.chainId)

  return { config, marketParams, gql, morphoMarket }
}

export async function buildLombardMarketSummary(
  resolved: ResolvedLombardMarket,
): Promise<LombardMarketSummary> {
  const { config, gql } = resolved
  const lltvPercent = wadToPercent(BigInt(gql.lltv))
  const borrowApyPercent =
    gql.state?.borrowApy != null && Number.isFinite(gql.state.borrowApy) ? gql.state.borrowApy * 100 : null

  return {
    marketId: config.marketId,
    collateral: config.collateral,
    collateralName: config.displayName,
    borrowAsset: 'USDC',
    chain: 'base',
    chainId: VANCELIAN_LOMBARD_V1.chainId,
    borrowApyPercent,
    liquidationLltvPercent: lltvPercent,
    maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
    poweredBy: 'Morpho',
    collateralTokenAddress: gql.collateralAsset.address,
    loanTokenAddress: gql.loanAsset.address,
    collateralDecimals: gql.collateralAsset.decimals,
    loanDecimals: gql.loanAsset.decimals,
  }
}

export async function fetchLombardMarketData(resolved: ResolvedLombardMarket) {
  return resolved.morphoMarket.getMarketData()
}

export async function fetchLombardPositionData(resolved: ResolvedLombardMarket, walletAddress: Address) {
  return resolved.morphoMarket.getPositionData(walletAddress)
}

export function lombardUserMaxLtvWad(): bigint {
  return lombardMaxUserLtvWad()
}

export function assertLombardChainId(chainId?: number): void {
  if ((chainId ?? MORPHO_CHAIN_ID) !== VANCELIAN_LOMBARD_V1.chainId) {
    throw new LombardMarketError('lombard.unsupported_chain', 'Only Base is supported.', 400)
  }
}
