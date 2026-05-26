import assert from 'node:assert/strict'
import { test } from 'node:test'

/**
 * Garde double-clic : un seul POST invest tant que inFlightRef est true.
 * (Même logique que useBundleLifiInvest.runInvest.)
 */
test('double invest invocation blocked while in flight', async () => {
  let postCount = 0
  let inFlight = false

  const investOnce = async (): Promise<'ok' | 'blocked'> => {
    if (inFlight) return 'blocked'
    inFlight = true
    try {
      postCount += 1
      await new Promise((r) => setTimeout(r, 20))
      return 'ok'
    } finally {
      inFlight = false
    }
  }

  const [a, b] = await Promise.all([investOnce(), investOnce()])
  assert.equal(postCount, 1)
  assert.ok(
    (a === 'ok' && b === 'blocked') || (a === 'blocked' && b === 'ok'),
    'exactly one call proceeds',
  )
})
