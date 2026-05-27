import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  clampLombardTargetLtvPercent,
  lombardLtvRiskLabelFr,
  lombardTargetLtvRatio,
  LOMBARD_MAX_USER_LTV_PERCENT,
  maxBorrowAmountHumanAtTargetLtv,
  resolveLombardLtvRiskTone,
} from '@/lib/portal/lombard/lombardBorrowLtv'

describe('lombardBorrowLtv', () => {
  it('clampLombardTargetLtvPercent bounds 0–70', () => {
    assert.equal(clampLombardTargetLtvPercent(-5), 0)
    assert.equal(clampLombardTargetLtvPercent(35.7), 36)
    assert.equal(clampLombardTargetLtvPercent(100), LOMBARD_MAX_USER_LTV_PERCENT)
  })

  it('maxBorrowAmountHumanAtTargetLtv scales from absolute max at 70%', () => {
    assert.equal(
      maxBorrowAmountHumanAtTargetLtv({ absoluteMaxBorrowHuman: '7000', targetLtvPercent: 0 }),
      '0',
    )
    assert.equal(
      maxBorrowAmountHumanAtTargetLtv({ absoluteMaxBorrowHuman: '7000', targetLtvPercent: 35 }),
      '3500',
    )
    assert.equal(
      maxBorrowAmountHumanAtTargetLtv({ absoluteMaxBorrowHuman: '7000', targetLtvPercent: 70 }),
      '7000',
    )
  })

  it('lombardTargetLtvRatio converts percent to ratio', () => {
    assert.equal(lombardTargetLtvRatio(35), 0.35)
    assert.equal(lombardTargetLtvRatio(70), 0.7)
  })

  it('resolveLombardLtvRiskTone maps health zones', () => {
    assert.equal(resolveLombardLtvRiskTone(0), 'idle')
    assert.equal(resolveLombardLtvRiskTone(40), 'safe')
    assert.equal(resolveLombardLtvRiskTone(55), 'balanced')
    assert.equal(resolveLombardLtvRiskTone(65), 'risky')
  })

  it('lombardLtvRiskLabelFr returns French labels', () => {
    assert.equal(lombardLtvRiskLabelFr(0), 'Choisissez votre LTV')
    assert.equal(lombardLtvRiskLabelFr(40), 'Prudent')
    assert.equal(lombardLtvRiskLabelFr(55), 'Équilibré')
    assert.equal(lombardLtvRiskLabelFr(65), 'Élevé')
  })
})
