import { NextResponse } from 'next/server'

import {
  formatBaseRpcUserMessage,
  isBaseRpcTransientError,
  logBaseRpcSupportEvent,
} from '@/lib/blockchain/baseRpcErrors'
import { LedgityVaultBetaError } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { LedgityVaultLiquidityError } from '@/lib/portal/ledgity/ledgityVaultLiquidityErrors'
import { LombardBetaError, LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
import { MorphoVaultBetaError } from '@/lib/portal/morphoUsdcBetaAccess'
import { MorphoVaultLedgerError } from '@/lib/portal/morphoVaultLedger'
import { PortalAuthError } from '@/lib/portal/portalJwt'
import { PortalForbiddenError } from '@/lib/portal/portalWalletOwnership'

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
