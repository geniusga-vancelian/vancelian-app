import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { submitBundleLegTx } from '@/lib/portal/bundleClient'

test('bundleClient uses portal bundle BFF routes', () => {
  const clientSrc = readFileSync(new URL('./bundleClient.ts', import.meta.url), 'utf8')
  assert.match(clientSrc, /\/api\/portal\/bundles\/invest/)
  assert.match(clientSrc, /\/api\/portal\/bundles\/withdraw/)
  assert.match(clientSrc, /\/api\/portal\/bundles\/withdraw\/finalize/)
  assert.match(clientSrc, /\/api\/portal\/bundles\/withdraw\/active-lock/)
  assert.match(clientSrc, /\/api\/portal\/bundles\/leg\//)
  assert.match(clientSrc, /\/api\/portal\/bundles\/batch\/finalize/)
})

test('submitBundleLegTx delegates to unified swap submit route (ADR 008)', async () => {
  const swapId = '00000000-0000-0000-0000-000000000099'
  const originalFetch = globalThis.fetch
  let capturedUrl = ''
  globalThis.fetch = async (input) => {
    capturedUrl = String(input)
    return new Response(
      JSON.stringify({ status: 'SUBMITTED', swap_id: swapId, tx_hash: '0xabc' }),
      { status: 200 },
    )
  }
  try {
    await submitBundleLegTx(swapId, '0xabc')
    assert.equal(capturedUrl, `/api/portal/swaps/${encodeURIComponent(swapId)}`)
  } finally {
    globalThis.fetch = originalFetch
  }
})
