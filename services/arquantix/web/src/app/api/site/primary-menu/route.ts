import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { type Locale, isValidLocale } from '@/config/locales'
import { getPublicLocaleFromPathname } from '@/lib/i18n/localizedExclusiveOfferPath'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'

export async function GET(request: NextRequest) {
  try {
    const path = request.nextUrl.searchParams.get('path')
    const localeParam = request.nextUrl.searchParams.get('locale')
    const cookieStore = await cookies()

    const urlLocale = path ? getPublicLocaleFromPathname(path) : null
    const requestedLocale =
      localeParam && isValidLocale(localeParam)
        ? (localeParam as Locale)
        : resolvePublicLocale({
            cookieStore,
            searchParams: undefined,
            urlLocale,
          })

    const menu = await getPrimaryMenu(requestedLocale)
    return NextResponse.json({ items: menu })
  } catch {
    return NextResponse.json({ items: [] })
  }
}
