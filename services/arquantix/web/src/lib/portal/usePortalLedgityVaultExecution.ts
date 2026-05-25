'use client'

import { useCallback } from 'react'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import { LEDGITY_CHAIN_ID } from '@/lib/portal/ledgity/ledgityConstants'
import {
  confirmPortalLedgityTransactions,
  preparePortalLedgityTransactions,
} from '@/lib/portal/ledgity/ledgityVaultClient'
import { buildWalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const RECEIPT_TIMEOUT_MS = 180_000

export type PortalLedgityExecutionPhase =
  | 'idle'
  | 'preparing'
  | 'approval_pending'
  | 'deposit_pending'
  | 'withdraw_pending'
  | 'confirming'
  | 'confirmed'
  | 'failed'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function usePortalLedgityVaultExecution() {
  const { sendPortalTransaction, resolveWallet } = usePortalTxSigner()

  const execute = useCallback(
    async (args: {
      vaultAddress: string
      operation: 'deposit' | 'withdraw'
      amount: string
      idempotencyKey: string
      onPhaseChange?: (phase: PortalLedgityExecutionPhase) => void
    }) => {
      args.onPhaseChange?.('preparing')

      const wallet = await resolveWallet()
      const walletMetadata = buildWalletSourceMetadata(wallet)

      const prepared = await preparePortalLedgityTransactions({
        vaultAddress: args.vaultAddress,
        walletAddress: wallet.address,
        operation: args.operation,
        amount: args.amount,
        idempotencyKey: args.idempotencyKey,
        walletSource: walletMetadata,
        externalWalletId: wallet.type === 'external_evm' ? wallet.externalWalletId : null,
        privyWalletId: wallet.type === 'privy_embedded' ? wallet.privyWalletId ?? null : null,
      })

      if (prepared.serverCompleted) {
        args.onPhaseChange?.('confirmed')
        return prepared.ledgerEntries[0]?.id ?? null
      }

      const client = createBasePublicClient({ side: 'client' })

      const confirmResults: Array<{ ledgerEntryId: string; txHash: string }> = []
      let lastHash: string | null = null

      for (let index = 0; index < prepared.transactions.length; index += 1) {
        const tx = prepared.transactions[index]
        const ledgerEntry = prepared.ledgerEntries[index]
        if (!ledgerEntry) {
          throw new Error('Entrée ledger manquante pour la transaction préparée.')
        }

        if (tx.operation === 'approve') {
          args.onPhaseChange?.('approval_pending')
        } else if (args.operation === 'deposit') {
          args.onPhaseChange?.('deposit_pending')
        } else {
          args.onPhaseChange?.('withdraw_pending')
        }

        const { hash } = await sendPortalTransaction(
          {
            chainId: tx.chainId ?? LEDGITY_CHAIN_ID,
            to: tx.to as `0x${string}`,
            data: tx.data as `0x${string}`,
            value: tx.value,
          },
          wallet,
        )
        lastHash = hash

        const started = Date.now()
        let receipt = null as Awaited<ReturnType<typeof client.getTransactionReceipt>> | null
        while (Date.now() - started < RECEIPT_TIMEOUT_MS) {
          receipt = await client.getTransactionReceipt({ hash: lastHash as `0x${string}` }).catch(() => null)
          if (receipt) break
          await sleep(3_000)
        }

        if (!receipt) {
          args.onPhaseChange?.('failed')
          throw new Error('Receipt introuvable — transaction non confirmée.')
        }

        if (receipt.status !== 'success') {
          args.onPhaseChange?.('failed')
          await confirmPortalLedgityTransactions({
            groupKey: prepared.groupKey,
            results: [{ ledgerEntryId: ledgerEntry.id, txHash: lastHash, status: 'reverted' }],
          }).catch(() => null)
          throw new Error('Transaction revert on-chain.')
        }

        if (receipt.blockNumber == null) {
          args.onPhaseChange?.('failed')
          throw new Error('Numéro de bloc absent du receipt.')
        }

        confirmResults.push({ ledgerEntryId: ledgerEntry.id, txHash: lastHash })
      }

      args.onPhaseChange?.('confirming')
      const confirmation = await confirmPortalLedgityTransactions({
        groupKey: prepared.groupKey,
        results: confirmResults.map((row) => ({
          ledgerEntryId: row.ledgerEntryId,
          txHash: row.txHash,
          status: 'success',
        })),
      })

      if (!confirmation.confirmed || confirmation.failed) {
        args.onPhaseChange?.('failed')
        throw new Error('Confirmation ledger échouée.')
      }

      args.onPhaseChange?.('confirmed')
      return lastHash
    },
    [resolveWallet, sendPortalTransaction],
  )

  const executeWithFriendlyErrors = useCallback(
    async (args: Parameters<typeof execute>[0]) => {
      try {
        return await execute(args)
      } catch (error) {
        if (isBaseRpcTransientError(error)) {
          throw new Error(formatBaseRpcUserMessage(error))
        }
        throw error
      }
    },
    [execute],
  )

  return { execute: executeWithFriendlyErrors }
}
