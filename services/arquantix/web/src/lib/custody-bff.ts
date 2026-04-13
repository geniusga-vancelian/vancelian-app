/**
 * BFF custody → API Python : JWT **compte de service** (`BFF_ANONYMOUS_BACKEND_ADMIN_ID`)
 * + en-têtes d’audit opérateur CMS (sans confondre avec le titulaire métier côté API).
 */
import { NextResponse } from 'next/server'

import type { AdminWebSession } from '@/lib/auth'
import {
  getAnonymousBackendAdminId,
  signInternalBackendJwtAu,
} from '@/lib/backend-jwt'

import { BFF_ERROR_CMS_ACTION_FORBIDDEN } from '@/lib/bff-errors'

/** Identifiant logique du principal « service » (en-tête X-Actor-Id). */
const DEFAULT_SERVICE_ACTOR_ID = 'cms-custody-service'

export function getCustodyServiceActorId(): string {
  const raw = process.env.CMS_CUSTODY_SERVICE_ACTOR_ID?.trim()
  return raw && raw.length > 0 ? raw : DEFAULT_SERVICE_ACTOR_ID
}

/** Rôles CMS autorisés à appeler les routes custody (back-office). */
export function canAccessCustody(session: AdminWebSession): boolean {
  return session.userRole === 'SUPER_ADMIN' || session.userRole === 'ADMIN'
}

export function custodyAccessForbiddenResponse(): NextResponse {
  return NextResponse.json({ error: BFF_ERROR_CMS_ACTION_FORBIDDEN }, { status: 403 })
}

export type CustodyBackendAuth =
  | { ok: true; headers: Record<string, string>; serviceJwtAdminId: number }
  | { ok: false; response: NextResponse }

/**
 * Mint JWT service + en-têtes standard custody (actor service + trace opérateur CMS).
 */
export function getCustodyBackendAuth(): CustodyBackendAuth {
  try {
    const serviceJwtAdminId = getAnonymousBackendAdminId()
    const token = signInternalBackendJwtAu(serviceJwtAdminId, '15m')
    const requestId = crypto.randomUUID()
    const headers: Record<string, string> = {
      Authorization: `Bearer ${token}`,
      'X-Actor-Type': 'service',
      'X-Actor-Id': getCustodyServiceActorId(),
      'X-Actor-Roles': 'admin',
      'X-Request-Id': requestId,
    }
    return { ok: true, headers, serviceJwtAdminId }
  } catch {
    return {
      ok: false,
      response: NextResponse.json(
        {
          error:
            'Service custody indisponible : variable d’environnement BFF_ANONYMOUS_BACKEND_ADMIN_ID manquante ou invalide.',
        },
        { status: 503 },
      ),
    }
  }
}

/**
 * Complète les en-têtes d’audit opérateur CMS (source de vérité humaine).
 */
export function withCmsOperatorHeaders(
  base: Record<string, string>,
  session: AdminWebSession,
): Record<string, string> {
  return {
    ...base,
    'X-CMS-User-Id': session.userId,
    'X-CMS-User-Email': session.userEmail,
    'X-CMS-User-Roles': session.userRole,
  }
}

/**
 * Chaîne prête pour fetch() : auth service + opérateur CMS.
 */
export function buildCustodyUpstreamHeaders(session: AdminWebSession): CustodyBackendAuth {
  const auth = getCustodyBackendAuth()
  if (!auth.ok) return auth
  return {
    ok: true,
    headers: withCmsOperatorHeaders(auth.headers, session),
    serviceJwtAdminId: auth.serviceJwtAdminId,
  }
}

export type CustodyPreflight =
  | { ok: true; session: AdminWebSession; headers: Record<string, string> }
  | { ok: false; response: NextResponse }

/** Session CMS + droit custody + JWT service + en-têtes audit opérateur. */
export function preflightCustodyRequest(
  session: AdminWebSession | null,
): CustodyPreflight {
  if (!session) {
    return { ok: false, response: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }) }
  }
  if (!canAccessCustody(session)) {
    return { ok: false, response: custodyAccessForbiddenResponse() }
  }
  const auth = buildCustodyUpstreamHeaders(session)
  if (!auth.ok) {
    return { ok: false, response: auth.response }
  }
  return { ok: true, session, headers: auth.headers }
}
