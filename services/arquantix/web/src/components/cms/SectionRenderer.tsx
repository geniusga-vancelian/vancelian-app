/**
 * Component to render sections based on their key and data
 * Uses the section registry to map section keys to React components
 */

import { getSectionComponent } from '@/lib/sections/registry'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'
import type { PublicArticle } from '@/lib/blog/getPublicArticle'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import type { CmsSectionRecord, SectionPageRendererContext } from '@/lib/sections/sectionPageRendererTypes'

export type { SectionPageRendererContext } from '@/lib/sections/sectionPageRendererTypes'
export { mapDataToComponentProps } from '@/lib/sections/mapDataToComponentProps'

interface SectionRendererProps {
  section: CmsSectionRecord
  locale?: string
  category?: string
  page?: number
  /** Pagination du module `blog_mosaic` (distinct de `page` pour `blog_feed`). */
  mosaicPage?: number
  /** Filtre segment liste blog (market | company | analysis), à préserver dans les liens du mosaic. */
  blogSegment?: string
  // Help Center context props
  collectionSlug?: string
  categorySlug?: string
  articleSlug?: string
  searchQuery?: string
  /** Contexte page détail blog : article Prisma + médias déjà résolus. */
  blogArticle?: PublicArticle | null
  /** Contexte gabarit offre exclusive : payload Vault pour la page `/projects/[slug]` courante. */
  exclusiveOfferVaultPayload?: ExclusiveOfferVaultPayload | null
  rendererContext?: SectionPageRendererContext
  /** Blog CMS : premier bloc `blog_hero` ou `blog_article_hero` sous le menu primaire. */
  blogHeroBleedUnderNav?: boolean
}

export function SectionRenderer({
  section,
  locale,
  category,
  page,
  mosaicPage,
  blogSegment,
  collectionSlug,
  categorySlug,
  articleSlug,
  searchQuery,
  blogArticle,
  exclusiveOfferVaultPayload,
  rendererContext,
  blogHeroBleedUnderNav,
}: SectionRendererProps) {
  const { data } = section
  const key = typeof section.key === 'string' ? section.key.trim() : section.key
  const canonicalForBlog = resolveCanonicalSectionKey(key) ?? key

  /** Footer global : édité dans /admin/pages, rendu dans le layout racine. */
  if (key === 'footer') {
    return null
  }

  /** Normalement résolu dans `getPageSections` vers le type cible ; repli si référence invalide. */
  if (key === 'common_module_ref') {
    return null
  }

  // Get component from registry
  const Component = getSectionComponent(key)

  if (!Component) {
    // Fallback admin/debug : visible uniquement quand le registre n'a pas la clé
    // (incohérence schéma ↔ code). Non user-facing en production : exempté du
    // garde-fou i18n site (cf. siteHardcodedStringsScanner).
    return (
      <div className="bg-yellow-50 border border-yellow-200 p-4 my-4">
        <p className="text-sm text-yellow-800">
          {/* i18n-allow-next-line: fallback admin/debug — section inconnue */}
          <strong>Unknown section:</strong> {key}
        </p>
        <pre className="mt-2 text-xs overflow-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    )
  }

  const props = mapDataToComponentProps(
    key,
    data,
    locale,
    category,
    page,
    collectionSlug,
    categorySlug,
    articleSlug,
    searchQuery,
    blogArticle,
    rendererContext,
    exclusiveOfferVaultPayload,
    mosaicPage,
    blogSegment,
  )

  const merged =
    blogHeroBleedUnderNav === true &&
    (canonicalForBlog === 'blog_hero' || canonicalForBlog === 'blog_article_hero')
      ? { ...props, bleedUnderPrimaryNav: true }
      : props

  return <Component {...merged} />
}
