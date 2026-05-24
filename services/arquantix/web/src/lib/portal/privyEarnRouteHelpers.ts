import { NextResponse } from 'next/server'
import { PrivyServerApiError } from '@/lib/portal/privyServerClient'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { readPortalPersonIdFromToken, PortalAuthError } from '@/lib/portal/portalJwt'
import { idempotencyKeySchema } from '@/lib/portal/morphoVaultValidation'
import { MorphoVaultLedgerError } from '@/lib/portal/morphoVaultLedger'
import { MorphoVaultBetaError } from '@/lib/portal/morphoUsdcBetaAccess'
import { PortalForbiddenError } from '@/lib/portal/portalWalletOwnership'
import {
  formatBaseRpcUserMessage,
  isBaseRpcTransientError,
  logBaseRpcSupportEvent,
} from '@/lib/blockchain/baseRpcErrors'

export async function requirePortalSessionToken(): Promise<string | NextResponse> {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }
  return token
}

export async function requirePortalPersonId(): Promise<string | NextResponse> {
  const token = await requirePortalSessionToken()
  if (token instanceof NextResponse) return token
  try {
    return readPortalPersonIdFromToken(token)
  } catch (error) {
    if (error instanceof PortalAuthError) {
      return NextResponse.json({ error: 'unauthorized', message: error.message }, { status: 401 })
    }
    throw error
  }
}

export function morphoRpcErrorResponse(error: unknown, route?: string): NextResponse | null {
  if (!isBaseRpcTransientError(error)) return null
  logBaseRpcSupportEvent({ error, route })
  return NextResponse.json(
    { code: 'morpho.base_rpc_busy', message: formatBaseRpcUserMessage(error) },
    { status: 503 },
  )
}

export function morphoLedgerErrorResponse(error: unknown): NextResponse {
  if (error instanceof MorphoVaultBetaError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof MorphoVaultLedgerError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof PortalForbiddenError) {
    return NextResponse.json({ code: 'portal.forbidden_wallet', message: error.message }, { status: 403 })
  }
  if (error instanceof PortalAuthError) {
    return NextResponse.json({ error: 'unauthorized', message: error.message }, { status: 401 })
  }
  console.error('[portal/morpho]', error)
  return NextResponse.json({ code: 'morpho.internal_error', message: 'Erreur interne.' }, { status: 500 })
}

export function privyEarnErrorResponse(error: unknown): NextResponse {
  if (error instanceof MorphoVaultBetaError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof PortalForbiddenError) {
    return NextResponse.json({ code: 'portal.forbidden_wallet', message: error.message }, { status: 403 })
  }
  if (error instanceof MorphoVaultLedgerError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof PrivyServerApiError) {
    return NextResponse.json(
      { code: error.code, message: error.message },
      { status: error.httpStatus >= 400 && error.httpStatus < 600 ? error.httpStatus : 502 },
    )
  }
  console.error('[portal/privy/earn]', error)
  return NextResponse.json({ code: 'privy.earn.internal_error', message: 'Erreur interne.' }, { status: 500 })
}

export function parseEarnAmount(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const amount = (body as { amount?: unknown }).amount
  if (typeof amount !== 'string' && typeof amount !== 'number') return null
  const normalized = String(amount).trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(normalized)) return null
  if (Number(normalized) <= 0) return null
  return normalized
}

export function parsePrivyWalletId(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const walletId = (body as { privy_wallet_id?: unknown; privyWalletId?: unknown }).privy_wallet_id
    ?? (body as { privyWalletId?: unknown }).privyWalletId
  if (typeof walletId !== 'string' || !walletId.trim()) return null
  return walletId.trim()
}

export function parseVaultId(body: unknown, searchParams?: URLSearchParams): string | null {
  const fromQuery = searchParams?.get('vault_id')?.trim() || searchParams?.get('vaultId')?.trim()
  if (fromQuery) return fromQuery
  if (!body || typeof body !== 'object') return null
  const vaultId = (body as { vault_id?: unknown; vaultId?: unknown }).vault_id
    ?? (body as { vaultId?: unknown }).vaultId
  if (typeof vaultId !== 'string' || !vaultId.trim()) return null
  return vaultId.trim()
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

export function parseRequiredIdempotencyKey(body: unknown): string | null {
  return parseIdempotencyKey(body)
}

export function parseAuthHeaders(body: unknown): {
  authorizationSignature?: string
  idempotencyKey?: string
  requestExpiry?: string
} {
  if (!body || typeof body !== 'object') return {}
  const row = body as Record<string, unknown>
  const idempotencyKey = parseIdempotencyKey(body) ?? undefined
  return {
    authorizationSignature:
      typeof row.authorization_signature === 'string'
        ? row.authorization_signature
        : typeof row.authorizationSignature === 'string'
          ? row.authorizationSignature
          : undefined,
    idempotencyKey,
    requestExpiry:
      typeof row.request_expiry === 'string'
        ? row.request_expiry
        : typeof row.requestExpiry === 'string'
          ? row.requestExpiry
          : undefined,
  }
}
