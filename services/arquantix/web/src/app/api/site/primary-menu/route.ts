import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { type Locale, isValidLocale } from '@/config/locales'
import { getPublicLocaleFromPathname } from '@/lib/i18n/localizedExclusiveOfferPath'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'
import { getSiteI18nSettingsCached, shouldShowPublicLanguageSwitcher } from '@/lib/i18n/siteI18nSettings'
import { getSiteMenuTheme } from '@/lib/cms/site-menu-theme'

export async function GET(request: NextRequest) {
  try {
    const path = request.nextUrl.searchParams.get('path')
    const localeParam = request.nextUrl.searchParams.get('locale')
    const cookieStore = await cookies()
    const site = await getSiteI18nSettingsCached()

    const urlLocale = path ? getPublicLocaleFromPathname(path) : null
    const requestedLocale =
      localeParam && isValidLocale(localeParam)
        ? (localeParam as Locale)
        : resolvePublicLocale({
            cookieStore,
            searchParams: undefined,
            urlLocale,
            fallbackLocale: site.defaultLocale,
          })

    const [menu, theme] = await Promise.all([
      getPrimaryMenu(requestedLocale, {
        languageSwitcherEnabled: shouldShowPublicLanguageSwitcher(site),
      }),
      getSiteMenuTheme(),
    ])
    return NextResponse.json({ items: menu, theme })
  } catch {
    return NextResponse.json({ items: [] })
  }
}
