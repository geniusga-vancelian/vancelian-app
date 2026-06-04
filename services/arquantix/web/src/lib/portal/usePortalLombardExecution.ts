'use client'

import { useCallback } from 'react'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import {
  confirmPortalLombardTransactions,
  preparePortalLombardOpenLoan,
} from '@/lib/portal/lombard/lombardClient'
import {
  delayBeforeInvisibleOpenLoanRetry,
  LombardTerminalBorrowError,
  shouldAttemptInvisibleOpenLoanRetry,
  toLombardTerminalBorrowError,
} from '@/lib/portal/lombard/lombardOpenLoanExecutionPolicy'
import { bumpLombardPositionsRevision } from '@/lib/portal/lombard/lombardPositionsRefresh'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import type { LombardExecutionPhase } from '@/lib/portal/lombard/lombardTypes'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import {
  applyLombardRetryLinkAfterFailure,
  buildLombardRetryPrepareContext,
  createInitialLombardRetryLinkState,
  createLogicalBorrowId,
  markLombardLinkedRetryStarted,
} from '@/lib/portal/lombard/lombardRetryLinking'
import { executeLombardOpenLoanSteps } from '@/lib/portal/lombard/lombardIncrementalStepConfirm'
import { generateLombardMockTxHash } from '@/lib/portal/lombard/mocks/lombardMockTxHash'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { buildWalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const RECEIPT_TIMEOUT_MS = 180_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `lombard-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
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
      onPhaseChange?: (phase: LombardExecutionPhase) => void
      /** Appelé quand un retry open_loan invisible démarre (reste étape 3). */
      onInvisibleRetry?: () => void
    }) => {
      args.onPhaseChange?.('preparing')

      const wallet = await resolveWallet(null, { expectedAddress: args.walletAddress })
      if (wallet.address.toLowerCase() !== args.walletAddress.toLowerCase()) {
        throw new LombardTerminalBorrowError()
      }

      const walletMetadata = buildWalletSourceMetadata(wallet)
      const linkState = {
        ...createInitialLombardRetryLinkState(),
        logicalBorrowId: createLogicalBorrowId(),
      }

      let lastPreparedGroupKey: string | null = null

      const runAttempt = async (mode: 'initial' | 'linked_retry') => {
        const retryLink = buildLombardRetryPrepareContext({ state: linkState, mode })
        const idempotencyKey = createIdempotencyKey()

        const prepared = await preparePortalLombardOpenLoan({
          collateral: args.collateral,
          borrowAmount: args.borrowAmount,
          walletAddress: wallet.address,
          targetLtvPercent: args.targetLtvPercent,
          idempotencyKey,
          retryLink,
          walletSource: walletMetadata,
          externalWalletId: wallet.type === 'external_evm' ? wallet.externalWalletId : null,
          privyWalletId: wallet.type === 'privy_embedded' ? wallet.privyWalletId ?? null : null,
        })
        lastPreparedGroupKey = prepared.groupKey

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
          return prepared.groupKey
        }

        const client = createBasePublicClient({ side: 'client' })

        await executeLombardOpenLoanSteps({
          groupKey: prepared.groupKey,
          transactions: prepared.transactions,
          ledgerEntries: prepared.ledgerEntries,
          mapTxPhase,
          onPhaseChange: args.onPhaseChange,
          sendTransaction: async (tx) => {
            const sent = await sendPortalTransaction(
              {
                chainId: tx.chainId,
                to: tx.to as `0x${string}`,
                data: tx.data as `0x${string}`,
                value: tx.value,
              },
              wallet,
            )
            return { hash: sent.hash }
          },
          waitForReceipt: async (hash) => {
            const started = Date.now()
            while (Date.now() - started < RECEIPT_TIMEOUT_MS) {
              const receipt = await client
                .getTransactionReceipt({ hash: hash as `0x${string}` })
                .catch(() => null)
              if (receipt) return receipt
              await sleep(3_000)
            }
            return null
          },
          resolveReceiptStatus: resolvePortalTransactionReceiptStatus,
          confirmStep: async (result) => {
            await confirmPortalLombardTransactions({
              groupKey: prepared.groupKey,
              results: [result],
            })
          },
        })

        return prepared.groupKey
      }

      try {
        const result = await runAttempt('initial')
        bumpLombardPositionsRevision()
        invalidatePortalCache()
        args.onPhaseChange?.('confirmed')
        return result
      } catch (error) {
        if (
          lastPreparedGroupKey &&
          shouldAttemptInvisibleOpenLoanRetry(error, linkState)
        ) {
          Object.assign(
            linkState,
            applyLombardRetryLinkAfterFailure({
              state: linkState,
              groupKey: lastPreparedGroupKey,
              operation: 'open_loan',
            }),
          )
          Object.assign(linkState, markLombardLinkedRetryStarted(linkState))
          args.onInvisibleRetry?.()
          args.onPhaseChange?.('sending')
          await delayBeforeInvisibleOpenLoanRetry()
          try {
            const retryResult = await runAttempt('linked_retry')
            bumpLombardPositionsRevision()
            invalidatePortalCache()
            args.onPhaseChange?.('confirmed')
            return retryResult
          } catch {
            throw new LombardTerminalBorrowError()
          }
        }
        throw toLombardTerminalBorrowError(error)
      }
    },
    [resolveWallet, sendPortalTransaction],
  )

  return { executeOpenLoan, chainId: VANCELIAN_LOMBARD_V1.chainId }
}

export function lombardExecutionPhaseLabel(phase: LombardExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Préparation de votre emprunt…'
    case 'authorizing':
      return 'Autorisation de la garantie…'
    case 'locking':
      return 'Dépôt de la garantie…'
    case 'sending':
      return "Ouverture de l'emprunt…"
    case 'confirming':
      return 'Réception des fonds…'
    case 'confirmed':
      return 'USDC reçus'
    case 'failed':
      return "Impossible d'ouvrir l'emprunt"
    default:
      return 'Transaction en cours…'
  }
}

export function isBaseRpcExecutionError(error: unknown): boolean {
  return isBaseRpcTransientError(error)
}

export {
  formatLombardExecutionErrorMessage,
  LombardExecutionError,
  resolveLombardExecutionFailure,
} from '@/lib/portal/lombard/lombardExecutionError'
export { LombardTerminalBorrowError } from '@/lib/portal/lombard/lombardOpenLoanExecutionPolicy'
