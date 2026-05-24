'use client'

import { useCallback } from 'react'
import { useCreateWallet, usePrivy, useSendTransaction, useWallets } from '@privy-io/react-auth'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import {
  confirmPortalMorphoTransactions,
  preparePortalMorphoTransactions,
} from '@/lib/portal/morphoVaultClient'
import { resolvePortalSwapSigningWallet } from '@/lib/portal/resolvePortalSwapSigningWallet'
import { normalizeSwapTxValue, normalizeTxHash } from '@/lib/portal/swapTxFormat'

const RECEIPT_TIMEOUT_MS = 180_000

export type PortalMorphoExecutionPhase =
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

export function usePortalMorphoVaultExecution() {
  const { ready, authenticated, user } = usePrivy()
  const { sendTransaction } = useSendTransaction()
  const { wallets } = useWallets()
  const { createWallet } = useCreateWallet()

  const execute = useCallback(
    async (args: {
      vaultAddress: string
      operation: 'deposit' | 'withdraw'
      amount: string
      idempotencyKey: string
      onPhaseChange?: (phase: PortalMorphoExecutionPhase) => void
    }) => {
      args.onPhaseChange?.('preparing')

      const wallet = await resolvePortalSwapSigningWallet({
        ready,
        authenticated,
        user,
        wallets,
        createWallet: async () => {
          const created = await createWallet()
          return { address: created.address }
        },
      })

      if (wallet.switchChain) {
        try {
          await wallet.switchChain(MORPHO_CHAIN_ID)
        } catch {
          /* déjà sur Base ou switch géré par Privy */
        }
      }

      const prepared = await preparePortalMorphoTransactions({
        vaultAddress: args.vaultAddress,
        walletAddress: wallet.address,
        operation: args.operation,
        amount: args.amount,
        idempotencyKey: args.idempotencyKey,
      })

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

        const { hash } = await sendTransaction(
          {
            chainId: tx.chainId,
            to: tx.to as `0x${string}`,
            data: tx.data as `0x${string}`,
            value: normalizeSwapTxValue(tx.value),
          },
          {
            address: wallet.address,
            sponsor: true,
            uiOptions: { showWalletUIs: false },
          },
        )
        lastHash = normalizeTxHash(hash)

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
          await confirmPortalMorphoTransactions({
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
      const confirmation = await confirmPortalMorphoTransactions({
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
    [authenticated, createWallet, ready, sendTransaction, user, wallets],
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
