/**
 * Ledger Morpho vault (Prisma) — prepare / confirm / positions.
 *
 * Legacy `integration_mode = privy_earn` ledger rows are read-only historical data.
 * New Morpho execution uses `direct_morpho` only (`wallet_source`: privy_embedded | external_evm).
 */
import type {
  OnchainVaultOperation,
  OnchainVaultTransaction,
  OnchainVaultTransactionStatus,
} from '@prisma/client'
import { Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import { sandboxUpdateLedgerSuccess } from '@/lib/portal/mocks/morphoLocalSandbox'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { lombardMockUpdateLedgerSuccess } from '@/lib/portal/lombard/mocks/lombardLocalMock'
import { verifyMorphoTransactionReceipt } from '@/lib/portal/morphoReceiptVerification'
import { emitMorphoLedgerTerminalSupportLog } from '@/lib/portal/morphoBetaSupportEmit'
import { syncMorphoIntentAfterReceipt, syncMorphoIntentPending } from '@/lib/portal/morphoIntentSync'

const ACTIVE_PENDING_STATUSES: OnchainVaultTransactionStatus[] = ['pending']

export class MorphoVaultLedgerError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'MorphoVaultLedgerError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

export function computePrincipalNetFromLedgerRows(
  rows: Array<{ operation: OnchainVaultOperation; amountRaw: string; status: OnchainVaultTransactionStatus }>,
): bigint {
  let principal = BigInt(0)
  for (const row of rows) {
    if (row.status !== 'success') continue
    const amount = BigInt(row.amountRaw || '0')
    if (row.operation === 'deposit') {
      principal += amount
    } else if (row.operation === 'withdraw') {
      principal -= amount
    }
  }
  if (principal < BigInt(0)) return BigInt(0)
  return principal
}

export async function loadPrincipalNetRaw(args: {
  personId: string
  vaultAddress: string
  chainId?: number
  walletAddress: string
}): Promise<string | null> {
  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      vaultAddress: normalizeVaultAddress(args.vaultAddress),
      chainId: args.chainId ?? MORPHO_CHAIN_ID,
      walletAddress: args.walletAddress.trim().toLowerCase(),
      status: 'success',
      operation: { in: ['deposit', 'withdraw'] },
    },
    select: { operation: true, amountRaw: true, status: true },
  })

  if (rows.length === 0) return null
  return computePrincipalNetFromLedgerRows(rows).toString()
}

export async function assertWithdrawAmountWithinPosition(args: {
  amountRaw: bigint
  assetsInVaultRaw: string
}): Promise<void> {
  const position = BigInt(args.assetsInVaultRaw || '0')
  if (args.amountRaw <= BigInt(0)) {
    throw new MorphoVaultLedgerError('morpho.invalid_amount', 'Montant invalide.')
  }
  if (args.amountRaw > position) {
    throw new MorphoVaultLedgerError(
      'morpho.withdraw_exceeds_position',
      'Le montant demandé dépasse votre position dans le vault.',
    )
  }
}

type CreateLedgerEntryInput = {
  personId: string
  vaultAddress: string
  chainId: number
  chainType?: string
  walletAddress: string
  privyWalletId?: string | null
  operation: OnchainVaultOperation
  amountRaw: string
  assetSymbol: string
  assetDecimals: number
  idempotencyKey: string
  integrationMode: string
  txIndex: number
  groupKey: string
  privyActionId?: string | null
  metadataJson?: Prisma.InputJsonValue | null
}

export async function findIdempotentLedgerGroup(args: {
  personId: string
  vaultAddress: string
  idempotencyKey: string
}): Promise<OnchainVaultTransaction[]> {
  return prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      vaultAddress: normalizeVaultAddress(args.vaultAddress),
      idempotencyKey: args.idempotencyKey,
    },
    orderBy: [{ txIndex: 'asc' }, { operation: 'asc' }],
  })
}

