import assert from 'node:assert/strict'
import test from 'node:test'

import { waitForPrivyClientReady } from './waitForPrivyClientReady.ts'

test('waitForPrivyClientReady resolves when getter becomes true during poll', async () => {
  let ready = false
  setTimeout(() => {
    ready = true
  }, 250)

  await waitForPrivyClientReady(() => ready, { timeoutMs: 2_000, intervalMs: 50 })
  assert.equal(ready, true)
})

test('waitForPrivyClientReady throws after timeout', async () => {
  await assert.rejects(
    () => waitForPrivyClientReady(() => false, { timeoutMs: 200, intervalMs: 50 }),
    /Privy is still initializing/,
  )
})
