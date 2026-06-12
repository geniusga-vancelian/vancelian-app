import { NextRequest, NextResponse } from 'next/server'
import { loadPortalAcademyLibrary } from '@/lib/portal/academyUpstream'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { readPortalAccessToken } from '@/lib/portal/portalSession'
import type { PortalAcademyLibraryPayload } from '@/lib/portal/academyHubTypes'

/** Academy — section bibliothèque (articles pédagogiques CMS). */
export async function GET(request: NextRequest) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  try {
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    return NextResponse.json(await loadPortalAcademyLibrary(locale))
  } catch (error) {
    console.error('[api/portal/academy/library GET]', error)
    return NextResponse.json({ academy: [], partial: true } satisfies PortalAcademyLibraryPayload)
  }
}
