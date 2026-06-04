/**
 * Politique d'exécution open_loan — retry invisible (interne, R4).
 */
import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'

/** Pause avant retry invisible open_loan (oracle / mempool). */
export const LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS = 2_000

export function sleepMs(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function delayBeforeInvisibleOpenLoanRetry(): Promise<void> {
  await sleepMs(LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS)
}
import {
  isLombardOpenLoanRetryableFailure,
  type LombardRetryLinkState,
} from '@/lib/portal/lombard/lombardRetryLinking'

export function shouldAttemptInvisibleOpenLoanRetry(
  error: unknown,
  state: LombardRetryLinkState,
): boolean {
  if (!(error instanceof LombardExecutionError)) return false
  if (error.code !== 'reverted') return false
  if (state.hasRetried) return false
  return isLombardOpenLoanRetryableFailure({ operation: error.operation })
}

export class LombardTerminalBorrowError extends Error {
  readonly userCopy = {
    title: "Impossible d'ouvrir l'emprunt",
    lines: [
      "Aucun montant n'a été emprunté.",
      "Votre garantie n'a pas été déposée.",
      'Une nouvelle tentative automatique a déjà été effectuée. Vous pouvez réessayer une fois.',
    ],
  }

  constructor() {
    super("Impossible d'ouvrir l'emprunt")
    this.name = 'LombardTerminalBorrowError'
  }
}

export function toLombardTerminalBorrowError(_error: unknown): LombardTerminalBorrowError {
  return new LombardTerminalBorrowError()
}
