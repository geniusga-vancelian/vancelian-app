/** Lombard logical borrow retry linking (Phase 3B-R3). */

export const LOMBARD_MAX_RETRY_ATTEMPTS = 1

export type LombardRetryPrepareContext = {
  logicalBorrowId: string
  retryOfGroupKey?: string | null
  retryAttemptNumber: number
}

export type LombardRetryLinkState = {
  logicalBorrowId: string | null
  failedGroupKeyForRetry: string | null
  /** Retry lié consommé (auto invisible ou manuel post-terminal). */
  hasRetried: boolean
}

export type LombardRetryPrepareMode = 'initial' | 'linked_retry'

export function createLogicalBorrowId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `lombard-logical-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function createInitialLombardRetryLinkState(): LombardRetryLinkState {
  return {
    logicalBorrowId: null,
    failedGroupKeyForRetry: null,
    hasRetried: false,
  }
}

export function resetLombardRetryLinkState(state: LombardRetryLinkState): LombardRetryLinkState {
  return createInitialLombardRetryLinkState()
}

export function buildLombardRetryPrepareContext(args: {
  state: LombardRetryLinkState
  mode: LombardRetryPrepareMode
}): LombardRetryPrepareContext {
  const logicalBorrowId = args.state.logicalBorrowId ?? createLogicalBorrowId()
  const retryOfGroupKey =
    args.mode === 'linked_retry' ? args.state.failedGroupKeyForRetry : null
  const retryAttemptNumber = retryOfGroupKey ? 1 : 0
  return {
    logicalBorrowId,
    retryOfGroupKey,
    retryAttemptNumber,
  }
}

/** @deprecated R4 — retry manuel post-terminal repart de zéro ; gardé pour compat tests. */
export function canAttemptExplicitLombardRetry(state: LombardRetryLinkState): boolean {
  return canAttemptLinkedLombardRetry(state)
}

export function canAttemptLinkedLombardRetry(state: LombardRetryLinkState): boolean {
  return Boolean(state.failedGroupKeyForRetry) && !state.hasRetried
}

export function isLombardOpenLoanRetryableFailure(args: {
  operation: string | null | undefined
}): boolean {
  return (args.operation ?? '').trim().toLowerCase() === 'open_loan'
}

export function applyLombardRetryLinkAfterFailure(args: {
  state: LombardRetryLinkState
  groupKey: string
  operation: string | null | undefined
}): LombardRetryLinkState {
  if (!isLombardOpenLoanRetryableFailure({ operation: args.operation })) {
    return resetLombardRetryLinkState(args.state)
  }
  return {
    ...args.state,
    failedGroupKeyForRetry: args.groupKey,
  }
}

export function applyLombardRetryLinkAfterSuccess(state: LombardRetryLinkState): LombardRetryLinkState {
  return resetLombardRetryLinkState(state)
}

export function markLombardLinkedRetryStarted(state: LombardRetryLinkState): LombardRetryLinkState {
  return {
    ...state,
    hasRetried: true,
  }
}

/** @deprecated alias */
export function markLombardExplicitRetryStarted(state: LombardRetryLinkState): LombardRetryLinkState {
  return markLombardLinkedRetryStarted(state)
}

export function buildLombardPrepareRetryBodyFields(
  context: LombardRetryPrepareContext,
): Record<string, string | number> {
  const body: Record<string, string | number> = {
    logical_borrow_id: context.logicalBorrowId,
    retry_attempt_number: context.retryAttemptNumber,
  }
  if (context.retryOfGroupKey) {
    body.retry_of_group_key = context.retryOfGroupKey
  }
  return body
}
