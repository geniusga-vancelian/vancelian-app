import Link from 'next/link'
import { prisma } from '@/lib/prisma'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault } from '@/config/locales'

interface SectionBlogCategoryNavProps {
  title?: string
  showTitle?: boolean
  allLabel?: string
  locale: string
  currentCategory?: string
}

export async function SectionBlogCategoryNav({
  title,
  showTitle = false,
  allLabel = 'All',
  locale,
  currentCategory,
}: SectionBlogCategoryNavProps) {
  const activeLocale = getLocaleOrDefault(locale)
  const blogBasePath = `/${activeLocale}/blog`

  // Fetch categories with i18n
  const categoriesRaw = await prisma.articleCategory.findMany({
    where: { isActive: true },
    orderBy: [{ order: 'asc' }, { label: 'asc' }],
    include: {
      i18n: true,
    },
  })

  // Resolve labels for requested locale
  const categories = categoriesRaw.map((category) => ({
    id: category.id,
    slug: category.slug,
    label: resolveLabelWithFallback({
      requestedLocale: locale,
      baseLabel: category.label,
      i18nRows: category.i18n.map((i18n) => ({
        locale: i18n.locale,
        label: i18n.label,
      })),
    }),
  }))

  if (categories.length === 0) {
    return null
  }

  return (
    <div className="mb-12">
      {showTitle && title && (
        <h2 className="text-2xl font-bold text-gray-900 mb-6">{title}</h2>
      )}
      <nav className="flex flex-wrap gap-2">
        <Link
          href={blogBasePath}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            !currentCategory
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          {allLabel}
        </Link>
        {categories.map((cat) => (
          <Link
            key={cat.id}
            href={`${blogBasePath}?category=${cat.slug}`}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              currentCategory === cat.slug
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cat.label}
          </Link>
        ))}
      </nav>
    </div>
  )
}









