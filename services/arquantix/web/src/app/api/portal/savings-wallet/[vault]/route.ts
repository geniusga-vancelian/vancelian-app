import { NextRequest, NextResponse } from 'next/server'

import { fetchPortalUpstreamJson } from '@/lib/portal/dashboardUpstream'
import { resolveDashboardReferenceCurrency } from '@/lib/portal/dashboardMerge'
import { isValidEvmAddress, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { mapPortalSavingsVaultTransactions } from '@/lib/portal/portalSavingsFormat'
import { loadPortalSavingsVaultDetail } from '@/lib/portal/portalSavingsService'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Détail vault épargne — position, APY, historique ledger (aligné crypto wallet detail). */
export async function GET(
  _request: NextRequest,
  { params }: { params: { vault: string } },
) {
  const personId = await requirePortalPersonId()
  if (personId instanceof NextResponse) return personId

  const rawVault = decodeURIComponent(params.vault ?? '').trim()
  const vaultAddress = rawVault.startsWith('0x') ? normalizeVaultAddress(rawVault) : rawVault
  if (!isValidEvmAddress(vaultAddress)) {
    return NextResponse.json({ error: 'invalid_vault' }, { status: 400 })
  }

  const bootstrap = await fetchPortalUpstreamJson('/api/app/bootstrap')
  const currency = resolveDashboardReferenceCurrency(bootstrap.ok ? bootstrap.data : null)

  const detail = await loadPortalSavingsVaultDetail({
    personId,
    vaultAddress,
    currency,
    mapTransactions: (rows, currentBalanceUsd) =>
      mapPortalSavingsVaultTransactions(rows, currentBalanceUsd),
  })

  if (!detail) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 })
  }

  return NextResponse.json({
    ...detail,
    partial: detail.partial || !bootstrap.ok,
  })
}