export async function assertNoConcurrentPendingGroup(args: {
  personId: string
  vaultAddress: string
  idempotencyKey: string
}): Promise<OnchainVaultTransaction[]> {
  const existing = await findIdempotentLedgerGroup(args)
  if (existing.length === 0) return existing

  const hasActivePending = existing.some((row) => ACTIVE_PENDING_STATUSES.includes(row.status))
  const allTerminal = existing.every((row) => row.status === 'success' || row.status === 'failed' || row.status === 'reverted')

  if (hasActivePending && !allTerminal) {
    const sameKey = existing.every((row) => row.idempotencyKey === args.idempotencyKey)
    if (sameKey) {
      return existing
    }
    throw new MorphoVaultLedgerError(
      'morpho.concurrent_operation',
      'Une opération identique est déjà en cours.',
      409,
    )
  }

  return existing
}

export async function createMorphoLedgerEntries(
  entries: CreateLedgerEntryInput[],
): Promise<OnchainVaultTransaction[]> {
  const created: OnchainVaultTransaction[] = []
  for (const entry of entries) {
    try {
      const row = await prisma.onchainVaultTransaction.create({
        data: {
          personId: entry.personId,
          vaultAddress: normalizeVaultAddress(entry.vaultAddress),
          chainId: entry.chainId,
          chainType: entry.chainType ?? 'evm',
          walletAddress: entry.walletAddress.trim().toLowerCase(),
          privyWalletId: entry.privyWalletId ?? null,
          operation: entry.operation,
          amountRaw: entry.amountRaw,
          assetSymbol: entry.assetSymbol,
          assetDecimals: entry.assetDecimals,
          idempotencyKey: entry.idempotencyKey,
          integrationMode: entry.integrationMode,
          txIndex: entry.txIndex,
          groupKey: entry.groupKey,
          privyActionId: entry.privyActionId ?? null,
          metadataJson: entry.metadataJson ?? undefined,
          status: 'pending',
        },
      })
      created.push(row)
      if (
        entry.integrationMode === 'direct_morpho' &&
        (entry.operation === 'deposit' || entry.operation === 'withdraw')
      ) {
        void syncMorphoIntentPending({
          personId: entry.personId,
          vaultTransactionId: row.id,
          vaultAddress: entry.vaultAddress,
          chainId: entry.chainId,
          walletAddress: entry.walletAddress,
          operation: entry.operation,
          idempotencyKey: entry.idempotencyKey,
          txIndex: entry.txIndex,
          vaultStatus: 'pending',
        })
      }
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2002') {
        const existing = await prisma.onchainVaultTransaction.findFirst({
          where: {
            personId: entry.personId,
            vaultAddress: normalizeVaultAddress(entry.vaultAddress),
            operation: entry.operation,
            idempotencyKey: entry.idempotencyKey,
            txIndex: entry.txIndex,
          },
        })
        if (existing) {
          created.push(existing)
          continue
        }
      }
      throw error
    }
  }
  return created
}

