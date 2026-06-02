import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { buildLombardBorrowRecap } from '@/lib/portal/lombard/lombardBorrowRecap'
import {
  LOMBARD_TERMINAL_FAILURE_COPY,
  lombardProcessingStepperIndex,
  resolveOpenLoanStepSubtext,
} from '@/lib/portal/lombard/lombardProcessingUx'

describe('lombardProcessingUx', () => {
  const recap = buildLombardBorrowRecap({
    marketId: 'm1',
    collateral: 'cbBTC',
    collateralName: 'Coinbase Wrapped BTC',
    targetLtvPercent: 28,
    borrowAmount: '1000',
    borrowAmountRaw: '1000000000',
    guaranteeAmount: '0.01',
    guaranteeAmountRaw: '1000000',
    projectedLtvPercent: 28,
    safetyLevel: 'comfortable',
    safetyLabel: 'Confortable',
    safetyMessage: 'ok',
    maxBorrowAmount: '5000',
    recommendedBorrowAmount: '1000',
    borrowApyPercent: 5,
    liquidationLltvPercent: 77,
    walletGuaranteeBalance: '0.1',
    poweredBy: 'Morpho',
  })

  it('maps phases to product stepper index', () => {
    assert.equal(lombardProcessingStepperIndex('sending'), 2)
    assert.equal(lombardProcessingStepperIndex('confirmed'), 4)
  })

  it('rotates open_loan subtext without blockchain jargon', () => {
    const a = resolveOpenLoanStepSubtext(recap, 0)
    const b = resolveOpenLoanStepSubtext(recap, 1)
    assert.match(a, /Emprunt de/)
    assert.match(b, /Vérification de votre garantie/)
    assert.doesNotMatch(b, /revert|retry|blockchain/i)
  })

  it('terminal copy is user-facing only', () => {
    assert.match(LOMBARD_TERMINAL_FAILURE_COPY.title, /Impossible/)
    assert.equal(LOMBARD_TERMINAL_FAILURE_COPY.lines.length, 2)
    for (const line of LOMBARD_TERMINAL_FAILURE_COPY.lines) {
      assert.doesNotMatch(line, /revert|retryable|group_key|tx_hash/i)
    }
  })
})
