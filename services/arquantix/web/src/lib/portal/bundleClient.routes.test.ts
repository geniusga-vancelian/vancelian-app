import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'

import { submitBundleLegTx } from '@/lib/portal/bundleClient'

test('bundleClient uses portal bundle BFF routes (not generic swap submit)', () => {
  const clientSrc = readFileSync(new URL('./bundleClient.ts', import.meta.url), 'utf8')
  assert.match(clientSrc, /\/api\/portal\/bundles\/invest/)
  assert.match(clientSrc, /\/api\/portal\/bundles\/leg\//)
  assert.match(clientSrc, /\/api\/portal\/bundles\/batch\/finalize/)
  assert.doesNotMatch(clientSrc, /\/api\/portal\/swaps\/.*submit/)

  const hookSrc = readFileSync(
    new URL('../../components/portal/bundles/useBundleLifiInvest.ts', import.meta.url),
    'utf8',
  )
  assert.match(hookSrc, /submitBundleLegTx/)
  assert.doesNotMatch(hookSrc, /submitSwapTx/)
})

test('submitBundleLegTx targets bundle leg submit-tx route', async () => {
  const swapId = '00000000-0000-0000-0000-000000000099'
  const originalFetch = globalThis.fetch
  let capturedUrl = ''
  globalThis.fetch = async (input) => {
    capturedUrl = String(input)
    return new Response(JSON.stringify({ status: 'ok' }), { status: 200 })
  }
  try {
    await submitBundleLegTx(swapId, '0xabc')
    assert.equal(
      capturedUrl,
      `/api/portal/bundles/leg/${encodeURIComponent(swapId)}/submit-tx`,
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})
