import { NextRequest, NextResponse } from 'next/server'

import { prisma } from '@/lib/prisma'
import { assertLedgityBetaAccess } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { LEDGITY_CHAIN_ID, isValidEvmAddress } from '@/lib/portal/ledgity/ledgityConstants'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { fetchLedgityVaultPosition } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { mapLedgityVaultPosition } from '@/lib/portal/ledgity/ledgityVaultFormat'
import { fetchSandboxLedgityVaultPosition } from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'
import { loadPrincipalNetRaw, syncUserVaultPositionFromLedger } from '@/lib/portal/morphoVaultLedger'
import { morphoLedgerErrorResponse } from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'

export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertLedgityBetaAccess(personId)

    const vaultAddress = request.nextUrl.searchParams.get('vault_address')?.trim()
      || request.nextUrl.searchParams.get('vaultAddress')?.trim()
    const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim()
      || request.nextUrl.searchParams.get('walletAddress')?.trim()

    if (!vaultAddress || !isValidEvmAddress(vaultAddress)) {
      return NextResponse.json({ error: 'vault_address invalide.' }, { status: 400 })
    }
    if (!walletAddress || !isValidEvmAddress(walletAddress)) {
      return NextResponse.json({ error: 'wallet_address invalide.' }, { status: 400 })
    }

    await assertPortalWalletAddressOwnership({ personId, walletAddress })

    const row = isLedgityLocalSandboxEnabled()
      ? await fetchSandboxLedgityVaultPosition({ personId, vaultAddress, walletAddress })
      : await fetchLedgityVaultPosition({ vaultAddress, walletAddress })
    if (!row) {
      return NextResponse.json({ position: null })
    }

    const principalNetRaw = await loadPrincipalNetRaw({
      personId,
      vaultAddress,
      chainId: LEDGITY_CHAIN_ID,
      walletAddress,
    })

    const storedPosition = await prisma.userVaultPosition.findFirst({
      where: {
        personId,
        vaultAddress: vaultAddress.toLowerCase(),
        walletAddress: walletAddress.toLowerCase(),
      },
    })

    await syncUserVaultPositionFromLedger({
      personId,
      vaultAddress,
      chainId: LEDGITY_CHAIN_ID,
      walletAddress,
      assetSymbol: row.asset.symbol,
      assetDecimals: row.asset.decimals,
      lastAssetsRaw: row.assets,
      lastSharesRaw: row.shares,
      costBasisUnknown: storedPosition?.costBasisUnknown ?? principalNetRaw == null,
    })

    return NextResponse.json({
      position: mapLedgityVaultPosition(row, vaultAddress, {
        principalNetRaw,
        costBasisUnknown: storedPosition?.costBasisUnknown ?? principalNetRaw == null,
      }),
    })
  } catch (error) {
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/ledgity/position GET]', error)
    return NextResponse.json({ code: 'ledgity.internal_error', message: 'Erreur interne.' }, { status: 500 })
  }
}
