/**
 * Politique d'exécution open_loan — retry invisible (interne, R4).
 */
import type { TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'
import { isBaseRpcTransientError } from '@/lib/blockchain/baseRpcErrors'
import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
import {
  buildPrepareBlockedTerminalCopy,
  LombardPrepareBlockedError,
} from '@/lib/portal/lombard/lombardPrepareFailure'
import {
  isLombardOpenLoanRetryableFailure,
  type LombardRetryLinkState,
} from '@/lib/portal/lombard/lombardRetryLinking'

/** Pause avant retry invisible (oracle Morpho / mempool Base). */
export const LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS = 5_000

export function sleepMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function delayBeforeInvisibleOpenLoanRetry(): Promise<void> {
  await sleepMs(LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS)
}

const PREPARE_RETRY_MESSAGE_MARKERS = [
  'réseau refuse',
  'réessayez dans quelques instants',
  'temporairement indisponible',
  'oracle',
  'pricing is temporarily unavailable',
] as const

export function isLombardPrepareRetryableError(error: unknown): boolean {
  if (error instanceof LombardPrepareBlockedError) {
    return (
      error.code === 'lombard.open_loan_simulation_failed' ||
      error.code === 'lombard.prepare_timeout' ||
      error.code === 'lombard.prepare_failed' ||
      error.code === 'lombard.base_rpc_busy' ||
      isBaseRpcTransientError(error.message)
    )
  }
  if (!(error instanceof Error)) return false
  if (isBaseRpcTransientError(error)) return true
  const haystack = error.message.toLowerCase()
  return PREPARE_RETRY_MESSAGE_MARKERS.some((marker) => haystack.includes(marker))
}

export function isLombardLinkedOpenLoanRetryFailure(error: unknown): boolean {
  return (
    error instanceof LombardExecutionError &&
    error.code === 'reverted' &&
    isLombardOpenLoanRetryableFailure({ operation: error.operation })
  )
}

export function shouldAttemptInvisibleOpenLoanRetry(
  error: unknown,
  state: LombardRetryLinkState,
): boolean {
  if (state.hasRetried) return false

  if (error instanceof LombardExecutionError) {
    if (error.code !== 'reverted' && error.code !== 'receipt_timeout') return false
    return true
  }

  return isLombardPrepareRetryableError(error)
}

export function buildLombardTerminalFailureCopy(args: {
  autoRetryAttempted: boolean
}): TransactionTerminalFailureCopy {
  if (args.autoRetryAttempted) {
    return {
      title: "Impossible d'ouvrir l'emprunt",
      lines: [
        "Aucun montant n'a été emprunté.",
        "Votre garantie n'a pas été déposée.",
        'Une nouvelle tentative automatique a déjà été effectuée. Voulez-vous recommencer ?',
      ],
    }
  }

  return {
    title: "Impossible d'ouvrir l'emprunt",
    lines: [
      "Aucun montant n'a été emprunté.",
      "Votre garantie n'a pas été déposée.",
      'Le marché ou le réseau a refusé la transaction. Voulez-vous recommencer ?',
    ],
  }
}

export class LombardTerminalBorrowError extends Error {
  readonly autoRetryAttempted: boolean
  readonly userCopy: TransactionTerminalFailureCopy

  constructor(args?: { autoRetryAttempted?: boolean; userCopy?: TransactionTerminalFailureCopy }) {
    super("Impossible d'ouvrir l'emprunt")
    this.name = 'LombardTerminalBorrowError'
    this.autoRetryAttempted = args?.autoRetryAttempted ?? false
    this.userCopy =
      args?.userCopy ??
      buildLombardTerminalFailureCopy({
        autoRetryAttempted: this.autoRetryAttempted,
      })
  }
}

export function toLombardTerminalBorrowError(
  error: unknown,
  args?: { autoRetryAttempted?: boolean },
): LombardTerminalBorrowError {
  if (error instanceof LombardPrepareBlockedError) {
    return new LombardTerminalBorrowError({
      autoRetryAttempted: args?.autoRetryAttempted ?? false,
      userCopy: buildPrepareBlockedTerminalCopy({
        message: error.message,
        autoRetryAttempted: args?.autoRetryAttempted,
      }),
    })
  }
  return new LombardTerminalBorrowError(args)
}
