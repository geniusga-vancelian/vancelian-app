import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
import {
  createInitialLombardRetryLinkState,
  markLombardLinkedRetryStarted,
} from '@/lib/portal/lombard/lombardRetryLinking'
import {
  buildLombardTerminalFailureCopy,
  isLombardLinkedOpenLoanRetryFailure,
  isLombardPrepareRetryableError,
  LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS,
  LombardTerminalBorrowError,
  shouldAttemptInvisibleOpenLoanRetry,
  toLombardTerminalBorrowError,
} from '@/lib/portal/lombard/lombardOpenLoanExecutionPolicy'

describe('lombardOpenLoanExecutionPolicy', () => {
  it('allows invisible retry on open_loan revert before retry consumed', () => {
    const error = new LombardExecutionError({
      code: 'reverted',
      operation: 'open_loan',
    })
    assert.equal(
      shouldAttemptInvisibleOpenLoanRetry(error, createInitialLombardRetryLinkState()),
      true,
    )
  })

  it('allows invisible retry on approve receipt timeout', () => {
    const error = new LombardExecutionError({
      code: 'receipt_timeout',
      operation: 'approve',
    })
    assert.equal(
      shouldAttemptInvisibleOpenLoanRetry(error, createInitialLombardRetryLinkState()),
      true,
    )
  })

  it('allows invisible retry on prepare simulation failure', () => {
    const error = new Error(
      'Le réseau refuse cette ouverture d’emprunt pour l’instant. Réessayez dans quelques instants.',
    )
    assert.equal(
      shouldAttemptInvisibleOpenLoanRetry(error, createInitialLombardRetryLinkState()),
      true,
    )
  })

  it('blocks invisible retry after linked retry consumed', () => {
    const error = new LombardExecutionError({
      code: 'reverted',
      operation: 'open_loan',
    })
    const state = markLombardLinkedRetryStarted({
      logicalBorrowId: 'x',
      failedGroupKeyForRetry: 'group-a',
      hasRetried: false,
    })
    assert.equal(shouldAttemptInvisibleOpenLoanRetry(error, state), false)
  })

  it('detects linked open_loan retry failures', () => {
    const error = new LombardExecutionError({
      code: 'reverted',
      operation: 'open_loan',
    })
    assert.equal(isLombardLinkedOpenLoanRetryFailure(error), true)
    assert.equal(
      isLombardLinkedOpenLoanRetryFailure(
        new LombardExecutionError({ code: 'reverted', operation: 'approve' }),
      ),
      false,
    )
  })

  it('detects prepare retryable errors', () => {
    assert.equal(
      isLombardPrepareRetryableError(
        new Error('Le réseau refuse cette ouverture d’emprunt pour l’instant.'),
      ),
      true,
    )
    assert.equal(isLombardPrepareRetryableError(new Error('Session expirée.')), false)
  })

  it('exposes invisible retry backoff', () => {
    assert.equal(LOMBARD_OPEN_LOAN_INVISIBLE_RETRY_DELAY_MS, 5_000)
  })

  it('builds terminal copy with and without auto retry', () => {
    const withRetry = buildLombardTerminalFailureCopy({ autoRetryAttempted: true })
    const withoutRetry = buildLombardTerminalFailureCopy({ autoRetryAttempted: false })
    assert.match(withRetry.lines[2] ?? '', /tentative automatique/i)
    assert.match(withoutRetry.lines[2] ?? '', /recommencer/i)
    assert.doesNotMatch(withoutRetry.lines[2] ?? '', /tentative automatique/i)
  })

  it('maps terminal errors to public copy only', () => {
    const err = toLombardTerminalBorrowError(
      new LombardExecutionError({ code: 'reverted', operation: 'open_loan', txHash: '0xabc' }),
      { autoRetryAttempted: true },
    )
    assert.ok(err instanceof LombardTerminalBorrowError)
    assert.equal(err.autoRetryAttempted, true)
    assert.doesNotMatch(err.message, /revert|0x/i)
  })
})
