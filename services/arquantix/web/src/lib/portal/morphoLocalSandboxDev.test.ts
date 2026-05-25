import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

process.env.NODE_ENV = 'test'
process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'

import {
  isMorphoSandboxDevRouteAvailable,
} from './morphoLocalSandboxDev'
import { isSandboxMorphoIdempotencyKey } from './mocks/morphoLocalSandbox'

describe('morpho local sandbox dev helpers', () => {
  it('detects sandbox idempotency keys', () => {
    assert.equal(isSandboxMorphoIdempotencyKey('sandbox-seed-deposit-initial'), true)
    assert.equal(isSandboxMorphoIdempotencyKey('user-deposit-123'), false)
  })

  it('dev route available in test env with sandbox enabled', () => {
    assert.equal(isMorphoSandboxDevRouteAvailable(), true)
  })

  it('dev route unavailable in production', () => {
    const prev = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    try {
      assert.equal(isMorphoSandboxDevRouteAvailable(), false)
    } finally {
      process.env.NODE_ENV = prev
    }
  })
})
