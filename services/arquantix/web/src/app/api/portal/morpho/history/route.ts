import { NextRequest, NextResponse } from 'next/server'

import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import {
  morphoLedgerErrorResponse,
  requirePortalPersonId,
} from '@/lib/portal/privyEarnRouteHelpers'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import { assertMorphoUsdcBetaAccess } from '@/lib/portal/morphoUsdcBetaAccess'
import { prisma } from '@/lib/prisma'

/** Historique ledger Morpho d’un utilisateur pour un vault/wallet. */
export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertMorphoUsdcBetaAccess(personId)

    const vaultAddress = request.nextUrl.searchParams.get('vault_address')?.trim()
      || request.nextUrl.searchParams.get('vaultAddress')?.trim()
    const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim()
      || request.nextUrl.searchParams.get('walletAddress')?.trim()
    const limitRaw = Number(request.nextUrl.searchParams.get('limit') ?? '50')
    const limit = Number.isFinite(limitRaw) ? Math.min(Math.max(limitRaw, 1), 200) : 50

    if (vaultAddress && !isValidEvmAddress(vaultAddress)) {
      return NextResponse.json({ error: 'vault_address invalide.' }, { status: 400 })
    }
    if (walletAddress) {
      if (!isValidEvmAddress(walletAddress)) {
        return NextResponse.json({ error: 'wallet_address invalide.' }, { status: 400 })
      }
      await assertPortalWalletAddressOwnership({ personId, walletAddress })
    }

    const rows = await prisma.onchainVaultTransaction.findMany({
      where: {
        personId,
        ...(vaultAddress ? { vaultAddress: vaultAddress.toLowerCase() } : {}),
        ...(walletAddress ? { walletAddress: walletAddress.toLowerCase() } : {}),
      },
      orderBy: { createdAt: 'desc' },
      take: limit,
      select: {
        id: true,
        vaultAddress: true,
        walletAddress: true,
        privyWalletId: true,
        operation: true,
        amountRaw: true,
        assetSymbol: true,
        assetDecimals: true,
        status: true,
        txHash: true,
        blockNumber: true,
        integrationMode: true,
        idempotencyKey: true,
        privyActionId: true,
        errorMessage: true,
        createdAt: true,
        updatedAt: true,
      },
    })

    return NextResponse.json({
      transactions: rows.map((row) => ({
        ...row,
        blockNumber: row.blockNumber?.toString() ?? null,
        createdAt: row.createdAt.toISOString(),
        updatedAt: row.updatedAt.toISOString(),
      })),
    })
  } catch (error) {
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/morpho/history GET]', error)
    return NextResponse.json({ code: 'morpho.internal_error', message: 'Erreur interne.' }, { status: 500 })
  }
}
