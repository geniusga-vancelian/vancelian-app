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
    assert.equal(swapProcessingStepperIndex('signing'), 2)
    assert.equal(swapProcessingStepperIndex('submitting'), 3)
    assert.equal(swapProcessingStepperIndex('bridging'), 4)
    assert.equal(swapProcessingStepperIndex('completed'), 5)
  })

  it('terminal copy is user-facing only', () => {
    assert.match(SWAP_TERMINAL_FAILURE_COPY.title, /Impossible/)
    for (const line of SWAP_TERMINAL_FAILURE_COPY.lines) {
      assert.doesNotMatch(line, /revert|LI\.FI|lifi|group_key|idempotency/i)
    }
  })

  it('maps raw revert to product copy without jargon', () => {
    const copy = resolveSwapFailureCopy(new Error('tx reverted on chain'))
    assert.equal(copy.title, SWAP_TERMINAL_FAILURE_COPY.title)
    assert.match(copy.lines[0]!, /n’a pas pu être exécuté on-chain/i)
    assert.equal(copy.lines[1], SWAP_TERMINAL_FAILURE_COPY.lines[0])
  })

  it('shows formatted wallet errors to the user', () => {
    const copy = resolveSwapFailureCopy(
      new Error(
        'Swap LI.FI refusé sur Base. L’approbation USDC vers le routeur LI.FI n’a probablement pas abouti — refaites une estimation puis réessayez.',
      ),
    )
    assert.match(copy.lines[0]!, /approbation USDC/i)
    assert.equal(copy.lines[1], SWAP_TERMINAL_FAILURE_COPY.lines[0])
  })

  it('maps quote expiry to product copy without jargon', () => {
    const copy = resolveSwapFailureCopy(
      new Error('Quote expirée — revenez à l’étape montant et refaites une estimation.'),
    )
    assert.match(copy.lines[0]!, /devis a expiré/i)
    assert.doesNotMatch(copy.lines[0]!, /LI\.FI|lifi|revert/i)
  })
})
