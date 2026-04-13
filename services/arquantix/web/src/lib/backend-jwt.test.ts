import assert from 'node:assert/strict'
import { describe, it, beforeEach, afterEach } from 'node:test'
import jwt from 'jsonwebtoken'

import {
  BACKEND_JWT_ALGORITHM,
  getBackendJwtSecret,
  parseRequiredAnonymousBackendAdminIdFromEnv,
  signAdminBackendJwtFromSession,
  signInternalBackendJwtAu,
} from './backend-jwt'

describe('backend-jwt (PR3 / PR3.1)', () => {
  it('signInternalBackendJwtAu émet sub=au:<id>, sub_typ=user_id, algo HS256 (parité Python)', () => {
    const token = signInternalBackendJwtAu(42, '1h')
    const decoded = jwt.verify(token, getBackendJwtSecret(), {
      algorithms: [BACKEND_JWT_ALGORITHM],
    }) as jwt.JwtPayload
    assert.equal(decoded.sub, 'au:42')
    assert.equal(decoded.sub_typ, 'user_id')
  })

  it('refuse un admin id invalide', () => {
    assert.throws(() => signInternalBackendJwtAu(0), /positive integer/)
  })

  it('signAdminBackendJwtFromSession refuse sans admin_user_id (FK)', () => {
    const r = signAdminBackendJwtFromSession({ adminUserId: null })
    assert.equal(r.ok, false)
    if (r.ok) throw new Error('expected failure')
    assert.equal(r.error, 'ADMIN_USER_NOT_LINKED')
  })

  it('signAdminBackendJwtFromSession mint avec admin_user_id uniquement', () => {
    const r = signAdminBackendJwtFromSession({ adminUserId: 1001 })
    assert.equal(r.ok, true)
    if (!r.ok) throw new Error('expected success')
    const decoded = jwt.verify(r.token, getBackendJwtSecret(), {
      algorithms: [BACKEND_JWT_ALGORITHM],
    }) as jwt.JwtPayload
    assert.equal(decoded.sub, 'au:1001')
  })

  describe('BFF_ANONYMOUS_BACKEND_ADMIN_ID', () => {
    let prev: string | undefined

    beforeEach(() => {
      prev = process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID
    })

    afterEach(() => {
      if (prev === undefined) delete process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID
      else process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID = prev
    })

    it('absent ou vide → erreur explicite', () => {
      delete process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID
      assert.throws(
        () => parseRequiredAnonymousBackendAdminIdFromEnv(),
        /BFF_ANONYMOUS_BACKEND_ADMIN_ID is required/
      )
    })

    it('valeur valide → entier positif', () => {
      process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID = '42'
      assert.equal(parseRequiredAnonymousBackendAdminIdFromEnv(), 42)
    })
  })
})
