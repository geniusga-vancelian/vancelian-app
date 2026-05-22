import { NextRequest, NextResponse } from 'next/server'
import { getLocaleOrDefault } from '@/config/locales'
import { getPortalAuthContent } from '@/lib/cms/portal-auth'

export async function GET(request: NextRequest) {
  try {
    const locale = getLocaleOrDefault(request.nextUrl.searchParams.get('locale'))
    const content = await getPortalAuthContent(locale)
    return NextResponse.json(content, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    })
  } catch (e) {
    console.error('GET /api/site/portal-auth', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
