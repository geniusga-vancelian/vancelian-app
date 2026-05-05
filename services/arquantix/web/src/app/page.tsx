import { cookies, headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { pickLocaleForRootFromSources } from '@/lib/i18n/rootLocaleRedirect'
import { ARQUANTIX_LOCALE_COOKIE } from '@/lib/i18n/locale-server'
import { getSiteI18nSettingsCached } from '@/lib/i18n/siteI18nSettings'

function pickLocaleQuery(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): string | null {
  if (!searchParams) return null
  const v = searchParams.locale
  if (Array.isArray(v)) return v[0] ?? null
  return v ?? null
}

/**
 * `/` redirige vers `/{locale}` (même logique que le middleware ; repli si le middleware est contourné).
 * La home indexable est `/fr`, `/en`, `/it` (phase 2A).
 */
export default async function RootPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>
}) {
  const cookieStore = await cookies()
  const hdrs = await headers()
  const site = await getSiteI18nSettingsCached()
  const locale = site.multilingualEnabled
    ? pickLocaleForRootFromSources({
        localeQuery: pickLocaleQuery(searchParams),
        cookieLocale: cookieStore.get(ARQUANTIX_LOCALE_COOKIE)?.value,
        acceptLanguage: hdrs.get('accept-language'),
        fallbackLocale: site.defaultLocale,
      })
    : site.defaultLocale
  redirect(`/${locale}`)
}
