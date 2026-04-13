import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'

export interface HelpCollectionWithCount {
  id: string
  slug: string
  order: number
  title: string
  subtitle: string | null
  description: string | null
  articleCount: number
}

export interface HelpCategoryWithCount {
  id: string
  slug: string
  order: number
  title: string
  description: string | null
  articleCount: number
}

export interface HelpArticlePreview {
  id: string
  slug: string
  title: string
  standfirst: string | null
  updatedAt: Date
  publishedAt: Date | null
}

/**
 * Get all published collections with article counts
 */
export async function getHelpCollections(locale?: string): Promise<HelpCollectionWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collections = await prisma.helpCollection.findMany({
    where: { isPublished: true },
    orderBy: { order: 'asc' },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
      categories: {
        where: { isPublished: true },
        include: {
          articles: {
            where: { status: 'PUBLISHED' },
          },
        },
      },
    },
  })

  return collections
    .map((collection) => {
      const i18n = collection.i18n[0]
      if (!i18n) return null

      // Count articles across all categories in this collection
      const articleCount = collection.categories.reduce(
        (sum, cat) => sum + cat.articles.length,
        0
      )

      return {
        id: collection.id,
        slug: collection.slug,
        order: collection.order,
        title: i18n.title,
        subtitle: i18n.subtitle ?? null,
        description: i18n.description ?? null,
        articleCount,
      }
    })
    .filter((c): c is HelpCollectionWithCount => c !== null)
}

/**
 * Get collection by slug with categories
 */
export async function getHelpCollection(
  slug: string,
  locale?: string
): Promise<HelpCollectionWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
      categories: {
        where: { isPublished: true },
        orderBy: { order: 'asc' },
        include: {
          articles: {
            where: { status: 'PUBLISHED' },
          },
        },
      },
    },
  })

  if (!collection || !collection.isPublished) return null
  const i18n = collection.i18n[0]
  if (!i18n) return null

  const articleCount = collection.categories.reduce(
    (sum, cat) => sum + cat.articles.length,
    0
  )

  return {
    id: collection.id,
    slug: collection.slug,
    order: collection.order,
    title: i18n.title,
    subtitle: i18n.subtitle ?? null,
    description: i18n.description ?? null,
    articleCount,
  }
}

/**
 * Get categories for a collection
 */
export async function getHelpCategories(
  collectionSlug: string,
  locale?: string
): Promise<HelpCategoryWithCount[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      categories: {
        where: { isPublished: true },
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
          articles: {
            where: { status: 'PUBLISHED' },
          },
        },
      },
    },
  })

  if (!collection) return []

  return collection.categories
    .map((category) => {
      const i18n = category.i18n[0]
      if (!i18n) return null

      return {
        id: category.id,
        slug: category.slug,
        order: category.order,
        title: i18n.title,
        description: i18n.description ?? null,
        articleCount: category.articles.length,
      }
    })
    .filter((c): c is HelpCategoryWithCount => c !== null)
}

/**
 * Get collection by slug with categories (for categories grid)
 */
export async function getHelpCollectionWithCategories(
  collectionSlug: string,
  locale?: string
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
      categories: {
        where: { isPublished: true },
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
        },
      },
    },
  })

  if (!collection || !collection.isPublished) return null
  return collection
}

/**
 * Get category by slug
 */
export async function getHelpCategory(
  collectionSlug: string,
  categorySlug: string,
  locale?: string
): Promise<HelpCategoryWithCount | null> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      categories: {
        where: { slug: categorySlug, isPublished: true },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
          articles: {
            where: { status: 'PUBLISHED' },
            orderBy: { publishedAt: 'desc' },
            include: {
              i18n: {
                where: { locale: resolvedLocale },
                take: 1,
              },
            },
          },
        },
      },
    },
  })

  if (!collection) return null

  const category = collection.categories[0]
  if (!category) return null

  const i18n = category.i18n[0]
  if (!i18n) return null

  return {
    id: category.id,
    slug: category.slug,
    order: category.order,
    title: i18n.title,
    description: i18n.description ?? null,
    articleCount: category.articles.length,
  }
}

