import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  SWAP_TERMINAL_FAILURE_COPY,
  resolveSwapFailureCopy,
  swapProcessingStepperIndex,
} from '@/components/portal/transaction/mappers/swapSteps'

describe('swapSteps', () => {
  it('maps phases to product stepper index', () => {
    assert.equal(swapProcessingStepperIndex('preparing'), 0)
    assert.equal(swapProcessingStepperIndex('approving'), 1)
    assert.equal(swapProcessingStepperIndex('signing'), 1)
    assert.equal(swapProcessingStepperIndex('submitting'), 2)
    assert.equal(swapProcessingStepperIndex('bridging'), 3)
    assert.equal(swapProcessingStepperIndex('completed'), 4)
  })

  it('terminal copy is user-facing only', () => {
    assert.match(SWAP_TERMINAL_FAILURE_COPY.title, /Unable/)
    for (const line of SWAP_TERMINAL_FAILURE_COPY.lines) {
      assert.doesNotMatch(line, /revert|LI\.FI|lifi|group_key|idempotency/i)
    }
  })

  it('sanitizes blockchain jargon in failure copy', () => {
    const copy = resolveSwapFailureCopy(new Error('tx reverted on chain'))
    assert.equal(copy.title, SWAP_TERMINAL_FAILURE_COPY.title)
    assert.deepEqual(copy.lines, SWAP_TERMINAL_FAILURE_COPY.lines)
  })

  it('maps quote expiry to product copy without jargon', () => {
    const copy = resolveSwapFailureCopy(
      new Error('Quote expirée — revenez à l’étape montant et refaites une estimation.'),
    )
    assert.match(copy.lines[0]!, /quote has expired/i)
    assert.doesNotMatch(copy.lines[0]!, /LI\.FI|lifi|revert/i)
  })
})
