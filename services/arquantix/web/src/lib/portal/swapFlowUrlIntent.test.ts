import assert from 'node:assert/strict'
import test from 'node:test'

import { parsePortalSwapUrlIntent } from '@/lib/portal/swapFlowTypes'

test('parsePortalSwapUrlIntent — buy CBBTC on Base', () => {
  const params = new URLSearchParams('to=CBBTC&toChain=base')
  assert.deepEqual(parsePortalSwapUrlIntent(params, 'base'), {
    mode: 'buy',
    toAsset: 'CBBTC',
    toChain: 'base',
  })
})

test('parsePortalSwapUrlIntent — sell uses from', () => {
  const params = new URLSearchParams('from=CBBTC&fromChain=base')
  assert.deepEqual(parsePortalSwapUrlIntent(params, 'base'), {
    mode: 'sell',
    fromAsset: 'CBBTC',
    fromChain: 'base',
  })
})

test('parsePortalSwapUrlIntent — chain from navbar when query omits chain', () => {
  const params = new URLSearchParams('to=CBBTC')
  assert.deepEqual(parsePortalSwapUrlIntent(params, 'base'), {
    mode: 'buy',
    toAsset: 'CBBTC',
    toChain: 'base',
  })
})

test('parsePortalSwapUrlIntent — buy CBETH on Base', () => {
  const params = new URLSearchParams('to=CBETH&toChain=base')
  assert.deepEqual(parsePortalSwapUrlIntent(params, 'base'), {
    mode: 'buy',
    toAsset: 'CBETH',
    toChain: 'base',
  })
})

test('parsePortalSwapUrlIntent — full when no trade params', () => {
  assert.deepEqual(parsePortalSwapUrlIntent(new URLSearchParams(), 'base'), { mode: 'full' })
})
