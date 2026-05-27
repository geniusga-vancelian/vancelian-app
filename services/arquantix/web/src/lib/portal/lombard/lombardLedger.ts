import type { Prisma } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import type { LombardPreparedTx, LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import {
  assertNoConcurrentPendingGroup,
  createMorphoLedgerEntries,
  MorphoVaultLedgerError,
} from '@/lib/portal/morphoVaultLedger'

export { MorphoVaultLedgerError as LombardLedgerError }

function mapLombardTxToLedgerOperation(
  txOperation: LombardPreparedTx['operation'],
): 'approve' | 'deposit' | 'withdraw' {
  if (txOperation === 'approve' || txOperation === 'authorize') return 'approve'
  return 'deposit'
}

export async function createLombardLedgerEntries(args: {
  personId: string
  marketId: string
  walletAddress: string
  privyWalletId?: string | null
  idempotencyKey: string
  quote: LombardQuoteResult
  transactions: LombardPreparedTx[]
  walletMetadata?: Prisma.InputJsonValue
}) {
  const groupKey = args.idempotencyKey
  const existing = await assertNoConcurrentPendingGroup({
    personId: args.personId,
    vaultAddress: args.marketId,
    idempotencyKey: args.idempotencyKey,
  })

  if (existing.some((row) => row.status === 'success' && row.operation === 'deposit')) {
    throw new MorphoVaultLedgerError('lombard.already_completed', 'This loan opening was already confirmed.', 409)
  }

  if (existing.length > 0) {
    return existing
  }

  const approveCount = args.transactions.filter(
    (tx) => tx.operation === 'approve' || tx.operation === 'authorize',
  ).length

  return createMorphoLedgerEntries(
    args.transactions.map((tx, index) => {
      const operation = mapLombardTxToLedgerOperation(tx.operation)
      const txIndex = operation === 'approve' ? index : index - approveCount
      return {
        personId: args.personId,
        vaultAddress: normalizeVaultAddress(args.marketId),
        chainId: tx.chainId,
        chainType: 'evm',
        walletAddress: args.walletAddress,
        privyWalletId: args.privyWalletId ?? null,
        operation,
        amountRaw: operation === 'approve' ? '0' : args.quote.borrowAmountRaw,
        assetSymbol: 'USDC',
        assetDecimals: 6,
        idempotencyKey: args.idempotencyKey,
        integrationMode: LOMBARD_INTEGRATION_MODE,
        txIndex: Math.max(0, txIndex),
        groupKey,
        metadataJson: {
          lombard_operation: 'open_loan',
          collateral: args.quote.collateral,
          guarantee_amount_raw: args.quote.guaranteeAmountRaw,
          guarantee_amount: args.quote.guaranteeAmount,
          borrow_amount_raw: args.quote.borrowAmountRaw,
          borrow_amount: args.quote.borrowAmount,
          projected_ltv_percent: args.quote.projectedLtvPercent,
          ...(args.walletMetadata && typeof args.walletMetadata === 'object' ? args.walletMetadata : {}),
        } as Prisma.InputJsonValue,
      }
    }),
  )
}

export async function findLombardLedgerGroup(args: {
  personId: string
  marketId: string
  idempotencyKey: string
}) {
  return prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      vaultAddress: normalizeVaultAddress(args.marketId),
      idempotencyKey: args.idempotencyKey,
      integrationMode: LOMBARD_INTEGRATION_MODE,
    },
    orderBy: [{ txIndex: 'asc' }, { operation: 'asc' }],
  })
}
