import { NextResponse } from 'next/server'
import { getSiteBrandLogo } from '@/lib/cms/site-footer'
import { getLocaleOrDefault } from '@/config/locales'

/** Logo Vancelian depuis le CMS (`global_settings.footer_json.logoMediaId`). */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const locale = getLocaleOrDefault(searchParams.get('locale') ?? undefined)
    const brand = await getSiteBrandLogo(locale)
    return NextResponse.json(brand, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600',
      },
    })
  } catch (error) {
    console.error('[api/site/brand-logo]', error)
    return NextResponse.json({ logoUrl: null, logoAlt: null }, { status: 500 })
  }
}
