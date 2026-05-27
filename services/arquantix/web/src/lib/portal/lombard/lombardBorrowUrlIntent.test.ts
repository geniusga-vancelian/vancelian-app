import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { parsePortalBorrowUrlIntent } from '@/lib/portal/lombard/lombardBorrowUrlIntent'

describe('parsePortalBorrowUrlIntent', () => {
  it('prefills cbBTC from collateral query', () => {
    const intent = parsePortalBorrowUrlIntent(new URLSearchParams('collateral=cbBTC'))
    assert.deepEqual(intent, { mode: 'prefilled', collateral: 'cbBTC' })
  })

  it('normalizes CBBTC wallet ticker', () => {
    const intent = parsePortalBorrowUrlIntent(new URLSearchParams('collateral=CBBTC'))
    assert.deepEqual(intent, { mode: 'prefilled', collateral: 'cbBTC' })
  })

  it('returns full mode when collateral unknown', () => {
    assert.deepEqual(parsePortalBorrowUrlIntent(new URLSearchParams('collateral=ETH')), { mode: 'full' })
  })
})
