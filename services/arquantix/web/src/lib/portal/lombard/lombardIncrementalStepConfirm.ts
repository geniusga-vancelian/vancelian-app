import type { LombardExecutionPhase, LombardPreparedTx } from '@/lib/portal/lombard/lombardTypes'
import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
import type { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'

export type LombardLedgerEntryRef = { id: string }

export type LombardStepConfirmResult = {
  ledgerEntryId: string
  txHash: string
}

type ReceiptLike = Parameters<typeof resolvePortalTransactionReceiptStatus>[0]

export type ExecuteLombardOpenLoanStepsArgs = {
  groupKey: string
  transactions: LombardPreparedTx[]
  ledgerEntries: LombardLedgerEntryRef[]
  sendTransaction: (tx: LombardPreparedTx, index: number) => Promise<{ hash: string }>
  waitForReceipt: (hash: string) => Promise<ReceiptLike | null>
  resolveReceiptStatus: (receipt: ReceiptLike) => 'success' | 'reverted'
  confirmStep: (result: LombardStepConfirmResult) => Promise<void>
  onPhaseChange?: (phase: LombardExecutionPhase) => void
  mapTxPhase?: (operation: LombardPreparedTx['operation']) => LombardExecutionPhase
}

function defaultMapTxPhase(operation: LombardPreparedTx['operation']): LombardExecutionPhase {
  if (operation === 'approve' || operation === 'authorize') return 'authorizing'
  if (operation === 'open_loan') return 'locking'
  return 'preparing'
}

/**
 * Exécute approve/open_loan et confirme chaque step backend immédiatement après receipt.
 * Les steps précédentes restent confirmées si une step ultérieure revert.
 */
export async function executeLombardOpenLoanSteps(
  args: ExecuteLombardOpenLoanStepsArgs,
): Promise<string> {
  const mapPhase = args.mapTxPhase ?? defaultMapTxPhase
  let lastHash: string | null = null

  for (let index = 0; index < args.transactions.length; index += 1) {
    const tx = args.transactions[index]
    const ledgerEntry = args.ledgerEntries[index]
    if (!ledgerEntry) {
      throw new Error('Missing ledger entry for prepared transaction.')
    }

    const phase = mapPhase(tx.operation)
    const isLastTx = index === args.transactions.length - 1
    args.onPhaseChange?.(phase === 'locking' && isLastTx ? 'sending' : phase)

    const { hash } = await args.sendTransaction(tx, index)
    lastHash = hash

    const receipt = await args.waitForReceipt(hash)
    if (!receipt) {
      throw new LombardExecutionError({
        code: 'receipt_timeout',
        operation: tx.operation,
        txHash: hash,
      })
    }

    if (args.resolveReceiptStatus(receipt) !== 'success') {
      await args.confirmStep({ ledgerEntryId: ledgerEntry.id, txHash: hash }).catch(() => null)
      throw new LombardExecutionError({
        code: 'reverted',
        operation: tx.operation,
        txHash: hash,
      })
    }

    if (isLastTx) {
      args.onPhaseChange?.('confirming')
    }
    await args.confirmStep({ ledgerEntryId: ledgerEntry.id, txHash: hash })
  }

  if (!lastHash) {
    throw new Error('No Lombard transaction was executed.')
  }

  return lastHash
}
