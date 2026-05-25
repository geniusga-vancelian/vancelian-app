import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { getLedgityBetaLimits } from '@/lib/portal/ledgity/ledgityConfig'

describe('ledgity live limits defaults', () => {
  it('defaults to low live caps (10 / 50 / 500 stablecoin units)', () => {
    const limits = getLedgityBetaLimits()
    assert.equal(limits.maxDepositRaw, BigInt(10_000_000))
    assert.equal(limits.maxUserExposureRaw, BigInt(50_000_000))
    assert.equal(limits.maxGlobalExposureRaw, BigInt(500_000_000))
  })
})
