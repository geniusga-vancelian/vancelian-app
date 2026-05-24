import { NextResponse } from 'next/server'

import { getPortalEarnVaultConfigs } from '@/lib/portal/privyEarnConfig'
import { mapPrivyEarnVaultDetails } from '@/lib/portal/privyEarnFormat'
import type { PortalEarnVaultsPayload } from '@/lib/portal/privyEarnTypes'
import {
  fetchPrivyEarnVaultDetails,
  isPrivyServerConfigured,
} from '@/lib/portal/privyServerClient'
import {
  findEarnConfigForMorphoRow,
  resolvePortalMorphoVaultConfigs,
} from '@/lib/portal/morphoVaultConfigStore'
import { privyEarnErrorResponse, requirePortalSessionToken } from '@/lib/portal/privyEarnRouteHelpers'

/** @deprecated Préférer `/api/portal/morpho/vaults`. Conserve le fallback env si table vide. */
export async function GET() {
  try {
    const token = await requirePortalSessionToken()
    if (token instanceof NextResponse) return token

    const configs = await resolvePortalMorphoVaultConfigs({ publishedOnly: true })
    const earnConfigs = getPortalEarnVaultConfigs()
    const privyRows = configs.filter((row) => row.integrationMode === 'privy_earn')
    const configured = isPrivyServerConfigured()

    if (!configured) {
      const payload: PortalEarnVaultsPayload = {
        configured: false,
        vaults: privyRows.map((row) => {
          const earnConfig = findEarnConfigForMorphoRow(row, earnConfigs)
          return {
            id: row.privyVaultId ?? row.vaultAddress,
            name: row.label ?? earnConfig?.label ?? 'Vault Earn',
            provider: 'morpho',
            vaultAddress: row.vaultAddress,
            asset: { address: '', symbol: 'USDC', decimals: 6 },
            caip2: '',
            userApyBps: null,
            tvlUsd: null,
            availableLiquidityUsd: null,
            label: row.label ?? earnConfig?.label,
            description: row.description ?? earnConfig?.description,
          }
        }),
      }
      return NextResponse.json(payload)
    }

    const vaults = await Promise.all(
      privyRows.map(async (row) => {
        const earnConfig = findEarnConfigForMorphoRow(row, earnConfigs)
        const vaultId = row.privyVaultId ?? row.vaultAddress
        try {
          const details = await fetchPrivyEarnVaultDetails(vaultId)
          return mapPrivyEarnVaultDetails(details, earnConfig)
        } catch {
          return mapPrivyEarnVaultDetails(
            { id: vaultId, name: row.label ?? 'Vault Earn', provider: 'morpho', vault_address: row.vaultAddress },
            earnConfig,
          )
        }
      }),
    )

    const payload: PortalEarnVaultsPayload = { configured: true, vaults }
    return NextResponse.json(payload)
  } catch (error) {
    return privyEarnErrorResponse(error)
  }
}
