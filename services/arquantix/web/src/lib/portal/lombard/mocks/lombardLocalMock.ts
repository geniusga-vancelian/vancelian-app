import type { OnchainVaultTransaction } from '@prisma/client'
import type { Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { LOMBARD_INTEGRATION_MODE, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  formatLombardTokenAmount,
  parseLombardHumanAmountToRaw,
} from '@/lib/portal/lombard/lombardFormat'
import { lombardSafetyDetails } from '@/lib/portal/lombard/lombardHealth'
import { createLombardLedgerEntries } from '@/lib/portal/lombard/lombardLedger'
import {
  getLombardMockConfig,
  getLombardMockBorrowApyPercent,
  getLombardMockLltvPercent,
  getLombardMockLiquidityRaw,
  isLombardMockEnabled,
  isLombardMockPositionEnabled,
} from '@/lib/portal/lombard/lombardMockConfig'
import type { LombardMorphoMarketRow } from '@/lib/portal/lombard/lombardGraphql'
import { buildLombardActivePositionRow } from '@/lib/portal/lombard/lombardPositionService'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { clampLombardTargetLtvPercent, lombardTargetLtvRatio } from '@/lib/portal/lombard/lombardBorrowLtv'
import { LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import type {
  LombardBorrowCapacity,
  LombardMarketSummary,
  LombardPreparePayload,
  LombardPreparedTx,
  LombardQuoteResult,
} from '@/lib/portal/lombard/lombardTypes'
import { MorphoVaultLedgerError } from '@/lib/portal/morphoVaultLedger'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'
import { generateLombardMockTxHash } from '@/lib/portal/lombard/mocks/lombardMockTxHash'
import {
  aggregateMockOpenLoansByMarket,
  computeMockAggregateLtvWad,
} from '@/lib/portal/lombard/mocks/lombardMockPositionAggregate'

export { generateLombardMockTxHash } from '@/lib/portal/lombard/mocks/lombardMockTxHash'

export const LOMBARD_MOCK_TX_METADATA: Prisma.InputJsonValue = {
  lombard_mock: true,
  source: 'lombard_v1_local_mock',
}

const MOCK_TX_TARGET = '0x00000000000000000000000000000000000101'

const MOCK_GQL_BY_COLLATERAL = {
  cbBTC: {
    collateralDecimals: 8,
    loanDecimals: 6,
    collateralTokenAddress: '0xcbbtc0000000000000000000000000000000001',
    loanTokenAddress: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  },
  cbETH: {
    collateralDecimals: 18,
    loanDecimals: 6,
    collateralTokenAddress: '0xcbeth00000000000000000000000000000000001',
    loanTokenAddress: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
  },
} as const

function findMarketConfig(collateral: string) {
  const normalized = collateral.trim()
  return (
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral === normalized) ??
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral.toLowerCase() === normalized.toLowerCase()) ??
    null
  )
}

function mockCollateralBalanceRaw(collateral: string): bigint {
  const config = getLombardMockConfig()
  const row = findMarketConfig(collateral)
  if (!row) return BigInt(0)
  const gql = MOCK_GQL_BY_COLLATERAL[row.collateral as 'cbBTC' | 'cbETH']
  const human =
    row.collateral === 'cbBTC' ? config.walletBalanceCbBtc : config.walletBalanceCbEth
  return parseLombardHumanAmountToRaw(String(human), gql.collateralDecimals)
}

export function readLombardMockCollateralBalanceRaw(args: {
  collateral: string
  walletAddress: string
}): Promise<bigint> {
  void args.walletAddress
  return Promise.resolve(mockCollateralBalanceRaw(args.collateral))
}

export function getLombardMockMarketSummaries(): LombardMarketSummary[] {
  const cfg = getLombardMockConfig()
  return VANCELIAN_LOMBARD_V1.markets.map((market) => {
    const gql = MOCK_GQL_BY_COLLATERAL[market.collateral as 'cbBTC' | 'cbETH']
    return {
      marketId: market.marketId,
      collateral: market.collateral,
      collateralName: market.displayName,
      borrowAsset: 'USDC' as const,
      chain: 'base' as const,
      chainId: VANCELIAN_LOMBARD_V1.chainId,
      borrowApyPercent: cfg.borrowApyBps / 100,
      liquidationLltvPercent: cfg.lltvBps / 100,
      maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
      poweredBy: 'Morpho' as const,
      collateralTokenAddress: gql.collateralTokenAddress,
      loanTokenAddress: gql.loanTokenAddress,
      collateralDecimals: gql.collateralDecimals,
      loanDecimals: gql.loanDecimals,
    }
  })
}

