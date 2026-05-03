import Link from 'next/link'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

interface SectionHelpBreadcrumbsProps {
  rootLabel?: string
  separator?: string
  locale: string
  collectionSlug?: string
  collectionTitle?: string
  categorySlug?: string
  categoryTitle?: string
  articleTitle?: string
}

export function SectionHelpBreadcrumbs({
  rootLabel = 'Toutes les collections',
  separator = '›',
  locale,
  collectionSlug,
  collectionTitle,
  categorySlug,
  categoryTitle,
  articleTitle,
}: SectionHelpBreadcrumbsProps) {
  const items: Array<{ label: string; href?: string }> = []

  // Root
  items.push({ label: rootLabel, href: '/help' })

  // Collection
  if (collectionSlug && collectionTitle) {
    items.push({ label: collectionTitle, href: `/help/${collectionSlug}` })
  }

  // Category
  if (categorySlug && categoryTitle && collectionSlug) {
    items.push({ label: categoryTitle, href: `/help/${collectionSlug}/${categorySlug}` })
  }

  // Article (no link)
  if (articleTitle) {
    items.push({ label: articleTitle })
  }

  return (
    <nav aria-label={siteCommonCta(locale, 'breadcrumb_aria')}>
      <ol className="flex items-center space-x-2 text-sm text-gray-500">
        {items.map((item, index) => (
          <li key={index} className="flex items-center">
            {index > 0 && (
              <span className="mx-2 text-gray-400" aria-hidden="true">
                {separator}
              </span>
            )}
            {item.href ? (
              <Link
                href={item.href}
                className="hover:text-gray-700 transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className="text-gray-900 font-medium">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

