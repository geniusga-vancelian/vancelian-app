import jwt from 'jsonwebtoken'

import { BACKEND_JWT_ALGORITHM, getBackendJwtSecret } from '@/lib/backend-jwt'

export class PortalAuthError extends Error {
  readonly httpStatus = 401

  constructor(message = 'Session portail invalide ou expirée.') {
    super(message)
    this.name = 'PortalAuthError'
  }
}

export function readPortalPersonIdFromToken(token: string): string {
  let payload: jwt.JwtPayload
  try {
    payload = jwt.verify(token, getBackendJwtSecret(), {
      algorithms: [BACKEND_JWT_ALGORITHM],
    }) as jwt.JwtPayload
  } catch {
    throw new PortalAuthError()
  }

  const raw = payload.person_id ?? payload.pid
  if (typeof raw !== 'string' || !raw.trim()) {
    throw new PortalAuthError('Identité personne absente du jeton.')
  }
  return raw.trim()
}