export function buildLombardMockBorrowCapacity(args: {
  collateral: string
  walletAddress: string
  targetLtvPercent: number
}): LombardBorrowCapacity {
  void args.walletAddress
  const targetLtvPercent = clampLombardTargetLtvPercent(args.targetLtvPercent)
  if (targetLtvPercent <= 0) {
    throw new LombardQuoteError('lombard.invalid_target_ltv', 'Choose a target LTV between 1% and 70%.')
  }

  const market = findMarketConfig(args.collateral)
  if (!market) {
    throw new LombardQuoteError('lombard.market_not_configured', 'Market not supported.')
  }

  const mockCfg = getLombardMockConfig()
  const gql = MOCK_GQL_BY_COLLATERAL[market.collateral as 'cbBTC' | 'cbETH']
  const balanceRaw = mockCollateralBalanceRaw(market.collateral)
  const collateralUsd =
    market.collateral === 'cbBTC'
      ? mockCfg.walletBalanceCbBtc * mockCfg.collateralUsdPrice.cbBTC
      : mockCfg.walletBalanceCbEth * mockCfg.collateralUsdPrice.cbETH
  const absoluteMaxBorrowRaw = BigInt(Math.round(collateralUsd * VANCELIAN_LOMBARD_V1.maxUserLtv * 1_000_000))
  const targetRatio = lombardTargetLtvRatio(targetLtvPercent)
  const maxBorrowRaw = BigInt(Math.round(collateralUsd * targetRatio * 1_000_000))
  const recommendedBorrowRaw = (maxBorrowRaw * BigInt(70)) / BigInt(100)

  return {
    marketId: market.marketId,
    collateral: market.collateral,
    collateralName: market.displayName,
    targetLtvPercent,
    maxBorrowAmount: formatLombardTokenAmount(maxBorrowRaw, gql.loanDecimals),
    maxBorrowAmountRaw: maxBorrowRaw.toString(),
    absoluteMaxBorrowAmount: formatLombardTokenAmount(absoluteMaxBorrowRaw, gql.loanDecimals),
    recommendedBorrowAmount: formatLombardTokenAmount(recommendedBorrowRaw, gql.loanDecimals),
    walletGuaranteeBalance: formatLombardTokenAmount(balanceRaw, gql.collateralDecimals),
    borrowApyPercent: getLombardMockBorrowApyPercent(),
    liquidationLltvPercent: getLombardMockLltvPercent(),
    maxUserLtvPercent: VANCELIAN_LOMBARD_V1.maxUserLtv * 100,
    poweredBy: 'Morpho',
  }
}

