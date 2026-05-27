import type { Prisma } from '@prisma/client'
import type { Address } from 'viem'

import { prisma } from '@/lib/prisma'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { getLombardReconciliationToleranceBps } from '@/lib/portal/lombard/lombardBetaConfig'
import { logLombardSupportEvent } from '@/lib/portal/lombard/lombardSupportLog'
import { logLombardOpsEvent } from '@/lib/portal/lombard/lombardOpsLog'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { mapLombardAccrualPosition } from '@/lib/portal/lombard/lombardPositionService'

export type LombardReconciliationStatus = 'confirmed' | 'confirmed_with_delta'

export type LombardReconciliationDelta = {
  borrowDeltaRaw: string
  collateralDeltaRaw: string
  borrowDeltaBps: number
  collateralDeltaBps: number
}

export type LombardReconciliationResult = {
  status: LombardReconciliationStatus
  marketId: string
  walletAddress: string
  expectedBorrowRaw: string
  expectedCollateralRaw: string
  actualBorrowRaw: string
  actualCollateralRaw: string
  delta: LombardReconciliationDelta | null
}

function absBigInt(value: bigint): bigint {
  return value < BigInt(0) ? -value : value
}

export function computeLombardRelativeDeltaBps(expected: bigint, actual: bigint): number {
  if (expected <= BigInt(0) && actual <= BigInt(0)) return 0
  const baseline = expected > BigInt(0) ? expected : actual
  if (baseline <= BigInt(0)) return 10_000
  const delta = absBigInt(actual - expected)
  return Number((delta * BigInt(10_000)) / baseline)
}

export function evaluateLombardReconciliation(args: {
  expectedBorrowRaw: bigint
  expectedCollateralRaw: bigint
  actualBorrowRaw: bigint
  actualCollateralRaw: bigint
  toleranceBps?: number
}): { status: LombardReconciliationStatus; delta: LombardReconciliationDelta | null } {
  const toleranceBps = args.toleranceBps ?? getLombardReconciliationToleranceBps()
  const borrowDeltaBps = computeLombardRelativeDeltaBps(args.expectedBorrowRaw, args.actualBorrowRaw)
  const collateralDeltaBps = computeLombardRelativeDeltaBps(
    args.expectedCollateralRaw,
    args.actualCollateralRaw,
  )

  const delta: LombardReconciliationDelta = {
    borrowDeltaRaw: (args.actualBorrowRaw - args.expectedBorrowRaw).toString(),
    collateralDeltaRaw: (args.actualCollateralRaw - args.expectedCollateralRaw).toString(),
    borrowDeltaBps,
    collateralDeltaBps,
  }

  const withinTolerance = borrowDeltaBps <= toleranceBps && collateralDeltaBps <= toleranceBps
  return {
    status: withinTolerance ? 'confirmed' : 'confirmed_with_delta',
    delta: withinTolerance ? null : delta,
  }
}

function readMetadataString(metadata: Prisma.JsonValue | null, key: string): string | null {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) return null
  const value = (metadata as Record<string, unknown>)[key]
  return typeof value === 'string' ? value : null
}

export async function reconcileLombardOpenLoanGroup(args: {
  personId: string
  groupKey: string
}): Promise<LombardReconciliationResult | null> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      idempotencyKey: args.groupKey,
      integrationMode: LOMBARD_INTEGRATION_MODE,
    },
    orderBy: [{ txIndex: 'asc' }, { operation: 'asc' }],
  })

  if (rows.length === 0) return null

  const primary = rows.find((row) => row.operation === 'deposit' && row.status === 'success') ?? null
  if (!primary) return null

  const metadata = primary.metadataJson
  const collateral = readMetadataString(metadata, 'collateral')
  const expectedBorrowRaw = BigInt(primary.amountRaw || readMetadataString(metadata, 'borrow_amount_raw') || '0')
  const expectedCollateralRaw = BigInt(readMetadataString(metadata, 'guarantee_amount_raw') || '0')
  if (!collateral || expectedBorrowRaw <= BigInt(0) || expectedCollateralRaw <= BigInt(0)) {
    return null
  }

  const resolved = await resolveLombardMarket({ collateral })
  const positionData = await resolved.morphoMarket.getPositionData(primary.walletAddress as Address)
  const mapped = mapLombardAccrualPosition({ resolved, position: positionData })

  const actualBorrowRaw = mapped ? BigInt(mapped.borrowAmountRaw) : BigInt(0)
  const actualCollateralRaw = mapped ? BigInt(mapped.collateralAmountRaw) : BigInt(0)

  const evaluation = evaluateLombardReconciliation({
    expectedBorrowRaw,
    expectedCollateralRaw,
    actualBorrowRaw,
    actualCollateralRaw,
  })

  const reconciliationPatch = {
    reconciliation_status: evaluation.status,
    reconciliation_checked_at: new Date().toISOString(),
    reconciliation_expected_borrow_raw: expectedBorrowRaw.toString(),
    reconciliation_expected_collateral_raw: expectedCollateralRaw.toString(),
    reconciliation_actual_borrow_raw: actualBorrowRaw.toString(),
    reconciliation_actual_collateral_raw: actualCollateralRaw.toString(),
    ...(evaluation.delta ? { reconciliation_delta: evaluation.delta } : {}),
  }

  for (const row of rows) {
    const currentMeta =
      row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
        ? (row.metadataJson as Record<string, unknown>)
        : {}
    await prisma.onchainVaultTransaction.update({
      where: { id: row.id },
      data: {
        metadataJson: {
          ...currentMeta,
          ...reconciliationPatch,
        },
      },
    })
  }

  if (evaluation.status === 'confirmed_with_delta' && evaluation.delta) {
    logLombardOpsEvent({
      code: 'lombard.reconciliation_delta',
      level: 'warning',
      message: 'Lombard open-loan reconciliation delta above tolerance.',
      personId: args.personId,
      walletAddress: primary.walletAddress,
      marketId: primary.vaultAddress,
      groupKey: args.groupKey,
      ledgerEntryId: primary.id,
      metadata: {
        delta: evaluation.delta,
      },
    })
    logLombardSupportEvent({
      code: 'lombard.reconciliation_delta',
      level: 'warning',
      message: 'Lombard open-loan reconciliation delta above tolerance.',
      personId: args.personId,
      walletAddress: primary.walletAddress,
      marketId: primary.vaultAddress,
      ledgerEntryId: primary.id,
      metadata: {
        groupKey: args.groupKey,
        delta: evaluation.delta,
      },
    })
  }

  return {
    status: evaluation.status,
    marketId: primary.vaultAddress,
    walletAddress: primary.walletAddress,
    expectedBorrowRaw: expectedBorrowRaw.toString(),
    expectedCollateralRaw: expectedCollateralRaw.toString(),
    actualBorrowRaw: actualBorrowRaw.toString(),
    actualCollateralRaw: actualCollateralRaw.toString(),
    delta: evaluation.delta,
  }
}
