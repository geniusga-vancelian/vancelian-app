import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { lombardBorrowStepperIndex, lombardBorrowStepperState } from '@/lib/portal/lombard/lombardBorrowRecap'

describe('lombardBorrowRecap stepper', () => {
  it('maps execution phases to step indices', () => {
    assert.equal(lombardBorrowStepperIndex('authorizing'), 0)
    assert.equal(lombardBorrowStepperIndex('locking'), 1)
    assert.equal(lombardBorrowStepperIndex('sending'), 2)
    assert.equal(lombardBorrowStepperIndex('confirming'), 3)
    assert.equal(lombardBorrowStepperIndex('confirmed'), 4)
  })

  it('marks prior steps done while current is in progress', () => {
    assert.equal(lombardBorrowStepperState(0, 2), 'done')
    assert.equal(lombardBorrowStepperState(2, 2), 'current')
    assert.equal(lombardBorrowStepperState(3, 2), 'pending')
  })
})
