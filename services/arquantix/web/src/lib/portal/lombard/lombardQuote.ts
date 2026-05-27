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
  borrowAmountRaw: bigint
  maxLtvWad: bigint
}): bigint {
  const { marketData, borrowAmountRaw, maxLtvWad } = args
  if (borrowAmountRaw <= BigInt(0)) {
    throw new LombardQuoteError('lombard.invalid_borrow_amount', 'Borrow amount must be positive.')
  }

  let low = BigInt(1)
  let high = borrowAmountRaw * BigInt(10) ** BigInt(12)
  let best: bigint | null = null

  for (let i = 0; i < 96; i += 1) {
    const mid = (low + high) / BigInt(2)
    const maxBorrow = marketData.getMaxBorrowAssets(mid, { maxLtv: maxLtvWad })
    if (maxBorrow != null && maxBorrow >= borrowAmountRaw) {
      best = mid
      high = mid - BigInt(1)
    } else {
      low = mid + BigInt(1)
    }
    if (low > high) break
  }

  if (best == null) {
    throw new LombardQuoteError(
      'lombard.collateral_quote_failed',
      'Unable to compute guarantee amount for this borrow request.',
    )
  }

  return best
}

function projectedLtvRatio(args: {
  marketData: Awaited<ReturnType<ResolvedLombardMarket['morphoMarket']['getMarketData']>>
  collateralRaw: bigint
  borrowAmountRaw: bigint
}): number {
  const collateralValue = args.marketData.getCollateralValue(args.collateralRaw)
  if (collateralValue == null || collateralValue <= BigInt(0)) {
    throw new LombardQuoteError('lombard.oracle_unavailable', 'Market pricing is temporarily unavailable.')
  }
  return Number(args.borrowAmountRaw) / Number(collateralValue)
}

export async function buildLombardQuote(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
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

  const [marketData, walletBalance] = await Promise.all([
    morphoMarket.getMarketData(),
    readCollateralBalance({
      tokenAddress: gql.collateralAsset.address,
      walletAddress: args.walletAddress,
      decimals: gql.collateralAsset.decimals,
    }),
  ])

  const targetLtvWad = lombardTargetLtvPercentToWad(targetLtvPercent)
  const absoluteMaxLtvWad = lombardMaxUserLtvWad()
  const absoluteMaxBorrowRaw = marketData.getMaxBorrowAssets(walletBalance.raw, { maxLtv: absoluteMaxLtvWad })
  const maxBorrowRaw = marketData.getMaxBorrowAssets(walletBalance.raw, { maxLtv: targetLtvWad })
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
    borrowAmountRaw,
    maxLtvWad: targetLtvWad,
  })

  if (guaranteeAmountRaw > walletBalance.raw) {
    throw new LombardQuoteError(
      'lombard.insufficient_guarantee_balance',
      `You need ${formatLombardTokenAmount(guaranteeAmountRaw, gql.collateralAsset.decimals)} ${config.collateral} but only have ${walletBalance.display}.`,
    )
  }

  const projectedLtv = projectedLtvRatio({
    marketData,
    collateralRaw: guaranteeAmountRaw,
    borrowAmountRaw,
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
    walletGuaranteeBalance: walletBalance.display,
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
