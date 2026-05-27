import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertLombardUserLtvWithinCap,
  lombardSafetyDetails,
  lombardSliderLabel,
  resolveLombardSafetyLevel,
} from '@/lib/portal/lombard/lombardHealth'

describe('lombardHealth', () => {
  it('resolveLombardSafetyLevel — zones', () => {
    assert.equal(resolveLombardSafetyLevel(0.42), 'comfortable')
    assert.equal(resolveLombardSafetyLevel(0.55), 'monitor')
    assert.equal(resolveLombardSafetyLevel(0.65), 'risky')
    assert.equal(resolveLombardSafetyLevel(0.75), 'blocked')
  })

  it('lombardSafetyDetails — labels', () => {
    const row = lombardSafetyDetails(0.48)
    assert.equal(row.level, 'comfortable')
    assert.equal(row.label, 'Comfortable')
  })

  it('lombardSliderLabel', () => {
    assert.equal(lombardSliderLabel(0.4), 'Safe')
    assert.equal(lombardSliderLabel(0.55), 'Balanced')
    assert.equal(lombardSliderLabel(0.68), 'Risky')
  })

  it('assertLombardUserLtvWithinCap blocks above 70%', () => {
    assert.throws(() => assertLombardUserLtvWithinCap(0.71, 0.7))
    assert.doesNotThrow(() => assertLombardUserLtvWithinCap(0.69, 0.7))
  })
})