export async function buildLombardMockQuote(args: {
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
}): Promise<LombardQuoteResult> {
  void args.walletAddress
  const targetLtvPercent = clampLombardTargetLtvPercent(args.targetLtvPercent)
  if (targetLtvPercent <= 0) {
    throw new LombardQuoteError('lombard.invalid_target_ltv', 'Choose a target LTV between 1% and 70%.')
  }

  const market = findMarketConfig(args.collateral)
  if (!market) {
    throw new LombardQuoteError('lombard.market_not_configured', 'Market not supported.')
  }

  const mockCfg = getLombardMockConfig()
  const gql = MOCK_GQL_BY_COLLATERAL[market.collateral as 'cbBTC' | 'cbETH']
  const borrowAmountRaw = parseLombardHumanAmountToRaw(args.borrowAmount, gql.loanDecimals)
  if (borrowAmountRaw <= BigInt(0)) {
    throw new LombardQuoteError('lombard.invalid_borrow_amount', 'Enter a valid USDC amount.')
  }

  const liquidityRaw = getLombardMockLiquidityRaw()
  if (borrowAmountRaw > liquidityRaw) {
    throw new LombardQuoteError(
      'lombard.insufficient_liquidity',
      'Not enough USDC liquidity is available on this market right now. Try a lower amount.',
      503,
    )
  }

  const balanceRaw = mockCollateralBalanceRaw(market.collateral)
  const collateralUsd =
    market.collateral === 'cbBTC'
      ? mockCfg.walletBalanceCbBtc * mockCfg.collateralUsdPrice.cbBTC
      : mockCfg.walletBalanceCbEth * mockCfg.collateralUsdPrice.cbETH
  const targetRatio = lombardTargetLtvRatio(targetLtvPercent)
  const absoluteMaxBorrowRaw = BigInt(Math.round(collateralUsd * VANCELIAN_LOMBARD_V1.maxUserLtv * 1_000_000))
  const maxBorrowRaw = BigInt(Math.round(collateralUsd * targetRatio * 1_000_000))

  if (borrowAmountRaw > maxBorrowRaw) {
    throw new LombardQuoteError(
      'lombard.borrow_exceeds_capacity',
      `Maximum available borrow is ${formatLombardTokenAmount(maxBorrowRaw, gql.loanDecimals)} USDC at ${targetLtvPercent}% LTV with your current ${market.collateral} balance.`,
    )
  }

  const borrowUsd = Number(borrowAmountRaw) / 1_000_000
  const guaranteeUsd = borrowUsd / targetRatio
  const price = mockCfg.collateralUsdPrice[market.collateral as 'cbBTC' | 'cbETH']
  const guaranteeHuman = guaranteeUsd / price
  const guaranteeAmountRaw = parseLombardHumanAmountToRaw(
    guaranteeHuman.toFixed(market.collateral === 'cbBTC' ? 8 : 6),
    gql.collateralDecimals,
  )

  if (guaranteeAmountRaw > balanceRaw) {
    throw new LombardQuoteError(
      'lombard.insufficient_guarantee_balance',
      `You need ${formatLombardTokenAmount(guaranteeAmountRaw, gql.collateralDecimals)} ${market.collateral} but only have ${formatLombardTokenAmount(balanceRaw, gql.collateralDecimals)}.`,
    )
  }

  const projectedLtv = borrowUsd / (guaranteeUsd || 1)
  if (projectedLtv > targetRatio + 1e-9) {
    throw new LombardQuoteError(
      'lombard.ltv_cap_exceeded',
      `Borrow amount exceeds the ${targetLtvPercent}% target LTV.`,
    )
  }

  const safety = lombardSafetyDetails(projectedLtv)
  const recommendedBorrowRaw = (maxBorrowRaw * BigInt(70)) / BigInt(100)

  return {
    marketId: market.marketId,
    collateral: market.collateral,
    collateralName: market.displayName,
    targetLtvPercent,
    borrowAmount: formatLombardTokenAmount(borrowAmountRaw, gql.loanDecimals),
    borrowAmountRaw: borrowAmountRaw.toString(),
    guaranteeAmount: formatLombardTokenAmount(guaranteeAmountRaw, gql.collateralDecimals),
    guaranteeAmountRaw: guaranteeAmountRaw.toString(),
    projectedLtvPercent: Math.round(projectedLtv * 10_000) / 100,
    safetyLevel: safety.level,
    safetyLabel: safety.label,
    safetyMessage: safety.message,
    maxBorrowAmount: formatLombardTokenAmount(maxBorrowRaw, gql.loanDecimals),
    recommendedBorrowAmount: formatLombardTokenAmount(recommendedBorrowRaw, gql.loanDecimals),
    borrowApyPercent: getLombardMockBorrowApyPercent(),
    liquidationLltvPercent: getLombardMockLltvPercent(),
    walletGuaranteeBalance: formatLombardTokenAmount(balanceRaw, gql.collateralDecimals),
    poweredBy: 'Morpho',
  }
}

function buildMockTransactions(): LombardPreparedTx[] {
  const chainId = VANCELIAN_LOMBARD_V1.chainId
  const base = {
    to: MOCK_TX_TARGET,
    data: '0x',
    value: '0x0',
    chainId,
  }
  return [
    { ...base, operation: 'approve' },
    { ...base, operation: 'open_loan' },
  ]
}

