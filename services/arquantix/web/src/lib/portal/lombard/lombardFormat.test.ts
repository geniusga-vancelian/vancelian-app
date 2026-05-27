import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatLombardTokenAmount,
  lltvWadToPercent,
  parseLombardHumanAmountToRaw,
  rawToLombardHumanAmount,
} from '@/lib/portal/lombard/lombardFormat'

describe('lombardFormat', () => {
  it('parse and format USDC amounts', () => {
    const raw = parseLombardHumanAmountToRaw('15000.5', 6)
    assert.equal(raw, BigInt('15000500000'))
    assert.equal(formatLombardTokenAmount(raw, 6), '15000.5')
  })

  it('parse cbBTC amounts', () => {
    const raw = parseLombardHumanAmountToRaw('0.25', 8)
    assert.equal(raw, BigInt('25000000'))
    assert.equal(rawToLombardHumanAmount(raw, 8), '0.25')
  })

  it('lltvWadToPercent', () => {
    assert.equal(lltvWadToPercent(BigInt('860000000000000000')), 86)
  })
})
