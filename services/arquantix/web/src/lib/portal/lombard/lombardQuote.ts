import { erc20Abi, type Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { assertLombardUserLtvWithinCap, lombardSafetyDetails } from '@/lib/portal/lombard/lombardHealth'
import { LombardMarketError, resolveLombardMarket, type ResolvedLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import type { LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import { lombardMaxUserLtvWad, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  clampLombardTargetLtvPercent,
  lombardTargetLtvPercentToWad,
} from '@/lib/portal/lombard/lombardBorrowLtv'
import {
  computeMaxIncrementalBorrowRawWithFallback,
  computeProjectedPositionLtvRatio,
  findMinimumIncrementalCollateralForBorrow,
  readLombardPositionBorrowSnapshot,
} from '@/lib/portal/lombard/lombardBorrowMath'
import { resolveEffectiveWalletCollateralRaw } from '@/lib/portal/lombard/lombardWalletCollateral'
import {
  formatLombardTokenAmount,
  lltvWadToPercent,
  parseLombardHumanAmountToRaw,
  rawToLombardHumanAmount,
} from '@/lib/portal/lombard/lombardFormat'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'

export class LombardQuoteError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'LombardQuoteError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

async function readCollateralBalance(args: {
  tokenAddress: string
  walletAddress: string
  decimals: number
}): Promise<{ raw: bigint; display: string }> {
  const client = createBasePublicClient({ side: 'server' })
  const raw = await client.readContract({
    address: args.tokenAddress as Address,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: [args.walletAddress as Address],
  })
  return {
    raw,
    display: rawToLombardHumanAmount(raw, args.decimals),
  }
}

function findMinimumCollateralForBorrow(args: {
  marketData: Awaited<ReturnType<ResolvedLombardMarket['morphoMarket']['getMarketData']>>
  position: ReturnType<typeof readLombardPositionBorrowSnapshot>
  borrowAmountRaw: bigint
  maxLtvWad: bigint
  walletCollateralRaw: bigint
}): bigint {
  const guaranteeAmountRaw = findMinimumIncrementalCollateralForBorrow(args)
  if (guaranteeAmountRaw == null) {
    throw new LombardQuoteError(
      'lombard.collateral_quote_failed',
      'Unable to compute guarantee amount for this borrow request.',
    )
  }
  return guaranteeAmountRaw
}

function projectedLtvRatio(args: {
  marketData: Awaited<ReturnType<ResolvedLombardMarket['morphoMarket']['getMarketData']>>
  position: ReturnType<typeof readLombardPositionBorrowSnapshot>
  additionalCollateralRaw: bigint
  additionalBorrowRaw: bigint
}): number {
  const projected = computeProjectedPositionLtvRatio({
    marketData: args.marketData,
    position: args.position,
    additionalCollateralRaw: args.additionalCollateralRaw,
    additionalBorrowRaw: args.additionalBorrowRaw,
  })
  if (projected == null) {
    throw new LombardQuoteError('lombard.oracle_unavailable', 'Market pricing is temporarily unavailable.')
  }
  return projected
}

export async function buildLombardQuote(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
  portalWalletCollateralBalance?: string | null
}): Promise<LombardQuoteResult> {
  const targetLtvPercent = clampLombardTargetLtvPercent(args.targetLtvPercent)
  if (targetLtvPercent <= 0) {
    throw new LombardQuoteError('lombard.invalid_target_ltv', 'Choose a target LTV between 1% and 70%.')
  }

  if (isLombardMockEnabled()) {
    const { buildLombardMockQuote } = await import('@/lib/portal/lombard/mocks/lombardLocalMock')
    return buildLombardMockQuote({ ...args, targetLtvPercent })
  }

  const resolved = await resolveLombardMarket({ collateral: args.collateral })
  const { config, gql, morphoMarket } = resolved

  const borrowAmountRaw = parseLombardHumanAmountToRaw(args.borrowAmount, gql.loanAsset.decimals)
  if (borrowAmountRaw <= BigInt(0)) {
    throw new LombardQuoteError('lombard.invalid_borrow_amount', 'Enter a valid USDC amount.')
  }

  const [marketData, walletBalance, positionData] = await Promise.all([
    morphoMarket.getMarketData(),
    readCollateralBalance({
      tokenAddress: gql.collateralAsset.address,
      walletAddress: args.walletAddress,
      decimals: gql.collateralAsset.decimals,
    }),
    morphoMarket.getPositionData(args.walletAddress as Address),
  ])
  const position = readLombardPositionBorrowSnapshot(positionData)
  const walletCollateralRaw = resolveEffectiveWalletCollateralRaw({
    onChainRaw: walletBalance.raw,
    portalBalanceHuman: args.portalWalletCollateralBalance,
    decimals: gql.collateralAsset.decimals,
  })
  const walletGuaranteeDisplay = rawToLombardHumanAmount(
    walletCollateralRaw,
    gql.collateralAsset.decimals,
  )

  const targetLtvWad = lombardTargetLtvPercentToWad(targetLtvPercent)
  const absoluteMaxLtvWad = lombardMaxUserLtvWad()
  const absoluteMaxBorrowRaw = computeMaxIncrementalBorrowRawWithFallback({
    marketData,
    position,
    walletCollateralRaw,
    maxLtvWad: absoluteMaxLtvWad,
  })
  const maxBorrowRaw = computeMaxIncrementalBorrowRawWithFallback({
    marketData,
    position,
    walletCollateralRaw,
    maxLtvWad: targetLtvWad,
  })
  if (maxBorrowRaw == null || absoluteMaxBorrowRaw == null) {
    throw new LombardQuoteError('lombard.oracle_unavailable', 'Market pricing is temporarily unavailable.')
  }

  if (borrowAmountRaw > maxBorrowRaw) {
    throw new LombardQuoteError(
      'lombard.borrow_exceeds_capacity',
      `Maximum available borrow is ${formatLombardTokenAmount(maxBorrowRaw, gql.loanAsset.decimals)} USDC at ${targetLtvPercent}% LTV with your current ${config.collateral} balance.`,
    )
  }

  const liquidityRaw = gql.state?.liquidityAssets ? BigInt(gql.state.liquidityAssets) : null
  if (liquidityRaw != null && borrowAmountRaw > liquidityRaw) {
    throw new LombardQuoteError(
      'lombard.insufficient_liquidity',
      'Not enough USDC liquidity is available on this market right now. Try a lower amount.',
      503,
    )
  }

  const guaranteeAmountRaw = findMinimumCollateralForBorrow({
    marketData,
    position,
    borrowAmountRaw,
    maxLtvWad: targetLtvWad,
    walletCollateralRaw,
  })

  if (guaranteeAmountRaw > walletCollateralRaw) {
    throw new LombardQuoteError(
      'lombard.insufficient_guarantee_balance',
      `You need ${formatLombardTokenAmount(guaranteeAmountRaw, gql.collateralAsset.decimals)} ${config.collateral} but only have ${walletGuaranteeDisplay}.`,
    )
  }

  const projectedLtv = projectedLtvRatio({
    marketData,
    position,
    additionalCollateralRaw: guaranteeAmountRaw,
    additionalBorrowRaw: borrowAmountRaw,
  })

  try {
    assertLombardUserLtvWithinCap(projectedLtv, VANCELIAN_LOMBARD_V1.maxUserLtv)
  } catch (error) {
    throw new LombardQuoteError(
      'lombard.ltv_cap_exceeded',
      error instanceof Error ? error.message : 'Borrow amount exceeds the 70% safety cap.',
    )
  }

  const safety = lombardSafetyDetails(projectedLtv)
  const recommendedBorrowRaw = (maxBorrowRaw * BigInt(70)) / BigInt(100)
  const borrowApyPercent =
    gql.state?.borrowApy != null && Number.isFinite(gql.state.borrowApy) ? gql.state.borrowApy * 100 : null

  return {
    marketId: config.marketId,
    collateral: config.collateral,
    collateralName: config.displayName,
    targetLtvPercent,
    borrowAmount: formatLombardTokenAmount(borrowAmountRaw, gql.loanAsset.decimals),
    borrowAmountRaw: borrowAmountRaw.toString(),
    guaranteeAmount: formatLombardTokenAmount(guaranteeAmountRaw, gql.collateralAsset.decimals),
    guaranteeAmountRaw: guaranteeAmountRaw.toString(),
    projectedLtvPercent: Math.round(projectedLtv * 10_000) / 100,
    safetyLevel: safety.level,
    safetyLabel: safety.label,
    safetyMessage: safety.message,
    maxBorrowAmount: formatLombardTokenAmount(maxBorrowRaw, gql.loanAsset.decimals),
    recommendedBorrowAmount: formatLombardTokenAmount(recommendedBorrowRaw, gql.loanAsset.decimals),
    borrowApyPercent,
    liquidationLltvPercent: lltvWadToPercent(BigInt(gql.lltv)),
    walletGuaranteeBalance: walletGuaranteeDisplay,
    poweredBy: 'Morpho',
  }
}

export async function assertLombardPrepareQuote(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
}): Promise<LombardQuoteResult> {
  return buildLombardQuote(args)
}

export { LombardMarketError }
