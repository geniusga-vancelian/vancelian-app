import type { LombardBorrowCapacity } from '@/lib/portal/lombard/lombardTypes'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { lombardMaxUserLtvWad, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  clampLombardTargetLtvPercent,
  lombardTargetLtvPercentToWad,
} from '@/lib/portal/lombard/lombardBorrowLtv'
import {
  computeMaxIncrementalBorrowRawWithFallback,
  readLombardPositionBorrowSnapshot,
} from '@/lib/portal/lombard/lombardBorrowMath'
import { resolveEffectiveWalletCollateralRaw } from '@/lib/portal/lombard/lombardWalletCollateral'
import {
  formatLombardTokenAmount,
  lltvWadToPercent,
  rawToLombardHumanAmount,
} from '@/lib/portal/lombard/lombardFormat'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { erc20Abi, type Address } from 'viem'
import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'

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

export async function buildLombardBorrowCapacity(args: {
  collateral: string
  walletAddress: string
  targetLtvPercent: number
  /** Solde garantie affiché côté portail (hub wallet) — aligne capacité si RPC `balanceOf` est en retard. */
  portalWalletCollateralBalance?: string | null
}): Promise<LombardBorrowCapacity> {
  const targetLtvPercent = clampLombardTargetLtvPercent(args.targetLtvPercent)
  if (targetLtvPercent <= 0) {
    throw new LombardQuoteError('lombard.invalid_target_ltv', 'Choose a target LTV between 1% and 70%.')
  }

  if (isLombardMockEnabled()) {
    const { buildLombardMockBorrowCapacity } = await import('@/lib/portal/lombard/mocks/lombardLocalMock')
    return buildLombardMockBorrowCapacity({ ...args, targetLtvPercent })
  }

  const resolved = await resolveLombardMarket({ collateral: args.collateral })
  const { config, gql, morphoMarket } = resolved

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

  const absoluteMaxLtvWad = lombardMaxUserLtvWad()
  const targetLtvWad = lombardTargetLtvPercentToWad(targetLtvPercent)
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

  const recommendedBorrowRaw = (maxBorrowRaw * BigInt(70)) / BigInt(100)
  const borrowApyPercent =
    gql.state?.borrowApy != null && Number.isFinite(gql.state.borrowApy) ? gql.state.borrowApy * 100 : null

  return {
    marketId: config.marketId,
    collateral: config.collateral,
    collateralName: config.displayName,
    targetLtvPercent,
    maxBorrowAmount: formatLombardTokenAmount(maxBorrowRaw, gql.loanAsset.decimals),
    maxBorrowAmountRaw: maxBorrowRaw.toString(),
    absoluteMaxBorrowAmount: formatLombardTokenAmount(absoluteMaxBorrowRaw, gql.loanAsset.decimals),
    recommendedBorrowAmount: formatLombardTokenAmount(recommendedBorrowRaw, gql.loanAsset.decimals),
    walletGuaranteeBalance: rawToLombardHumanAmount(
      walletCollateralRaw,
      gql.collateralAsset.decimals,
    ),
    borrowApyPercent,
    liquidationLltvPercent: lltvWadToPercent(BigInt(gql.lltv)),
    maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
    poweredBy: 'Morpho',
  }
}
