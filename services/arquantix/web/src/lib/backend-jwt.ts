/**
 * JWT BFF → API FastAPI (alignement PR3 / PR3.1).
 *
 * - **sub** = `au:<admin_users.id>` (entier) — identique au backend Python (`jwt_user_claims.format_user_jwt_sub`).
 * - **sub_typ** = `user_id`
 * - **Algorithme** : HS256 (même valeur que `services/arquantix/api/auth.py` → `ALGORITHM = "HS256"`).
 * - **Secret** : même ordre que Python — `JWT_SECRET_KEY` puis `AUTH_SECRET` (voir `getBackendJwtSecret()`).
 *
 * Résolution identité nominative : **uniquement** `users.admin_user_id` (FK vers `admin_users`).
 * Les routes custody CMS utilisent plutôt signInternalBackendJwtAu + BFF_ANONYMOUS_BACKEND_ADMIN_ID (voir custody-bff.ts).
 * Aucun lookup par email sur le chemin d’émission JWT nominatif.
 */
import jwt, { type SignOptions } from 'jsonwebtoken'

/** Aligné sur FastAPI `auth.ALGORITHM` (HS256). */
export const BACKEND_JWT_ALGORITHM = 'HS256' as const

export function getBackendJwtSecret(): string {
  return (
    process.env.JWT_SECRET_KEY ||
    process.env.AUTH_SECRET ||
    'dev-secret-change-me'
  )
}

export type SignAdminBackendJwtOk = {
  ok: true
  token: string
  adminUserId: number
}

export type SignAdminBackendJwtErr = {
  ok: false
  error: 'ADMIN_USER_NOT_LINKED'
}

/** Contexte minimal pour émettre un JWT BFF (session CMS + FK admin API). */
export type AdminJwtSessionContext = {
  /** `users.admin_user_id` — obligatoire pour émettre un JWT vers l’API Python. */
  adminUserId: number | null
}

/**
 * Mint un JWT utilisateur admin pour appeler l’API Python.
 * Utilise **uniquement** `adminUserId` (FK) — pas de résolution par email.
 */
export function signAdminBackendJwtFromSession(
  session: AdminJwtSessionContext,
  options?: { expiresIn?: SignOptions['expiresIn'] }
): SignAdminBackendJwtOk | SignAdminBackendJwtErr {
  if (session.adminUserId == null) {
    return { ok: false, error: 'ADMIN_USER_NOT_LINKED' }
  }
  const id = session.adminUserId
  if (!Number.isInteger(id) || id <= 0) {
    return { ok: false, error: 'ADMIN_USER_NOT_LINKED' }
  }

  const expiresIn: SignOptions['expiresIn'] = options?.expiresIn ?? '24h'
  const signOpts: SignOptions = {
    expiresIn,
    algorithm: BACKEND_JWT_ALGORITHM,
  }
  const token = jwt.sign(
    { sub: `au:${id}`, sub_typ: 'user_id' },
    getBackendJwtSecret(),
    signOpts
  )
  return { ok: true, token, adminUserId: id }
}

/**
 * Lit `BFF_ANONYMOUS_BACKEND_ADMIN_ID` (**obligatoire** en prod — pas de défaut `1`).
 * Compte technique dédié dans `admin_users` (ex. id réservé + rôle internal).
 */
export function parseRequiredAnonymousBackendAdminIdFromEnv(): number {
  const raw = process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID
  if (raw === undefined || String(raw).trim() === '') {
    throw new Error(
      'BFF_ANONYMOUS_BACKEND_ADMIN_ID is required: set it to an existing admin_users.id used for internal BFF JWTs (widgets, feed preview)'
    )
  }
  const n = parseInt(String(raw), 10)
  if (!Number.isInteger(n) || n <= 0) {
    throw new Error(
      `BFF_ANONYMOUS_BACKEND_ADMIN_ID must be a positive integer, got: ${raw}`
    )
  }
  return n
}

let _cachedAnonymousAdminId: number | null = null

export function getAnonymousBackendAdminId(): number {
  if (_cachedAnonymousAdminId !== null) {
    return _cachedAnonymousAdminId
  }
  _cachedAnonymousAdminId = parseRequiredAnonymousBackendAdminIdFromEnv()
  return _cachedAnonymousAdminId
}

export function signInternalBackendJwtAu(
  adminUserId: number,
  expiresIn: SignOptions['expiresIn'] = '24h'
): string {
  if (!Number.isInteger(adminUserId) || adminUserId <= 0) {
    throw new Error('signInternalBackendJwtAu: adminUserId must be a positive integer')
  }
  const signOpts: SignOptions = {
    expiresIn,
    algorithm: BACKEND_JWT_ALGORITHM,
  }
  return jwt.sign(
    { sub: `au:${adminUserId}`, sub_typ: 'user_id' },
    getBackendJwtSecret(),
    signOpts
  )
}
