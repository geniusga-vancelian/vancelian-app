import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import jwt from 'jsonwebtoken'

import { BACKEND_JWT_ALGORITHM, getBackendJwtSecret } from '@/lib/backend-jwt'
import { PortalAuthError, readPortalPersonIdFromToken } from '@/lib/portal/portalJwt'

describe('readPortalPersonIdFromToken', () => {
  it('lit person_id depuis le JWT portail', () => {
    const personId = '550e8400-e29b-41d4-a716-446655440000'
    const token = jwt.sign(
      { sub: 'au:42', person_id: personId },
      getBackendJwtSecret(),
      { algorithm: BACKEND_JWT_ALGORITHM, expiresIn: '1h' },
    )
    assert.equal(readPortalPersonIdFromToken(token), personId)
  })

  it('accepte le claim pid', () => {
    const personId = '660e8400-e29b-41d4-a716-446655440001'
    const token = jwt.sign(
      { sub: 'au:42', pid: personId },
      getBackendJwtSecret(),
      { algorithm: BACKEND_JWT_ALGORITHM, expiresIn: '1h' },
    )
    assert.equal(readPortalPersonIdFromToken(token), personId)
  })

  it('rejette un jeton sans person_id', () => {
    const token = jwt.sign(
      { sub: 'au:42' },
      getBackendJwtSecret(),
      { algorithm: BACKEND_JWT_ALGORITHM, expiresIn: '1h' },
    )
    assert.throws(() => readPortalPersonIdFromToken(token), PortalAuthError)
  })
})
