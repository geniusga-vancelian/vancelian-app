import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  classifySwapError,
  SwapExecutionError,
  userMessageForSwapFailureCode,
} from '@/lib/portal/swapFailure'

describe('swapFailure', () => {
  it('maps user rejected to approval code in approval phase', () => {
    const err = classifySwapError(new Error('User rejected the request'), 'approval', {
      approvalPhase: true,
    })
    assert.equal(err.code, 'user_rejected_approval')
    assert.equal(err.userMessage, userMessageForSwapFailureCode('user_rejected_approval'))
  })

  it('maps wallet mismatch message', () => {
    const err = classifySwapError(new Error('swap.wallet_mismatch'), 'signing')
    assert.equal(err.code, 'wallet_mismatch')
  })

  it('maps AbortSignal timeout to rpc_error', () => {
    const err = classifySwapError(new Error('signal timed out'), 'confirm_execute')
    assert.equal(err.code, 'rpc_error')
    assert.equal(err.userMessage, userMessageForSwapFailureCode('rpc_error'))
  })

  it('preserves SwapExecutionError', () => {
    const original = new SwapExecutionError({
      code: 'insufficient_funds',
      failurePhase: 'signing',
      technicalMessage: 'transfer_from_failed',
    })
    assert.equal(classifySwapError(original, 'signing'), original)
  })
})