export async function prepareLombardMockOpenLoan(args: {
  personId: string
  collateral: string
  borrowAmount: string
  walletAddress: string
  idempotencyKey: string
  quote: LombardQuoteResult
  privyWalletId?: string | null
  walletMetadata?: WalletSourceMetadata
}): Promise<LombardPreparePayload & { mockExecution: true }> {
  const transactions = buildMockTransactions()
  const ledgerEntries = await createLombardLedgerEntries({
    personId: args.personId,
    marketId: args.quote.marketId,
    walletAddress: args.walletAddress,
    privyWalletId: args.privyWalletId ?? null,
    idempotencyKey: args.idempotencyKey,
    quote: args.quote,
    transactions,
    walletMetadata: args.walletMetadata,
  })

  for (const row of ledgerEntries) {
    await prisma.onchainVaultTransaction.update({
      where: { id: row.id },
      data: {
        metadataJson: {
          ...(row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
            ? (row.metadataJson as Record<string, unknown>)
            : {}),
          ...(LOMBARD_MOCK_TX_METADATA as Record<string, unknown>),
        } as Prisma.InputJsonValue,
      },
    })
  }

  return {
    transactions,
    ledgerEntries: ledgerEntries.map((row) => ({
      id: row.id,
      operation: row.operation,
      txIndex: row.txIndex,
    })),
    groupKey: args.idempotencyKey,
    idempotencyKey: args.idempotencyKey,
    quote: args.quote,
    mockExecution: true,
  }
}

export async function lombardMockUpdateLedgerSuccess(args: {
  ledgerEntryId: string
  personId: string
  txHash?: string
}): Promise<OnchainVaultTransaction> {
  const entry = await prisma.onchainVaultTransaction.findFirst({
    where: { id: args.ledgerEntryId, personId: args.personId },
  })
  if (!entry) {
    throw new MorphoVaultLedgerError('lombard.ledger_not_found', 'Ledger entry not found.', 404)
  }
  if (entry.status === 'success') return entry

  return prisma.onchainVaultTransaction.update({
    where: { id: entry.id },
    data: {
      txHash: args.txHash ?? generateLombardMockTxHash(),
      blockNumber: BigInt(1),
      status: 'success',
      errorMessage: null,
      metadataJson: {
        ...(entry.metadataJson && typeof entry.metadataJson === 'object' && !Array.isArray(entry.metadataJson)
          ? (entry.metadataJson as Record<string, unknown>)
          : {}),
        ...(LOMBARD_MOCK_TX_METADATA as Record<string, unknown>),
        mock_confirmed_at: new Date().toISOString(),
      } as Prisma.InputJsonValue,
    },
  })
}

function mockGqlRow(collateral: 'cbBTC' | 'cbETH'): LombardMorphoMarketRow {
  const gql = MOCK_GQL_BY_COLLATERAL[collateral]
  const cfg = getLombardMockConfig()
  const market =
    VANCELIAN_LOMBARD_V1.markets.find((row) => row.collateral === collateral) ??
    VANCELIAN_LOMBARD_V1.markets[0]
  return {
    marketId: market.marketId,
    loanAsset: { address: gql.loanTokenAddress, symbol: 'USDC', decimals: gql.loanDecimals },
    collateralAsset: {
      address: gql.collateralTokenAddress,
      symbol: collateral,
      decimals: gql.collateralDecimals,
    },
    lltv: String(Math.round(cfg.lltvBps * 1e14)),
    oracle: { address: '0x663BECd10daE6C4A3Dcd89F1d76c1174199639B9' },
    irmAddress: '0x46415998764C29aB2a25CbeA6254146D50D22687',
    state: {
      borrowApy: cfg.borrowApyBps / 10_000,
      borrowAssets: '0',
      liquidityAssets: getLombardMockLiquidityRaw().toString(),
    },
  }
}

