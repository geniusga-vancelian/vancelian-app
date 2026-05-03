import { defaultLocale, type Locale } from '@/config/locales'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'
import {
  buildLocalizedCmsPagePath,
  buildLocalizedHomePath,
  buildLocalizedProjectDetailPath,
} from '@/lib/i18n/publicLocalizedRouting'

/**
 * Chemin menu aligné sur le routing public.
 * - isRoot ou slug `home` → `/{locale}`
 * - pages Vault Builder (`vault_builder`) → `/{locale}/projects/{slug}`
 * - sinon → `/{locale}/{slug}`
 */
export function computeMenuItemUrlPath(
  isRoot: boolean,
  pageSlug: string | null | undefined,
  locale: Locale = defaultLocale,
  pageTemplate?: string | null,
): string {
  if (isRoot) {
    return buildLocalizedHomePath(locale)
  }

  if (!pageSlug) {
    return buildLocalizedHomePath(locale)
  }

  if (pageSlug === 'home') {
    return buildLocalizedHomePath(locale)
  }

  if (pageTemplate === VAULT_BUILDER_TEMPLATE) {
    return buildLocalizedProjectDetailPath(locale, pageSlug)
  }

  return buildLocalizedCmsPagePath(locale, pageSlug)
}


