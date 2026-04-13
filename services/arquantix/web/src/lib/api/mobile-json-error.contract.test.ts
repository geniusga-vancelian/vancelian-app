import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { mobileApiJsonError } from './mobile-json-error'

describe('mobileApiJsonError', () => {
  it('returns JSON body with error + message and no HTML', async () => {
    const res = mobileApiJsonError(500, 'Readable API-safe message')
    assert.equal(res.status, 500)
    const ct = res.headers.get('content-type')
    assert.ok(ct?.includes('application/json'), ct ?? '')
    const body = await res.json()
    assert.equal(body.error, 'Internal server error')
    assert.equal(body.message, 'Readable API-safe message')
  })

  it('serializes as JSON string without HTML', async () => {
    const text = await mobileApiJsonError(502, 'upstream').text()
    assert.ok(text.trim().startsWith('{'))
    assert.ok(!text.toLowerCase().includes('<html'))
  })
})
