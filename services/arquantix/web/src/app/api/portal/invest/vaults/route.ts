import { NextRequest, NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import { loadPortalInvestVaults } from '@/lib/portal/investUpstream'
import type { PortalInvestVaultsPayload } from '@/lib/portal/investTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'

/** Section invest « coffres catalogue » — chargée indépendamment (shimmer dédié). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const origin = resolvePortalBffOrigin(request.nextUrl.origin)
  const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

  try {
    return NextResponse.json(await loadPortalInvestVaults(origin, locale))
  } catch (error) {
    console.error('[api/portal/invest/vaults GET]', error)
    return NextResponse.json({ vaults: [], partial: true } satisfies PortalInvestVaultsPayload)
  }
}
