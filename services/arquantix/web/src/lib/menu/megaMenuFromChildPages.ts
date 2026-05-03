/**
 * Construit le payload méga-menu à partir des pages enfants (CMS).
 */
import type { Locale } from '@/config/locales'
import { computeMenuItemUrlPath } from '@/lib/menu/computeUrlPath'
import {
  layoutMegaMenuColumns,
  type MegaMenuColumnPayload,
  type MegaMenuItemPayload,
} from '@/lib/menu/buildMegaMenuColumns'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'

export type MegaMenuPayload = {
  columns: MegaMenuColumnPayload[]
}

export type PageChildForMegaMenu = {
  id: string
  slug: string
  template: string
  title: string | null
  description: string | null
  pageI18n: Array<{
    locale: string
    title: string | null
    description: string | null
    navMegaCategory: string | null
    navMegaDescription: string | null
  }>
  navMegaIconMedia: { key: string; url: string } | null
}

export async function megaMenuPayloadFromChildPages(
  children: PageChildForMegaMenu[],
  locale: Locale,
): Promise<MegaMenuPayload | null> {
  if (children.length < 2) {
    return null
  }

  const withCat: (MegaMenuItemPayload & { category: string })[] = await Promise.all(
    children.map(async (c) => {
      const i18n =
        c.pageI18n.find((r) => r.locale === locale) ||
        c.pageI18n.find((r) => r.locale === DEFAULT_LOCALE) ||
        c.pageI18n[0]

      const title = (i18n?.title || c.title || c.slug || '').trim()
      const description = (
        i18n?.navMegaDescription ||
        i18n?.description ||
        c.description ||
        ''
      ).trim()
      const category = (i18n?.navMegaCategory || '').trim()
      const href = computeMenuItemUrlPath(false, c.slug, locale, c.template)

      let iconUrl: string | null = null
      if (c.navMegaIconMedia) {
        try {
          iconUrl = await getPresignedUrl(c.navMegaIconMedia.key, 3600)
        } catch {
          iconUrl = c.navMegaIconMedia.url
        }
      }

      return {
        id: c.id,
        title,
        description,
        href,
        iconUrl,
        category,
      }
    }),
  )

  const columns = layoutMegaMenuColumns(withCat)
  if (columns.length === 0) {
    return null
  }
  return { columns }
}
