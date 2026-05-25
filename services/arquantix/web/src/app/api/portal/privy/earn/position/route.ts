import { NextRequest, NextResponse } from 'next/server'

import { mapPrivyEarnVaultPosition } from '@/lib/portal/privyEarnFormat'
import { PrivyEarnVaultConfigError, resolvePublishedPrivyEarnVault } from '@/lib/portal/morphoPrivyEarnService'
import { fetchPrivyEarnVaultPosition } from '@/lib/portal/privyServerClient'
import {
  parsePrivyWalletId,
  parseVaultId,
  parseWalletAddress,
  privyEarnErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/privyEarnRouteHelpers'
import { assertPortalPrivyWalletOwnership } from '@/lib/portal/portalWalletOwnership'

async function handlePositionRequest(args: {
  personId: string
  vaultId: string
  walletId: string
  walletAddress?: string | null
}) {
  await assertPortalPrivyWalletOwnership({
    personId: args.personId,
    privyWalletId: args.walletId,
    walletAddress: args.walletAddress,
  })
  await resolvePublishedPrivyEarnVault(args.vaultId)
  const row = await fetchPrivyEarnVaultPosition(args.walletId, args.vaultId)
  return NextResponse.json({ position: mapPrivyEarnVaultPosition(row, args.vaultId) })
}

/** Position Earn d’un wallet Privy dans un vault. */
export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const vaultId = parseVaultId(null, request.nextUrl.searchParams)
    const walletId = request.nextUrl.searchParams.get('privy_wallet_id')?.trim()
      || request.nextUrl.searchParams.get('privyWalletId')?.trim()
      || null
    const walletAddress = parseWalletAddress(null, request.nextUrl.searchParams)

    if (!vaultId || !walletId) {
      return NextResponse.json(
        { code: 'privy.earn.invalid_request', message: 'vault_id et privy_wallet_id requis.' },
        { status: 400 },
      )
    }

    return handlePositionRequest({ personId, vaultId, walletId, walletAddress })
  } catch (error) {
    if (error instanceof PrivyEarnVaultConfigError) {
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    return privyEarnErrorResponse(error)
  }
}

export async function POST(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const body = await request.json().catch(() => null)
    const vaultId = parseVaultId(body)
    const walletId = parsePrivyWalletId(body)
    const walletAddress = parseWalletAddress(body)
    if (!vaultId || !walletId) {
      return NextResponse.json(
        { code: 'privy.earn.invalid_request', message: 'vault_id et privy_wallet_id requis.' },
        { status: 400 },
      )
    }

    return handlePositionRequest({ personId, vaultId, walletId, walletAddress })
  } catch (error) {
    if (error instanceof PrivyEarnVaultConfigError) {
      return NextResponse.json({ code: error.code, message: error.message }, { status: error.httpStatus })
    }
    return privyEarnErrorResponse(error)
  }
}
