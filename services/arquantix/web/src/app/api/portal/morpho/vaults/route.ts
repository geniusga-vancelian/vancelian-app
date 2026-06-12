import { NextResponse } from 'next/server'

import { fetchMorphoVaultsByAddresses } from '@/lib/portal/morphoGraphql'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'
import { listSandboxMockVaultCatalogs } from '@/lib/portal/mocks/morphoLocalSandbox'
import { mergeMorphoVaultConfigWithGraphql } from '@/lib/portal/morphoVaultFormat'
import { resolvePortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { requirePortalPersonId } from '@/lib/portal/portalSessionRouteHelpers'
import { getMorphoBetaPortalFlags } from '@/lib/portal/morphoUsdcBetaAccess'
import type { PortalMorphoVaultsPayload } from '@/lib/portal/morphoVaultTypes'

/** Vaults Morpho publiés (direct on-chain) + enrichissement GraphQL (APY, TVL). */
export async function GET() {
  try {
    const personId = await requirePortalPersonId()
    if (personId instanceof NextResponse) return personId

    const beta = await getMorphoBetaPortalFlags(personId)
    if (beta.enabled && !beta.allowed) {
      const payload: PortalMorphoVaultsPayload = {
        configured: true,
        vaults: [],
        beta,
      }
      return NextResponse.json(payload)
    }

    const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
    const sandbox = isMorphoLocalSandboxEnabled()
    let gqlRows: Awaited<ReturnType<typeof fetchMorphoVaultsByAddresses>> = []
    if (sandbox) {
      gqlRows = listSandboxMockVaultCatalogs(configs.map((row) => row.vaultAddress).filter(Boolean))
    } else {
      try {
        gqlRows = await fetchMorphoVaultsByAddresses({
          addresses: configs.map((row) => row.vaultAddress).filter(Boolean),
        })
      } catch (gqlError) {
        console.error('[api/portal/morpho/vaults GET] Morpho GraphQL enrichment failed', gqlError)
      }
    }
    const gqlByAddress = new Map(gqlRows.map((row) => [row.address.toLowerCase(), row]))

    const payload: PortalMorphoVaultsPayload = {
      configured: true,
      vaults: configs.map((config) =>
        mergeMorphoVaultConfigWithGraphql(config, gqlByAddress.get(config.vaultAddress.toLowerCase())),
      ),
      beta,
    }
    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/morpho/vaults GET]', error)
    // Fail-soft : 200 + liste vide marquée partielle plutôt qu'un 500 qui casse
    // le hub Invest et la page détail (le détail propose un retry sur `partial`).
    return NextResponse.json({
      configured: true,
      vaults: [],
      partial: true,
    } satisfies PortalMorphoVaultsPayload)
  }
}