export async function updateLedgerAfterReceipt(args: {
  ledgerEntryId: string
  personId: string
  txHash: string
  expectedChainId?: number
}): Promise<OnchainVaultTransaction> {
  const entry = await prisma.onchainVaultTransaction.findFirst({
    where: { id: args.ledgerEntryId, personId: args.personId },
  })
  if (!entry) {
    throw new MorphoVaultLedgerError('morpho.ledger_not_found', 'Entrée ledger introuvable.', 404)
  }

  if (entry.status === 'success') {
    return entry
  }

  if (
    isLombardMockEnabled() &&
    entry.integrationMode === LOMBARD_INTEGRATION_MODE
  ) {
    return lombardMockUpdateLedgerSuccess({
      ledgerEntryId: entry.id,
      personId: args.personId,
      txHash: args.txHash,
    })
  }

  if (isMorphoLocalSandboxEnabled()) {
    return sandboxUpdateLedgerSuccess({
      ledgerEntryId: entry.id,
      personId: args.personId,
      txHash: args.txHash,
    })
  }

  let verified
  try {
    verified = await verifyMorphoTransactionReceipt({
      txHash: args.txHash,
      expectedChainId: args.expectedChainId ?? entry.chainId,
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Receipt invalide.'
    return prisma.onchainVaultTransaction.update({
      where: { id: entry.id },
      data: {
        txHash: args.txHash,
        status: 'failed',
        errorMessage: message,
      },
    }).then((updated) => {
      if (
        updated.integrationMode === 'direct_morpho' &&
        (updated.operation === 'deposit' || updated.operation === 'withdraw')
      ) {
        void syncMorphoIntentAfterReceipt({
          personId: updated.personId,
          vaultTransactionId: updated.id,
          txHash: updated.txHash,
          vaultStatus: updated.status,
        })
      }
      emitMorphoLedgerTerminalSupportLog(updated)
      return updated
    })
  }

  const nextStatus: OnchainVaultTransactionStatus =
    verified.status === 'success' ? 'success' : 'reverted'

  const updated = await prisma.onchainVaultTransaction.update({
    where: { id: entry.id },
    data: {
      txHash: verified.txHash,
      blockNumber: verified.blockNumber,
      status: nextStatus,
      errorMessage: nextStatus === 'reverted' ? 'Transaction revert on-chain.' : null,
    },
  })

  if (nextStatus === 'success' && (updated.operation === 'deposit' || updated.operation === 'withdraw')) {
    await syncUserVaultPositionFromLedger({
      personId: updated.personId,
      vaultAddress: updated.vaultAddress,
      chainId: updated.chainId,
      walletAddress: updated.walletAddress,
      assetSymbol: updated.assetSymbol,
      assetDecimals: updated.assetDecimals,
    })
  }

  if (
    updated.integrationMode === 'direct_morpho' &&
    (updated.operation === 'deposit' || updated.operation === 'withdraw')
  ) {
    void syncMorphoIntentAfterReceipt({
      personId: updated.personId,
      vaultTransactionId: updated.id,
      txHash: updated.txHash,
      vaultStatus: updated.status,
    })
  }

  if (nextStatus !== 'success') {
    emitMorphoLedgerTerminalSupportLog(updated)
  }

  return updated
}

export async function syncUserVaultPositionFromLedger(args: {
  personId: string
  vaultAddress: string
  chainId: number
  walletAddress: string
  privyWalletId?: string | null
  assetSymbol: string
  assetDecimals: number
  lastAssetsRaw?: string | null
  lastSharesRaw?: string | null
  costBasisUnknown?: boolean
}): Promise<void> {
  const principalNetRaw = await loadPrincipalNetRaw({
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    chainId: args.chainId,
    walletAddress: args.walletAddress,
  })

  const costBasisUnknown = args.costBasisUnknown ?? principalNetRaw == null

  await prisma.userVaultPosition.upsert({
    where: {
      personId_chainId_vaultAddress_walletAddress: {
        personId: args.personId,
        chainId: args.chainId,
        vaultAddress: normalizeVaultAddress(args.vaultAddress),
        walletAddress: args.walletAddress.trim().toLowerCase(),
      },
    },
    create: {
      personId: args.personId,
      vaultAddress: normalizeVaultAddress(args.vaultAddress),
      chainId: args.chainId,
      chainType: 'evm',
      walletAddress: args.walletAddress.trim().toLowerCase(),
      privyWalletId: args.privyWalletId ?? null,
      assetSymbol: args.assetSymbol,
      assetDecimals: args.assetDecimals,
      principalNetRaw: principalNetRaw ?? '0',
      costBasisUnknown,
      lastAssetsRaw: args.lastAssetsRaw ?? null,
      lastSharesRaw: args.lastSharesRaw ?? null,
      lastSyncedAt: new Date(),
    },
    update: {
      privyWalletId: args.privyWalletId ?? undefined,
      principalNetRaw: principalNetRaw ?? '0',
      costBasisUnknown,
      lastAssetsRaw: args.lastAssetsRaw ?? undefined,
      lastSharesRaw: args.lastSharesRaw ?? undefined,
      lastSyncedAt: new Date(),
    },
  })
}