async function loadMockPositionsFromLedger(walletAddress: string): Promise<LombardActivePosition[]> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      integrationMode: LOMBARD_INTEGRATION_MODE,
      walletAddress: walletAddress.toLowerCase(),
      operation: 'deposit',
      status: 'success',
    },
    orderBy: { createdAt: 'asc' },
  })

  const slices = aggregateMockOpenLoansByMarket(
    rows.map((row) => {
      const meta =
        row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
          ? (row.metadataJson as Record<string, unknown>)
          : {}
      return {
        lombardOperation: typeof meta.lombard_operation === 'string' ? meta.lombard_operation : null,
        collateral: typeof meta.collateral === 'string' ? meta.collateral : null,
        borrowRaw: BigInt(row.amountRaw || String(meta.borrow_amount_raw || '0')),
        collateralRaw: BigInt(String(meta.guarantee_amount_raw || '0')),
      }
    }),
  )

  const cfg = getLombardMockConfig()
  const positions: LombardActivePosition[] = []

  for (const slice of slices) {
    const gql = mockGqlRow(slice.market.collateral as 'cbBTC' | 'cbETH')
    const currentLtvWad = computeMockAggregateLtvWad({
      collateral: slice.market.collateral as 'cbBTC' | 'cbETH',
      borrowRaw: slice.borrowRaw,
      collateralRaw: slice.collateralRaw,
      loanDecimals: gql.loanAsset.decimals,
      collateralDecimals: gql.collateralAsset.decimals,
      collateralUsdPrice: cfg.collateralUsdPrice[slice.market.collateral as 'cbBTC' | 'cbETH'],
    })

    const mapped = buildLombardActivePositionRow({
      marketConfig: slice.market,
      gql,
      collateralAmountRaw: slice.collateralRaw,
      borrowAmountRaw: slice.borrowRaw,
      currentLtvWad,
      liquidationPriceRaw: null,
    })
    if (mapped) positions.push(mapped)
  }

  return positions
}

export async function fetchLombardMockActivePositionsForWallet(
  walletAddress: string,
): Promise<LombardActivePosition[]> {
  if (!isLombardMockEnabled() || !isLombardMockPositionEnabled()) return []
  return loadMockPositionsFromLedger(walletAddress)
}

export async function loadLombardMockWalletBorrowExposureRaw(walletAddress: string): Promise<bigint> {
  const positions = await fetchLombardMockActivePositionsForWallet(walletAddress)
  return positions.reduce((sum, row) => sum + BigInt(row.borrowAmountRaw || '0'), BigInt(0))
}

export async function reconcileLombardMockOpenLoanGroup(args: {
  personId: string
  groupKey: string
}): Promise<{
  status: 'confirmed'
  marketId: string
  walletAddress: string
  expectedBorrowRaw: string
  expectedCollateralRaw: string
  actualBorrowRaw: string
  actualCollateralRaw: string
  delta: null
} | null> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      idempotencyKey: args.groupKey,
      integrationMode: LOMBARD_INTEGRATION_MODE,
    },
  })
  const primary = rows.find((row) => row.operation === 'deposit' && row.status === 'success')
  if (!primary) return null

  const meta =
    primary.metadataJson && typeof primary.metadataJson === 'object' && !Array.isArray(primary.metadataJson)
      ? (primary.metadataJson as Record<string, unknown>)
      : {}

  const expectedBorrowRaw = String(primary.amountRaw || meta.borrow_amount_raw || '0')
  const expectedCollateralRaw = String(meta.guarantee_amount_raw || '0')
  const patch = {
    reconciliation_status: 'confirmed',
    reconciliation_checked_at: new Date().toISOString(),
    reconciliation_expected_borrow_raw: expectedBorrowRaw,
    reconciliation_expected_collateral_raw: expectedCollateralRaw,
    reconciliation_actual_borrow_raw: expectedBorrowRaw,
    reconciliation_actual_collateral_raw: expectedCollateralRaw,
    reconciliation_mock: true,
  }

  for (const row of rows) {
    const currentMeta =
      row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
        ? (row.metadataJson as Record<string, unknown>)
        : {}
    await prisma.onchainVaultTransaction.update({
      where: { id: row.id },
      data: { metadataJson: { ...currentMeta, ...patch } },
    })
  }

  return {
    status: 'confirmed',
    marketId: primary.vaultAddress,
    walletAddress: primary.walletAddress,
    expectedBorrowRaw,
    expectedCollateralRaw,
    actualBorrowRaw: expectedBorrowRaw,
    actualCollateralRaw: expectedCollateralRaw,
    delta: null,
  }
}

export function isLombardMockLedgerEntry(metadata: unknown): boolean {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) return false
  return (metadata as Record<string, unknown>).lombard_mock === true
}