/**
 * Get articles for a category
 */
export async function getHelpArticles(
  collectionSlug: string,
  categorySlug: string,
  locale?: string
): Promise<HelpArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      categories: {
        where: { slug: categorySlug, isPublished: true },
        include: {
          articles: {
            where: { status: 'PUBLISHED' },
            orderBy: { publishedAt: 'desc' },
            include: {
              i18n: {
                where: { locale: resolvedLocale },
                take: 1,
              },
            },
          },
        },
      },
    },
  })

  if (!collection) return []

  const category = collection.categories[0]
  if (!category) return []

  return category.articles
    .map((article) => {
      const i18n = article.i18n[0]
      if (!i18n) return null

      return {
        id: article.id,
        slug: article.slug,
        title: i18n.title,
        standfirst: i18n.standfirst ?? null,
        updatedAt: article.updatedAt,
        publishedAt: article.publishedAt ?? null,
      }
    })
    .filter((a): a is HelpArticlePreview => a !== null)
}

/**
 * Get articles in a category by category ID
 */
export async function getHelpArticlesInCategory(
  categoryId: string,
  locale?: string
): Promise<HelpArticlePreview[]> {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const category = await prisma.helpCategory.findUnique({
    where: { id: categoryId },
    include: {
      articles: {
        where: { status: 'PUBLISHED' },
        orderBy: { publishedAt: 'desc' },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
        },
      },
    },
  })

  if (!category) return []

  return category.articles
    .map((article) => {
      const i18n = article.i18n[0]
      if (!i18n) return null

      return {
        id: article.id,
        slug: article.slug,
        title: i18n.title,
        standfirst: i18n.standfirst ?? null,
        updatedAt: article.updatedAt,
        publishedAt: article.publishedAt ?? null,
      }
    })
    .filter((a): a is HelpArticlePreview => a !== null)
}

/**
 * Get single article with blocks
 */
export async function getHelpArticle(
  collectionSlug: string,
  categorySlug: string,
  articleSlug: string,
  locale?: string
) {
  const cookieStore = await cookies()
  const resolvedLocale = locale || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

  const collection = await prisma.helpCollection.findUnique({
    where: { slug: collectionSlug },
    include: {
      i18n: {
        where: { locale: resolvedLocale },
        take: 1,
      },
      categories: {
        where: { slug: categorySlug, isPublished: true },
        include: {
          i18n: {
            where: { locale: resolvedLocale },
            take: 1,
          },
          articles: {
            where: { slug: articleSlug, status: 'PUBLISHED' },
            include: {
              i18n: {
                where: { locale: resolvedLocale },
                take: 1,
              },
              blocks: {
                where: { locale: resolvedLocale },
                orderBy: { order: 'asc' },
              },
              coverMedia: true,
            },
          },
        },
      },
    },
  })

  if (!collection) return null

  const category = collection.categories[0]
  if (!category) return null

  const article = category.articles[0]
  if (!article) return null

  const articleI18n = article.i18n[0]
  if (!articleI18n) return null

  const collectionI18n = collection.i18n[0]
  const categoryI18n = category.i18n[0]

  return {
    id: article.id,
    slug: article.slug,
    title: articleI18n.title,
    standfirst: articleI18n.standfirst ?? null,
    metaTitle: articleI18n.metaTitle,
    metaDescription: articleI18n.metaDescription,
    updatedAt: article.updatedAt,
    publishedAt: article.publishedAt ?? null,
    authorName: article.authorName,
    allowAnchors: article.allowAnchors,
    coverMedia: article.coverMedia,
    blocks: article.blocks,
    collection: {
      slug: collection.slug,
      title: collectionI18n?.title || collection.slug,
    },
    category: {
      slug: category.slug,
      title: categoryI18n?.title || category.slug,
    },
    locale: resolvedLocale,
  }
}

