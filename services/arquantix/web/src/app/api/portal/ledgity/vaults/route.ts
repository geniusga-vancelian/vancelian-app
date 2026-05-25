import { NextResponse } from 'next/server'

import { getLedgityBetaPortalFlags } from '@/lib/portal/ledgity/ledgityBetaAccess'
import { fetchLedgityVaultCatalog } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { resolvePortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import { mergeLedgityVaultConfigWithCatalog } from '@/lib/portal/ledgity/ledgityVaultFormat'
import type { PortalLedgityVaultsPayload } from '@/lib/portal/ledgity/ledgityVaultTypes'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Vaults Ledgity publiés (ERC4626 direct) + enrichissement on-chain (PPS, TVL). */
export async function GET() {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const beta = await getLedgityBetaPortalFlags(personId)
    if (beta.enabled && !beta.allowed) {
      const payload: PortalLedgityVaultsPayload = {
        configured: true,
        vaults: [],
        beta,
      }
      return NextResponse.json(payload)
    }

    const configs = await resolvePortalLedgityVaultConfigs({ publishedOnly: true })
    let catalogRows: Awaited<ReturnType<typeof fetchLedgityVaultCatalog>> = []
    try {
      catalogRows = await fetchLedgityVaultCatalog({
        addresses: configs.map((row) => row.vaultAddress).filter(Boolean),
      })
    } catch (catalogError) {
      console.error('[api/portal/ledgity/vaults GET] Ledgity catalog enrichment failed', catalogError)
    }
    const catalogByAddress = new Map(catalogRows.map((row) => [row.address.toLowerCase(), row]))

    const payload: PortalLedgityVaultsPayload = {
      configured: true,
      vaults: configs.map((config) =>
        mergeLedgityVaultConfigWithCatalog(config, catalogByAddress.get(config.vaultAddress.toLowerCase())),
      ),
      beta,
    }
    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/ledgity/vaults GET]', error)
    return NextResponse.json({ code: 'ledgity.internal_error', message: 'Erreur interne.' }, { status: 500 })
  }
}
