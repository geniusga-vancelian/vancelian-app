import { NextRequest, NextResponse } from 'next/server'

import {
  loadPortalAcademyEditorial,
  loadPortalAcademyLibrary,
} from '@/lib/portal/academyUpstream'
import type { PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

/**
 * Agrégateur Academy (compat). Le client préfère désormais les sections
 * /academy/editorial + /academy/library en chargement progressif.
 */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE

    const [editorial, library] = await Promise.all([
      loadPortalAcademyEditorial(bffOrigin, locale),
      loadPortalAcademyLibrary(locale),
    ])

    const payload: PortalAcademyHubPayload = {
      featured: editorial.featured,
      highlighted: editorial.highlighted,
      marketNews: editorial.marketNews,
      vancelianNews: editorial.vancelianNews,
      analysis: editorial.analysis,
      academy: library.academy,
    }

    return NextResponse.json(payload)
  } catch (err) {
    console.error('[api/portal/academy] GET failed', err)
    return NextResponse.json({
      featured: null,
      highlighted: [],
      marketNews: [],
      vancelianNews: [],
      analysis: [],
      academy: [],
    } satisfies PortalAcademyHubPayload)
  }
}
