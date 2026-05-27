/**
 * Helpers BFF portail : session JWT, parsing wallet/idempotency, réponses erreurs Morpho.
 * Utilisé par les routes `/api/portal/morpho/*` et `/api/portal/wallets/external/*`.
 */
import { NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { readPortalPersonIdFromToken, PortalAuthError } from '@/lib/portal/portalJwt'
import { idempotencyKeySchema } from '@/lib/portal/morphoVaultValidation'
import { MorphoVaultLedgerError } from '@/lib/portal/morphoVaultLedger'
import { LedgityVaultBetaError } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { buildLedgityLedgerMetadata } from '@/lib/portal/ledgity/ledgityLedgerMetadata'
import {
  assertLedgityWithdrawLiquidity,
  LedgityVaultLiquidityError,
  readLedgityVaultLiquidityMetrics,
} from '@/lib/portal/ledgity/ledgityVaultLiquidity'
import { LombardBetaError, LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
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

export function ledgityRpcErrorResponse(error: unknown, route?: string): NextResponse | null {
  if (!isBaseRpcTransientError(error)) return null
  logBaseRpcSupportEvent({ error, route })
  return NextResponse.json(
    { code: 'ledgity.base_rpc_busy', message: formatBaseRpcUserMessage(error) },
    { status: 503 },
  )
}

export function morphoLedgerErrorResponse(error: unknown): NextResponse {
  if (error instanceof MorphoVaultBetaError || error instanceof LedgityVaultBetaError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof LombardBetaError || error instanceof LombardSafetyError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
  }
  if (error instanceof LedgityVaultLiquidityError) {
    return NextResponse.json({ code: error.code, message: error.message }, { status: error.status })
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
