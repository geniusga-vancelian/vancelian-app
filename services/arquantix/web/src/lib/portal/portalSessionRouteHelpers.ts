import { NextResponse } from 'next/server'

import { idempotencyKeySchema } from '@/lib/portal/portalRequestValidation'
import { readPortalPersonIdFromToken, PortalAuthError } from '@/lib/portal/portalJwt'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

export function resolvePortalSessionAccessToken(token: string | null): string | NextResponse {
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }
  return token
}

export async function requirePortalSessionToken(): Promise<string | NextResponse> {
  return resolvePortalSessionAccessToken(await readPortalAccessToken())
}

export function resolvePortalPersonIdFromAccessToken(token: string | null): string | NextResponse {
  const sessionToken = resolvePortalSessionAccessToken(token)
  if (sessionToken instanceof NextResponse) return sessionToken
  try {
    return readPortalPersonIdFromToken(sessionToken)
  } catch (error) {
    if (error instanceof PortalAuthError) {
      return NextResponse.json({ error: 'unauthorized', message: error.message }, { status: 401 })
    }
    throw error
  }
}

export async function requirePortalPersonId(): Promise<string | NextResponse> {
  return resolvePortalPersonIdFromAccessToken(await readPortalAccessToken())
}

export function parseWalletAddress(body: unknown, searchParams?: URLSearchParams): string | null {
  const fromQuery =
    searchParams?.get('wallet_address')?.trim() || searchParams?.get('walletAddress')?.trim()
  if (fromQuery) return fromQuery
  if (!body || typeof body !== 'object') return null
  const row = body as Record<string, unknown>
  const address =
    typeof row.wallet_address === 'string'
      ? row.wallet_address
      : typeof row.walletAddress === 'string'
        ? row.walletAddress
        : null
  if (!address?.trim()) return null
  return address.trim()
}

export function parseIdempotencyKey(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const row = body as Record<string, unknown>
  const raw =
    typeof row.idempotency_key === 'string'
      ? row.idempotency_key
      : typeof row.idempotencyKey === 'string'
        ? row.idempotencyKey
        : null
  if (!raw?.trim()) return null
  const parsed = idempotencyKeySchema.safeParse(raw.trim())
  return parsed.success ? parsed.data : null
}
