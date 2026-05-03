import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { isValidLocale, type Locale } from '@/config/locales'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import {
  getNavShellStateForPathname,
  DEFAULT_NAV_SHELL,
} from '@/lib/cms/navShellContext'
import { getPublicLocaleFromPathname } from '@/lib/i18n/localizedExclusiveOfferPath'

export async function GET(request: NextRequest) {
  try {
    const path = request.nextUrl.searchParams.get('path') || '/'
    const preferDraft = request.nextUrl.searchParams.get('draft') === '1'
    const localeParam = request.nextUrl.searchParams.get('locale')
    const cookieStore = await cookies()
    const urlLocale = getPublicLocaleFromPathname(path)
    const locale =
      localeParam && isValidLocale(localeParam)
        ? (localeParam as Locale)
        : (resolvePublicLocale({
            cookieStore,
            searchParams: undefined,
            urlLocale,
          }) as Locale)
    const state = await getNavShellStateForPathname(path, locale, { preferDraft })
    return NextResponse.json(state)
  } catch {
    return NextResponse.json(DEFAULT_NAV_SHELL)
  }
}
