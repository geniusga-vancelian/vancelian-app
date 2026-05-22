import { NextRequest, NextResponse } from 'next/server'
import { isValidLocale, type Locale } from '@/config/locales'
import { getSiteFooterData } from '@/lib/cms/site-footer'

/** Données footer publiques pour la coquille client (cache par locale). */
export async function GET(request: NextRequest) {
  try {
    const localeParam = request.nextUrl.searchParams.get('locale')
    const locale =
      localeParam && isValidLocale(localeParam) ? (localeParam as Locale) : undefined
    const data = await getSiteFooterData(locale)
    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    })
  } catch (error) {
    console.error('[api/site/footer]', error)
    return NextResponse.json({ error: 'Footer unavailable' }, { status: 500 })
  }
}
