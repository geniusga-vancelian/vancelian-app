import { cookies, headers } from 'next/headers'
import { resolveLayoutLocale } from '@/lib/i18n/resolveLayoutLocale'
import { getSiteFooterData } from '@/lib/cms/site-footer'
import { GlobalFooterClient } from './GlobalFooterClient'

export async function SiteFooter() {
  const headersList = await headers()
  const cookieStore = await cookies()
  const locale = resolveLayoutLocale({
    pathLocaleHeader: headersList.get('x-arq-locale'),
    cookieStore,
  })
  const data = await getSiteFooterData(locale)
  return <GlobalFooterClient data={data} />
}
