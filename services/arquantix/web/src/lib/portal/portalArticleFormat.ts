import type { AppNewsCategoryDot } from '@/components/design-system/app/AppNewsStackedList'
import { academyCategoryTone } from '@/lib/portal/academyFormat'
import type { PortalArticleView } from '@/lib/portal/portalArticleTypes'
import { portalArticleTypeLabel } from '@/lib/portal/portalArticleTypes'

export function authorInitials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

export function resolveArticleSlug(view: PortalArticleView): string {
  return view.kind === 'editorial' ? view.article.slug : view.slug
}

export function resolveArticleHeroTags(view: PortalArticleView): {
  categoryLabel: string
  sectionLabel: string
  categoryTone: AppNewsCategoryDot
} {
  if (view.kind === 'academy') {
    return {
      categoryLabel: view.categoryTitle,
      sectionLabel: view.collectionTitle || 'Academy',
      categoryTone: academyCategoryTone(view.categoryTitle.toLowerCase()),
    }
  }

  const category = view.article.categories[0]
  return {
    categoryLabel: category?.label ?? portalArticleTypeLabel(view),
    sectionLabel: portalArticleTypeLabel(view),
    categoryTone: academyCategoryTone(category?.slug),
  }
}
