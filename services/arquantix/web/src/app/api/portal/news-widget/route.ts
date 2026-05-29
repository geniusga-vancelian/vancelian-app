import { NextRequest, NextResponse } from 'next/server'
import { loadPortalTop10NewsWidget } from '@/lib/portal/loadTop10NewsWidget'
import { PORTAL_CONTENT_LOCALE } from '@/lib/portal/portalContentLocale'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { resolveRequestPublicOrigin } from '@/lib/http/resolveRequestPublicOrigin'

/** Feed news dashboard — même widget Builder que Flutter (`top10news`). */
export async function GET(request: NextRequest) {
  try {
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || PORTAL_CONTENT_LOCALE
    const parsed = await loadPortalTop10NewsWidget(locale, resolveRequestPublicOrigin(request))

    if (!parsed || parsed.items.length === 0) {
      return NextResponse.json({ title: 'Latest news', items: [], headerHref: PORTAL_ROUTES.academy })
    }

    return NextResponse.json(parsed)
  } catch (error) {
    console.error('[api/portal/news-widget GET]', error)
    return NextResponse.json({ error: 'internal_error', items: [] }, { status: 500 })
  }
}
