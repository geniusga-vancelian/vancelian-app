import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import jwt from 'jsonwebtoken'
import { NextResponse } from 'next/server'

import { BACKEND_JWT_ALGORITHM, getBackendJwtSecret } from '@/lib/backend-jwt'
import {
  parseIdempotencyKey,
  parseWalletAddress,
  resolvePortalPersonIdFromAccessToken,
  resolvePortalSessionAccessToken,
} from '@/lib/portal/portalSessionRouteHelpers'

describe('portalSessionRouteHelpers — session auth', () => {
  it('requirePortalSessionToken sans token retourne 401', () => {
    const result = resolvePortalSessionAccessToken(null)
    assert.ok(result instanceof NextResponse)
    assert.equal(result.status, 401)
  })

  it('requirePortalPersonId avec token valide retourne personId', () => {
    const personId = '550e8400-e29b-41d4-a716-446655440000'
    const token = jwt.sign(
      { sub: 'au:42', person_id: personId },
      getBackendJwtSecret(),
      { algorithm: BACKEND_JWT_ALGORITHM, expiresIn: '1h' },
    )
    const result = resolvePortalPersonIdFromAccessToken(token)
    assert.equal(result, personId)
  })

  it('requirePortalPersonId avec token invalide retourne 401', () => {
    const result = resolvePortalPersonIdFromAccessToken('not-a-valid-jwt')
    assert.ok(result instanceof NextResponse)
    assert.equal(result.status, 401)
  })
})

describe('portalSessionRouteHelpers — parseWalletAddress', () => {
  it('lit wallet_address depuis le body', () => {
    assert.equal(parseWalletAddress({ wallet_address: ' 0xabc ' }), '0xabc')
  })

  it('lit walletAddress depuis le body', () => {
    assert.equal(parseWalletAddress({ walletAddress: '0xdef' }), '0xdef')
  })

  it('lit wallet_address depuis les search params', () => {
    const params = new URLSearchParams('wallet_address=0x111')
    assert.equal(parseWalletAddress(null, params), '0x111')
  })

  it('lit walletAddress depuis les search params', () => {
    const params = new URLSearchParams('walletAddress=0x222')
    assert.equal(parseWalletAddress(null, params), '0x222')
  })

  it('retourne null si absent', () => {
    assert.equal(parseWalletAddress({}), null)
    assert.equal(parseWalletAddress(null), null)
  })
})

describe('portalSessionRouteHelpers — parseIdempotencyKey', () => {
  it('accepte idempotency_key valide', () => {
    assert.equal(parseIdempotencyKey({ idempotency_key: 'abcd1234' }), 'abcd1234')
  })

  it('accepte idempotencyKey camelCase', () => {
    assert.equal(parseIdempotencyKey({ idempotencyKey: 'abcd1234' }), 'abcd1234')
  })

  it('rejette une clé trop courte', () => {
    assert.equal(parseIdempotencyKey({ idempotency_key: 'short' }), null)
  })

  it('retourne null si absent', () => {
    assert.equal(parseIdempotencyKey({}), null)
    assert.equal(parseIdempotencyKey(null), null)
  })
})
