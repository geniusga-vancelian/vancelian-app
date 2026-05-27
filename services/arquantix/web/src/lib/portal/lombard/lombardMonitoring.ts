import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  getLombardBetaLimitsForClient,
  isLombardV1BetaLimitsEnabled,
  isLombardWalletAllowlistConfigured,
} from '@/lib/portal/lombard/lombardBetaConfig'
import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { fetchLombardMockActivePositionsForWallet } from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { fetchLombardActivePositionsForWallet } from '@/lib/portal/lombard/lombardPositionService'
import type { Address } from 'viem'

import { prisma } from '@/lib/prisma'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'

export type LombardLedgerTxStats = {
  pendingCount: number
  failedCount: number
  revertedCount: number
  successCount: number
  confirmedWithDeltaCount: number
}

export type LombardMonitoringPositionRow = {
  walletAddress: string
  marketId: string
  collateralSymbol: string
  borrowAmount: string
  borrowAmountRaw: string
  collateralAmount: string
  currentLtvPercent: number | null
  healthStatus: string
}

export type LombardMonitoringSnapshot = {
  generatedAt: string
  featureEnabled: boolean
  betaLimitsEnabled: boolean
  allowlistConfigured: boolean
  mockMode?: boolean
  betaLimits: ReturnType<typeof getLombardBetaLimitsForClient> | null
  totals: {
    activePositions: number
    totalBorrowedUsdc: string
    totalCollateralUsdcValue: string
    positionsAbove60Ltv: number
    positionsAbove70Ltv: number
  }
  ledger: LombardLedgerTxStats
  positions: LombardMonitoringPositionRow[]
}

export function aggregateLombardMonitoringStats(args: {
  positions: Array<{
    walletAddress: string
    position: LombardActivePosition
  }>
  ledger: LombardLedgerTxStats
  featureEnabled: boolean
  betaLimitsEnabled: boolean
  allowlistConfigured: boolean
  mockMode?: boolean
}): LombardMonitoringSnapshot {
  let totalBorrowRaw = BigInt(0)
  let totalCollateralUsdRaw = BigInt(0)
  let above60 = 0
  let above70 = 0

  const rows: LombardMonitoringPositionRow[] = []

  for (const item of args.positions) {
    const position = item.position
    totalBorrowRaw += BigInt(position.borrowAmountRaw || '0')
    if (position.collateralUsdValue) {
      const normalized = position.collateralUsdValue.replace(',', '.')
      const usdcMicros = BigInt(Math.round(Number(normalized) * 1_000_000))
      if (usdcMicros > BigInt(0)) totalCollateralUsdRaw += usdcMicros
    }

    const ltv = position.currentLtvPercent
    if (ltv != null && ltv > 60) above60 += 1
    if (ltv != null && ltv > 70) above70 += 1

    rows.push({
      walletAddress: item.walletAddress,
      marketId: position.marketId,
      collateralSymbol: position.collateralSymbol,
      borrowAmount: position.borrowAmount,
      borrowAmountRaw: position.borrowAmountRaw,
      collateralAmount: position.collateralAmount,
      currentLtvPercent: position.currentLtvPercent,
      healthStatus: position.healthStatus,
    })
  }

  const formatUsdcFromRaw = (raw: bigint) => (Number(raw) / 1_000_000).toFixed(2)

  return {
    generatedAt: new Date().toISOString(),
    featureEnabled: args.featureEnabled,
    betaLimitsEnabled: args.betaLimitsEnabled,
    allowlistConfigured: args.allowlistConfigured,
    mockMode: args.mockMode ?? false,
    betaLimits: args.betaLimitsEnabled ? getLombardBetaLimitsForClient() : null,
    totals: {
      activePositions: rows.length,
      totalBorrowedUsdc: formatUsdcFromRaw(totalBorrowRaw),
      totalCollateralUsdcValue: formatUsdcFromRaw(totalCollateralUsdRaw),
      positionsAbove60Ltv: above60,
      positionsAbove70Ltv: above70,
    },
    ledger: args.ledger,
    positions: rows.sort((a, b) => b.borrowAmountRaw.localeCompare(a.borrowAmountRaw)),
  }
}

export async function loadLombardLedgerTxStats(): Promise<LombardLedgerTxStats> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: { integrationMode: LOMBARD_INTEGRATION_MODE },
    select: { status: true, metadataJson: true },
  })

  let pendingCount = 0
  let failedCount = 0
  let revertedCount = 0
  let successCount = 0
  let confirmedWithDeltaCount = 0

  for (const row of rows) {
    if (row.status === 'pending') pendingCount += 1
    if (row.status === 'failed') failedCount += 1
    if (row.status === 'reverted') revertedCount += 1
    if (row.status === 'success') successCount += 1

    const meta = row.metadataJson
    if (meta && typeof meta === 'object' && !Array.isArray(meta)) {
      const status = (meta as Record<string, unknown>).reconciliation_status
      if (status === 'confirmed_with_delta') confirmedWithDeltaCount += 1
    }
  }

  return {
    pendingCount,
    failedCount,
    revertedCount,
    successCount,
    confirmedWithDeltaCount,
  }
}

async function loadDistinctLombardWallets(): Promise<string[]> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: { integrationMode: LOMBARD_INTEGRATION_MODE },
    select: { walletAddress: true },
    distinct: ['walletAddress'],
  })
  return rows.map((row) => row.walletAddress.toLowerCase())
}

export async function getLombardMonitoringSnapshot(): Promise<LombardMonitoringSnapshot> {
  const featureEnabled = isLombardV1Enabled()
  const betaLimitsEnabled = isLombardV1BetaLimitsEnabled()
  const allowlistConfigured = isLombardWalletAllowlistConfigured()

  const [ledger, wallets] = await Promise.all([loadLombardLedgerTxStats(), loadDistinctLombardWallets()])

  const activePairs: Array<{ walletAddress: string; position: LombardActivePosition }> = []

  if (featureEnabled) {
    for (const walletAddress of wallets) {
      const positions = isLombardMockEnabled()
        ? await fetchLombardMockActivePositionsForWallet(walletAddress)
        : await fetchLombardActivePositionsForWallet(walletAddress as Address)
      for (const position of positions) {
        if (BigInt(position.borrowAmountRaw || '0') > BigInt(0)) {
          activePairs.push({ walletAddress, position })
        }
      }
    }
  }

  return aggregateLombardMonitoringStats({
    positions: activePairs,
    ledger,
    featureEnabled,
    betaLimitsEnabled,
    allowlistConfigured,
    mockMode: isLombardMockEnabled(),
  })
}