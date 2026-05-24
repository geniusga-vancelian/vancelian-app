import type { OnchainVaultTransaction } from '@prisma/client'

import { logMorphoSupportEvent } from '@/lib/portal/morphoBetaSupportLog'
import { isSignificantMismatchDelta } from '@/lib/portal/morphoVaultMonitoring'

export function emitMorphoLedgerTerminalSupportLog(entry: Pick<
  OnchainVaultTransaction,
  'id' | 'personId' | 'vaultAddress' | 'operation' | 'status' | 'txHash' | 'errorMessage'
>): void {
  if (entry.status === 'success' || entry.status === 'pending') return

  const isWithdraw = entry.operation === 'withdraw'
  const code =
    entry.status === 'reverted'
      ? 'morpho.tx_reverted'
      : isWithdraw
        ? 'morpho.withdraw_failed'
        : entry.operation === 'deposit'
          ? 'morpho.deposit_failed'
          : 'morpho.tx_failed'

  logMorphoSupportEvent({
    code,
    level: entry.status === 'reverted' ? 'warning' : 'critical',
    message: entry.errorMessage ?? `Transaction Morpho ${entry.status}.`,
    personId: entry.personId,
    vaultAddress: entry.vaultAddress,
    txHash: entry.txHash,
    ledgerEntryId: entry.id,
    metadata: { operation: entry.operation, status: entry.status },
  })
}

export function emitMorphoReconciliationMismatchLog(args: {
  personId: string
  vaultAddress: string
  walletAddress: string
  status: string
  deltaAssetsRaw: string | null
}): void {
  if (args.status !== 'mismatch' || !isSignificantMismatchDelta(args.deltaAssetsRaw)) return

  logMorphoSupportEvent({
    code: 'morpho.reconciliation_mismatch',
    level: 'critical',
    message: 'Mismatch réconciliation Morpho au-dessus du seuil d’alerte.',
    personId: args.personId,
    vaultAddress: args.vaultAddress,
    deltaAssetsRaw: args.deltaAssetsRaw,
    metadata: { walletAddress: args.walletAddress, status: args.status },
  })
}

export function emitMorphoStalePendingSupportLogs(
  pendingTxs: Array<{
    id: string
    personId: string
    vaultAddress: string
    operation: string
    createdAt: Date | string
    txHash?: string | null
  }>,
): void {
  for (const tx of pendingTxs) {
    logMorphoSupportEvent({
      code: 'morpho.tx_pending_stale',
      level: 'warning',
      message: 'Transaction Morpho pending au-delà du seuil de surveillance.',
      personId: tx.personId,
      vaultAddress: tx.vaultAddress,
      txHash: tx.txHash ?? null,
      ledgerEntryId: tx.id,
      metadata: { operation: tx.operation, createdAt: String(tx.createdAt) },
    })
  }
}
