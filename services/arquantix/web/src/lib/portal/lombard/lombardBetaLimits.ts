import { erc20Abi, type Address } from 'viem'

import { prisma } from '@/lib/prisma'
import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LOMBARD_INTEGRATION_MODE, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  getLombardBetaLimits,
  isLombardV1BetaLimitsEnabled,
  isLombardWalletAllowlisted,
  isLombardWalletAllowlistConfigured,
} from '@/lib/portal/lombard/lombardBetaConfig'
import { LombardBetaError } from '@/lib/portal/lombard/lombardBetaErrors'
import { logLombardSupportEvent } from '@/lib/portal/lombard/lombardSupportLog'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { fetchLombardActivePositionsForWallet } from '@/lib/portal/lombard/lombardPositionService'
import { formatLombardTokenAmount } from '@/lib/portal/lombard/lombardFormat'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { resolveEffectiveWalletCollateralRaw } from '@/lib/portal/lombard/lombardWalletCollateral'

export async function loadLombardWalletBorrowExposureRaw(walletAddress: string): Promise<bigint> {
  if (isLombardMockEnabled()) {
    const { loadLombardMockWalletBorrowExposureRaw } = await import(
      '@/lib/portal/lombard/mocks/lombardLocalMock'
    )
    return loadLombardMockWalletBorrowExposureRaw(walletAddress)
  }

  const positions = await fetchLombardActivePositionsForWallet(walletAddress as Address)
  return positions.reduce((sum, row) => sum + BigInt(row.borrowAmountRaw || '0'), BigInt(0))
}

export async function loadLombardGlobalBorrowExposureRaw(): Promise<bigint> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      integrationMode: LOMBARD_INTEGRATION_MODE,
      operation: 'deposit',
      status: 'success',
    },
    select: { walletAddress: true },
    distinct: ['walletAddress'],
  })

  let total = BigInt(0)
  for (const row of rows) {
    const walletExposure = await loadLombardWalletBorrowExposureRaw(row.walletAddress)
    total += walletExposure
  }
  return total
}

export async function assertLombardBetaAccess(args: {
  walletAddress: string
}): Promise<void> {
  if (!isLombardV1BetaLimitsEnabled()) return

  if (isLombardWalletAllowlistConfigured() && !isLombardWalletAllowlisted(args.walletAddress)) {
    throw new LombardBetaError(
      'lombard.beta.wallet_not_allowlisted',
      'This wallet is not enabled for the Lombard beta.',
      403,
    )
  }
}

export async function assertLombardBetaBorrowLimits(args: {
  personId: string
  walletAddress: string
  newBorrowAmountRaw: bigint
}): Promise<void> {
  if (!isLombardV1BetaLimitsEnabled()) return

  const limits = getLombardBetaLimits()

  if (args.newBorrowAmountRaw <= BigInt(0)) {
    throw new LombardBetaError('lombard.beta.invalid_borrow_amount', 'Borrow amount must be positive.')
  }

  const [walletExposure, globalExposure] = await Promise.all([
    loadLombardWalletBorrowExposureRaw(args.walletAddress),
    loadLombardGlobalBorrowExposureRaw(),
  ])

  const nextWalletExposure = walletExposure + args.newBorrowAmountRaw
  if (nextWalletExposure > limits.maxBorrowUsdcPerWalletRaw) {
    logLombardSupportEvent({
      code: 'lombard.beta_limit_exceeded',
      level: 'warning',
      message: 'Wallet Lombard borrow cap exceeded.',
      personId: args.personId,
      walletAddress: args.walletAddress,
      metadata: {
        walletExposure: walletExposure.toString(),
        newBorrowAmountRaw: args.newBorrowAmountRaw.toString(),
        maxBorrowUsdcPerWalletRaw: limits.maxBorrowUsdcPerWalletRaw.toString(),
      },
    })
    throw new LombardBetaError(
      'lombard.beta.wallet_borrow_cap',
      `Maximum borrow per wallet: ${formatLombardTokenAmount(limits.maxBorrowUsdcPerWalletRaw, limits.assetDecimals)} USDC.`,
    )
  }

  const nextGlobalExposure = globalExposure + args.newBorrowAmountRaw
  if (nextGlobalExposure > limits.maxTotalBorrowUsdcGlobalRaw) {
    logLombardSupportEvent({
      code: 'lombard.beta_limit_exceeded',
      level: 'critical',
      message: 'Global Lombard borrow cap exceeded.',
      personId: args.personId,
      metadata: {
        globalExposure: globalExposure.toString(),
        newBorrowAmountRaw: args.newBorrowAmountRaw.toString(),
        maxTotalBorrowUsdcGlobalRaw: limits.maxTotalBorrowUsdcGlobalRaw.toString(),
      },
    })
    throw new LombardBetaError(
      'lombard.beta.global_borrow_cap',
      'Global Lombard beta capacity reached. Try again later.',
      503,
    )
  }
}

export async function readLombardCollateralBalanceRaw(args: {
  collateral: string
  walletAddress: string
  /** Solde hub wallet — même source que capacité / devis Morpho. */
  portalWalletCollateralBalance?: string | null
}): Promise<bigint> {
  if (isLombardMockEnabled()) {
    const { readLombardMockCollateralBalanceRaw } = await import(
      '@/lib/portal/lombard/mocks/lombardLocalMock'
    )
    return readLombardMockCollateralBalanceRaw(args)
  }

  const resolved = await resolveLombardMarket({ collateral: args.collateral })
  const client = createBasePublicClient({ side: 'server' })
  const onChainRaw = await client.readContract({
    address: resolved.gql.collateralAsset.address as Address,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: [args.walletAddress as Address],
  })
  return resolveEffectiveWalletCollateralRaw({
    onChainRaw,
    portalBalanceHuman: args.portalWalletCollateralBalance,
    decimals: resolved.gql.collateralAsset.decimals,
  })
}

export async function assertLombardCollateralBalanceCoversGuarantee(args: {
  collateral: string
  walletAddress: string
  guaranteeAmountRaw: bigint
  portalWalletCollateralBalance?: string | null
}): Promise<void> {
  const balance = await readLombardCollateralBalanceRaw({
    collateral: args.collateral,
    walletAddress: args.walletAddress,
    portalWalletCollateralBalance: args.portalWalletCollateralBalance,
  })

  if (balance < args.guaranteeAmountRaw) {
    throw new LombardBetaError(
      'lombard.balance_changed',
      'Solde de garantie insuffisant. Actualisez le montant ou réessayez dans quelques secondes.',
      409,
    )
  }
}

export function assertLombardBaseChain(chainId?: number): void {
  const expected = VANCELIAN_LOMBARD_V1.chainId
  if ((chainId ?? expected) !== expected) {
    throw new LombardBetaError(
      'lombard.unsupported_chain',
      'Liquidity advance is only available on Base.',
      400,
    )
  }
}
