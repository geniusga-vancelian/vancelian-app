import { NextRequest, NextResponse } from 'next/server'
import { loadPortalAcademyEditorial } from '@/lib/portal/academyUpstream'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalAcademyEditorialPayload } from '@/lib/portal/academyHubTypes'

/** Academy — section éditoriale (actualités + analyses). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    return NextResponse.json(await loadPortalAcademyEditorial(bffOrigin, locale))
  } catch (error) {
    console.error('[api/portal/academy/editorial GET]', error)
    return NextResponse.json({
      featured: null,
      highlighted: [],
      marketNews: [],
      vancelianNews: [],
      analysis: [],
      partial: true,
    } satisfies PortalAcademyEditorialPayload)
  }
}
