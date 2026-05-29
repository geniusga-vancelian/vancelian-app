import { NextRequest, NextResponse } from 'next/server'

import { prisma } from '@/lib/prisma'
import { fetchMorphoVaultPosition } from '@/lib/portal/morphoGraphql'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import { fetchSandboxMorphoVaultPosition } from '@/lib/portal/mocks/morphoLocalSandbox'
import { mapMorphoVaultPosition } from '@/lib/portal/morphoVaultFormat'
import { morphoLedgerErrorResponse } from '@/lib/portal/portalVaultRouteHelpers'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { isValidEvmAddress, MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import { loadPrincipalNetRaw, syncUserVaultPositionFromLedger } from '@/lib/portal/morphoVaultLedger'
import { assertPortalWalletAddressOwnership } from '@/lib/portal/portalWalletOwnership'
import { assertMorphoUsdcBetaAccess } from '@/lib/portal/morphoUsdcBetaAccess'

export async function GET(request: NextRequest) {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    await assertMorphoUsdcBetaAccess(personId)

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

    const row = isMorphoLocalSandboxEnabled()
      ? await fetchSandboxMorphoVaultPosition({ personId, vaultAddress, walletAddress })
      : await fetchMorphoVaultPosition({ vaultAddress, walletAddress })
    if (!row) {
      return NextResponse.json({ position: null })
    }

    const principalNetRaw = await loadPrincipalNetRaw({
      personId,
      vaultAddress,
      chainId: MORPHO_CHAIN_ID,
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
      chainId: MORPHO_CHAIN_ID,
      walletAddress,
      assetSymbol: row.asset.symbol,
      assetDecimals: row.asset.decimals,
      lastAssetsRaw: row.assets,
      lastSharesRaw: row.shares,
      costBasisUnknown: storedPosition?.costBasisUnknown ?? principalNetRaw == null,
    })

    return NextResponse.json({
      position: mapMorphoVaultPosition(row, vaultAddress, {
        principalNetRaw,
        costBasisUnknown: storedPosition?.costBasisUnknown ?? principalNetRaw == null,
      }),
    })
  } catch (error) {
    const ledgerResponse = morphoLedgerErrorResponse(error)
    if (ledgerResponse.status !== 500) return ledgerResponse
    console.error('[api/portal/morpho/position GET]', error)
    return NextResponse.json({ code: 'morpho.internal_error', message: 'Erreur interne.' }, { status: 500 })
  }
}
