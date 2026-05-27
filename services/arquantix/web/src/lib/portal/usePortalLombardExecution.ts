'use client'

import { useCallback } from 'react'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import {
  confirmPortalLombardTransactions,
  preparePortalLombardOpenLoan,
} from '@/lib/portal/lombard/lombardClient'
import { bumpLombardPositionsRevision } from '@/lib/portal/lombard/lombardPositionsRefresh'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { generateLombardMockTxHash } from '@/lib/portal/lombard/mocks/lombardMockTxHash'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { buildWalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const RECEIPT_TIMEOUT_MS = 180_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function mapTxPhase(operation: string): LombardExecutionPhase {
  if (operation === 'approve' || operation === 'authorize') return 'authorizing'
  if (operation === 'open_loan') return 'locking'
  return 'preparing'
}

export function usePortalLombardExecution() {
  const { sendPortalTransaction, resolveWallet } = usePortalTxSigner()

  const executeOpenLoan = useCallback(
    async (args: {
      collateral: string
      borrowAmount: string
      walletAddress: string
      targetLtvPercent: number
      idempotencyKey: string
      onPhaseChange?: (phase: LombardExecutionPhase) => void
    }) => {
      args.onPhaseChange?.('preparing')

      const wallet = await resolveWallet(null, { expectedAddress: args.walletAddress })
      if (wallet.address.toLowerCase() !== args.walletAddress.toLowerCase()) {
        throw new Error('Active wallet does not match the selected execution wallet.')
      }

      const walletMetadata = buildWalletSourceMetadata(wallet)

      const prepared = await preparePortalLombardOpenLoan({
        collateral: args.collateral,
        borrowAmount: args.borrowAmount,
        walletAddress: wallet.address,
        targetLtvPercent: args.targetLtvPercent,
        idempotencyKey: args.idempotencyKey,
        walletSource: walletMetadata,
        externalWalletId: wallet.type === 'external_evm' ? wallet.externalWalletId : null,
        privyWalletId: wallet.type === 'privy_embedded' ? wallet.privyWalletId ?? null : null,
      })

      if (prepared.mockExecution) {
        args.onPhaseChange?.('confirming')
        const confirmResults = prepared.ledgerEntries.map((entry) => ({
          ledgerEntryId: entry.id,
          txHash: generateLombardMockTxHash(),
        }))
        await confirmPortalLombardTransactions({
          groupKey: prepared.groupKey,
          results: confirmResults,
        })
        bumpLombardPositionsRevision()
        invalidatePortalCache()
        args.onPhaseChange?.('confirmed')
        return prepared.groupKey
      }

      const client = createBasePublicClient({ side: 'client' })
      const confirmResults: Array<{ ledgerEntryId: string; txHash: string }> = []
      let lastHash: string | null = null

      for (let index = 0; index < prepared.transactions.length; index += 1) {
        const tx = prepared.transactions[index]
        const ledgerEntry = prepared.ledgerEntries[index]
        if (!ledgerEntry) {
          throw new Error('Missing ledger entry for prepared transaction.')
        }

        const phase = mapTxPhase(tx.operation)
        args.onPhaseChange?.(phase === 'locking' && index === prepared.transactions.length - 1 ? 'sending' : phase)

        const { hash } = await sendPortalTransaction(
          {
            chainId: tx.chainId,
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
          throw new Error(formatBaseRpcUserMessage('Transaction confirmation timed out.'))
        }
        if (resolvePortalTransactionReceiptStatus(receipt) !== 'success') {
          throw new Error('On-chain transaction reverted.')
        }

        confirmResults.push({ ledgerEntryId: ledgerEntry.id, txHash: hash })
      }

      args.onPhaseChange?.('confirming')
      await confirmPortalLombardTransactions({
        groupKey: prepared.groupKey,
        results: confirmResults,
      })

      bumpLombardPositionsRevision()
      invalidatePortalCache()

      args.onPhaseChange?.('confirmed')
      return lastHash
    },
    [resolveWallet, sendPortalTransaction],
  )

  return { executeOpenLoan, chainId: VANCELIAN_LOMBARD_V1.chainId }
}

export function lombardExecutionPhaseLabel(phase: LombardExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Creating your loan…'
    case 'authorizing':
      return 'Authorising your guarantee…'
    case 'locking':
      return 'Locking your guarantee…'
    case 'sending':
      return 'Sending USDC to your wallet…'
    case 'confirming':
      return 'Confirming on-chain…'
    case 'confirmed':
      return 'USDC received'
    case 'failed':
      return 'Something went wrong'
    default:
      return 'Processing…'
  }
}

export function isBaseRpcExecutionError(error: unknown): boolean {
  return isBaseRpcTransientError(error)
}
