import assert from 'node:assert/strict'
import { test } from 'node:test'

import { investBundle } from '@/lib/portal/bundleClient'

test('investBundle maps HTTP 409 to already_pending payload', async () => {
  let postCount = 0
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input, init) => {
    const url = String(input)
    if (url.includes('/api/portal/bundles/invest') && init?.method === 'POST') {
      postCount += 1
      return new Response(
        JSON.stringify({
          status: 'already_pending',
          batch_id: 'batch-abc',
          lock_status: 'pending_signature',
          message: 'A bundle investment is already in progress',
        }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      )
    }
    return new Response(JSON.stringify({ error: 'unexpected' }), { status: 500 })
  }
  try {
    const result = await investBundle({
      portfolio_id: 'p1',
      funding_asset: 'USDC',
      funding_amount: 10,
    })
    assert.equal(result.kind, 'already_pending')
    if (result.kind === 'already_pending') {
      assert.equal(result.payload.batch_id, 'batch-abc')
    }
    assert.equal(postCount, 1)
  } finally {
    globalThis.fetch = originalFetch
  }
})
