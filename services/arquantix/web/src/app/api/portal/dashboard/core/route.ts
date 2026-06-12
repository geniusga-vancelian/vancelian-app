import { NextResponse } from 'next/server'
import { loadPortalDashboardCorePayload } from '@/lib/portal/dashboardUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/** Dashboard portail — section rapide (header, EUR, inscription). */
export async function GET() {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const payload = await loadPortalDashboardCorePayload()
    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/dashboard/core GET]', error)
    return NextResponse.json({
      bootstrap: null,
      profile: null,
      cash: null,
      globalStatistics: null,
      globalHistory: null,
      notifications: null,
      privyPersonWallets: null,
      partial: true,
    })
  }
}
