import { redirect } from 'next/navigation'
import { getSessionFromCookie } from '@/lib/auth'
import { resolveHomePageCmsSlug } from '@/lib/cms/resolveHomePageCmsSlug'
import { getSiteI18nSettingsCached } from '@/lib/i18n/siteI18nSettings'

/**
 * Entrée aperçu site depuis `console.*` / local : `/preview` → home CMS en brouillon.
 */
export default async function PreviewIndexPage() {
  const session = await getSessionFromCookie()
  if (!session) {
    redirect('/admin/login?redirect=%2Fpreview')
  }

  const [homeSlug, siteI18n] = await Promise.all([
    resolveHomePageCmsSlug(),
    getSiteI18nSettingsCached(),
  ])

  redirect(
    `/preview/${encodeURIComponent(homeSlug)}?locale=${encodeURIComponent(siteI18n.defaultLocale)}`,
  )
}
