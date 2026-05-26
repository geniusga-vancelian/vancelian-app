import { NextRequest, NextResponse } from 'next/server'
import { loadPortalTop10NewsWidget } from '@/lib/portal/loadTop10NewsWidget'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

/** Feed news dashboard — même widget Builder que Flutter (`top10news`). */
export async function GET(request: NextRequest) {
  try {
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
    const parsed = await loadPortalTop10NewsWidget(locale, request.nextUrl.origin)

    if (!parsed || parsed.items.length === 0) {
      return NextResponse.json({ title: 'Latest news', items: [], headerHref: PORTAL_ROUTES.academy })
    }

    return NextResponse.json(parsed)
  } catch (error) {
    console.error('[api/portal/news-widget GET]', error)
    return NextResponse.json({ error: 'internal_error', items: [] }, { status: 500 })
  }
}
