import { NextRequest, NextResponse } from 'next/server'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import {
  loadPortalInvestOffers,
  loadPortalInvestVaults,
} from '@/lib/portal/investUpstream'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'

/**
 * Agrégateur de compatibilité (preview navigation + écrans legacy).
 * Compose les loaders de section fail-soft : renvoie toujours 200 avec un
 * payload partiel plutôt qu'une erreur, pour éviter la cassure plein écran.
 */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const origin = resolvePortalBffOrigin(request.nextUrl.origin)
  const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

  try {
    const [offersSection, vaultsSection] = await Promise.all([
      loadPortalInvestOffers(origin, locale),
      loadPortalInvestVaults(origin, locale),
    ])

    const payload: PortalInvestPayload = {
      offers: offersSection.offers,
      vaults: vaultsSection.vaults,
      partial: Boolean(offersSection.partial || vaultsSection.partial),
    }

    return NextResponse.json(payload)
  } catch (error) {
    console.error('[api/portal/invest GET]', error)
    return NextResponse.json({
      offers: [],
      vaults: [],
      partial: true,
    } satisfies PortalInvestPayload)
  }
}
