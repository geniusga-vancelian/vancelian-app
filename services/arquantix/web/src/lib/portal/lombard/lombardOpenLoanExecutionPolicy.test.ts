import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
import {
  createInitialLombardRetryLinkState,
  markLombardLinkedRetryStarted,
} from '@/lib/portal/lombard/lombardRetryLinking'
import {
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

  it('maps terminal errors to public copy only', () => {
    const err = toLombardTerminalBorrowError(
      new LombardExecutionError({ code: 'reverted', operation: 'open_loan', txHash: '0xabc' }),
    )
    assert.ok(err instanceof LombardTerminalBorrowError)
    assert.doesNotMatch(err.message, /revert|0x/i)
  })
})
