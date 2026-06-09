import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  bundleV3QueuedToInvestShim,
  investBundle,
  isBundleV3DepositQueuedPayload,
} from '@/lib/portal/bundleClient'

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

test('investBundle maps V3 queued deposit to v3_queued payload', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input, init) => {
    const url = String(input)
    if (url.includes('/api/portal/bundles/invest') && init?.method === 'POST') {
      return new Response(
        JSON.stringify({
          status: 'queued',
          flow: 'bundle_v3_deposit',
          deposit_execution_id: 'dep-1',
          batch_id: 'batch-v3',
          portfolio_id: 'p1',
          intent_id: 'intent-1',
          outbox_id: 'outbox-1',
          funding: { amount: 20, funded: true },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      )
    }
    return new Response(JSON.stringify({ error: 'unexpected' }), { status: 500 })
  }
  try {
    const result = await investBundle({
      portfolio_id: 'p1',
      funding_asset: 'USDC',
      funding_amount: 20,
    })
    assert.equal(result.kind, 'v3_queued')
    if (result.kind === 'v3_queued') {
      assert.equal(result.payload.batch_id, 'batch-v3')
      assert.equal(result.payload.flow, 'bundle_v3_deposit')
      const shim = bundleV3QueuedToInvestShim(result.payload, {
        fundingAsset: 'USDC',
        fundingAmount: 20,
      })
      assert.equal(shim.total_entry_asset_received, 20)
      assert.deepEqual(shim.allocation_details, [])
    }
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('isBundleV3DepositQueuedPayload rejects legacy success shape', () => {
  assert.equal(
    isBundleV3DepositQueuedPayload({
      status: 'pending_signature',
      batch_id: 'batch-legacy',
      allocation_details: [{ asset: 'ETH', status: 'pending' }],
    }),
    false,
  )
})
