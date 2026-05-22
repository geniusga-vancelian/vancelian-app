import { NextRequest, NextResponse } from 'next/server'
import { parseTop10NewsWidget } from '@/lib/portal/parseTop10NewsWidget'

const WIDGET_SLUG = 'top10news'

/** Feed news dashboard — même widget Builder que Flutter (`top10news`). */
export async function GET(request: NextRequest) {
  try {
    const locale = request.nextUrl.searchParams.get('locale')?.trim() || 'fr'
    const widgetUrl = new URL(
      `/api/mobile/flutter/widgets/${WIDGET_SLUG}`,
      request.nextUrl.origin,
    )
    widgetUrl.searchParams.set('locale', locale)

    const res = await fetch(widgetUrl, { cache: 'no-store' })
    if (!res.ok) {
      return NextResponse.json(
        { error: 'widget_unavailable', items: [] },
        { status: res.status === 404 ? 404 : 502 },
      )
    }

    const raw = await res.json()
    const parsed = parseTop10NewsWidget(raw)

    if (!parsed || parsed.items.length === 0) {
      return NextResponse.json({ title: 'Vancelian News', items: [], headerHref: '/blog' })
    }

    return NextResponse.json(parsed)
  } catch (error) {
    console.error('[api/portal/news-widget GET]', error)
    return NextResponse.json({ error: 'internal_error', items: [] }, { status: 500 })
  }
}
