/**
 * Politique d'exécution open_loan — retry invisible (interne, R4).
 */
import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
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
