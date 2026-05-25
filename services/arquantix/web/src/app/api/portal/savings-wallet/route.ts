import { NextRequest, NextResponse } from 'next/server'

import { fetchPortalUpstreamJson } from '@/lib/portal/dashboardUpstream'
import { resolveDashboardReferenceCurrency } from '@/lib/portal/dashboardMerge'
import { loadPortalSavingsSummary } from '@/lib/portal/portalSavingsService'
import { requirePortalPersonId } from '@/lib/portal/portalWalletRouteHelpers'

/** Hub épargne DeFi — positions vault Morpho agrégées (aligné hub crypto). */
export async function GET(request: NextRequest) {
  const personId = await requirePortalPersonId()
  if (personId instanceof NextResponse) return personId

  const walletAddress = request.nextUrl.searchParams.get('wallet_address')?.trim() || undefined

  const [bootstrap, savingsResult] = await Promise.all([
    fetchPortalUpstreamJson('/api/app/bootstrap'),
    loadPortalSavingsSummary({ personId, live: true, walletAddress }),
  ])

  const currency = resolveDashboardReferenceCurrency(bootstrap.ok ? bootstrap.data : null)

  return NextResponse.json({
    currency,
    savings: savingsResult.savings,
    historyPoints: [],
    partial: savingsResult.partial || !bootstrap.ok,
  })
}
