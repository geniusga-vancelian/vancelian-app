import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  applyLombardRetryLinkAfterFailure,
  buildLombardPrepareRetryBodyFields,
  buildLombardRetryPrepareContext,
  canAttemptLinkedLombardRetry,
  createInitialLombardRetryLinkState,
  createLogicalBorrowId,
  markLombardLinkedRetryStarted,
  resetLombardRetryLinkState,
} from './lombardRetryLinking'

describe('lombardRetryLinking', () => {
  it('creates logical borrow id', () => {
    const id = createLogicalBorrowId()
    assert.match(id, /[0-9a-f-]{8,}/i)
  })

  it('initial prepare has retry_attempt_number 0', () => {
    const state = createInitialLombardRetryLinkState()
    const ctx = buildLombardRetryPrepareContext({ state, mode: 'initial' })
    assert.equal(ctx.retryAttemptNumber, 0)
    assert.equal(ctx.retryOfGroupKey, null)
    assert.ok(ctx.logicalBorrowId)
  })

  it('linked retry carries retry_of_group_key and attempt 1', () => {
    const state = {
      logicalBorrowId: 'logical-1',
      failedGroupKeyForRetry: 'group-a',
      hasRetried: false,
    }
    const ctx = buildLombardRetryPrepareContext({ state, mode: 'linked_retry' })
    assert.equal(ctx.logicalBorrowId, 'logical-1')
    assert.equal(ctx.retryOfGroupKey, 'group-a')
    assert.equal(ctx.retryAttemptNumber, 1)
    const body = buildLombardPrepareRetryBodyFields(ctx)
    assert.equal(body.logical_borrow_id, 'logical-1')
    assert.equal(body.retry_of_group_key, 'group-a')
    assert.equal(body.retry_attempt_number, 1)
  })

  it('records failed group key only for open_loan failures', () => {
    const state = createInitialLombardRetryLinkState()
    const next = applyLombardRetryLinkAfterFailure({
      state: { ...state, logicalBorrowId: 'logical-1' },
      groupKey: 'group-a',
      operation: 'open_loan',
    })
    assert.equal(next.failedGroupKeyForRetry, 'group-a')
    const cleared = applyLombardRetryLinkAfterFailure({
      state: { ...state, logicalBorrowId: 'logical-1', failedGroupKeyForRetry: 'group-a' },
      groupKey: 'group-b',
      operation: 'approve',
    })
    assert.equal(cleared.failedGroupKeyForRetry, null)
    assert.equal(cleared.logicalBorrowId, null)
  })

  it('blocks second linked retry after one retry started', () => {
    const state = markLombardLinkedRetryStarted({
      logicalBorrowId: 'logical-1',
      failedGroupKeyForRetry: 'group-a',
      hasRetried: false,
    })
    assert.equal(canAttemptLinkedLombardRetry(state), false)
  })

  it('reset clears retry state', () => {
    const state = resetLombardRetryLinkState({
      logicalBorrowId: 'logical-1',
      failedGroupKeyForRetry: 'group-a',
      hasRetried: true,
    })
    assert.deepEqual(state, createInitialLombardRetryLinkState())
  })
})
