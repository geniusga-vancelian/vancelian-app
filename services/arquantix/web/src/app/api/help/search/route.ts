import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ArticleBlockType, ContentStatus } from '@prisma/client'
import { mergeArticleBlockLocalizedData } from '@/lib/blog/normalizeArticleBlocks'
import { deriveGroupingTags, tagSlugToDisplayTitle } from '@/lib/articles/collectionTags'

function matchesHelpCategoryFilter(
  categorySlug: string | null,
  collectionTagsRaw: unknown,
  helpCategorySlug: string | null,
): boolean {
  if (!categorySlug) return true
  const tags = deriveGroupingTags(collectionTagsRaw, helpCategorySlug)
  return tags.includes(categorySlug)
}

/**
 * GET /api/help/search?q=&locale=&collection=&category=&limit=&titleOnly=&minLength=
 *
 * Uniquement contenu **Help** (`Article` type HELP + `HelpArticle` legacy) —
 * pas News ni Academy.
 *
 * Phase 3.3 : recherche fulltext (côté JS, sur titre + standfirst + texte
 * des blocs) qui agrège `Article(articleType='HELP')` unifié ET
 * `HelpArticle` legacy. Dédup par `helpSlug` (priorité unifié). Tri :
 * matches dans le titre d'abord, puis par `updatedAt desc`.
 */

function extractTextFromBlock(type: string, dataInput: unknown): string {
  const data = (dataInput as Record<string, unknown> | null | undefined) ?? {}
  switch (type) {
    case ArticleBlockType.PARAGRAPH:
    case ArticleBlockType.QUOTE:
    case ArticleBlockType.HEADING:
      return typeof data.text === 'string' ? data.text : ''
    case ArticleBlockType.BULLET_LIST:
      return Array.isArray(data.items) ? (data.items as unknown[]).join(' ') : ''
    default:
      return ''
  }
}

function generateSnippet(blocksTexts: string[]): string {
  for (const text of blocksTexts) {
    if (text && text.length > 20) {
      return text.substring(0, 150) + (text.length > 150 ? '...' : '')
    }
  }
  return ''
}

interface SearchHit {
  id: string
  slug: string
  question: string
  snippet: string
  collection: { slug: string; title: string }
  category: { slug: string; title: string }
  updatedAt: Date
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const query = searchParams.get('q') || ''
    const localeParam = searchParams.get('locale')
    const collectionSlug = searchParams.get('collection')
    const categorySlug = searchParams.get('category')
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 50)
    const titleOnly =
      searchParams.get('titleOnly') === '1' || searchParams.get('titleOnly') === 'true'
    const minLengthRaw = parseInt(searchParams.get('minLength') || '2', 10)
    const minLength = Number.isFinite(minLengthRaw)
      ? Math.min(Math.max(minLengthRaw, 1), 20)
      : 2

    if (!query.trim() || query.trim().length < minLength) {
      return NextResponse.json({ query: query.trim(), results: [] })
    }

    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)
    const queryLower = query.toLowerCase().trim()

    const [legacyArticles, unifiedArticles] = await Promise.all([
      prisma.helpArticle.findMany({
        where: buildLegacyWhere(collectionSlug, categorySlug),
        include: {
          i18n: { where: { locale }, take: 1 },
          blocks: { where: { locale }, orderBy: { order: 'asc' } },
          category: {
            include: {
              collection: { include: { i18n: { where: { locale }, take: 1 } } },
              i18n: { where: { locale }, take: 1 },
            },
          },
        },
        orderBy: { publishedAt: 'desc' },
      }),
      prisma.article.findMany({
        where: buildUnifiedWhere(collectionSlug, categorySlug),
        include: {
          i18n: { where: { locale }, take: 1 },
          blocks: {
            orderBy: { order: 'asc' },
            include: { i18n: { where: { locale }, take: 1 } },
          },
          helpCollection: { include: { i18n: { where: { locale }, take: 1 } } },
          helpCategory: { include: { i18n: { where: { locale }, take: 1 } } },
        },
        orderBy: { publishedAt: 'desc' },
      }),
    ])

    const hits: SearchHit[] = []
    const taken = new Set<string>()

    for (const article of unifiedArticles) {
      if (!article.helpCollection) continue
      if (
        !matchesHelpCategoryFilter(
          categorySlug,
          article.collectionTags,
          article.helpCategory?.slug ?? null,
        )
      ) {
        continue
      }
      const i18n = article.i18n[0]
      if (!i18n) continue
      const slug = article.helpSlug ?? article.slug
      const blocksTexts = article.blocks.map((b) =>
        extractTextFromBlock(String(b.type), mergeArticleBlockLocalizedData(b)),
      )
      const tags = deriveGroupingTags(article.collectionTags, article.helpCategory?.slug ?? null)
      const catSlug = tags[0] ?? article.helpCategory?.slug ?? 'general'
      const catTitle = article.helpCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(catSlug)
      const hit = matchAndBuildHit({
        id: article.id,
        slug,
        title: i18n.title,
        standfirst: i18n.standfirst ?? '',
        blocksTexts,
        queryLower,
        updatedAt: article.updatedAt,
        titleOnly,
        collection: {
          slug: article.helpCollection.slug,
          title: article.helpCollection.i18n[0]?.title ?? article.helpCollection.slug,
        },
        category: {
          slug: catSlug,
          title: catTitle,
        },
      })
      if (hit) {
        hits.push(hit)
        taken.add(slug)
      }
    }

    for (const article of legacyArticles) {
      if (categorySlug && article.category.slug !== categorySlug) continue
      if (taken.has(article.slug)) continue
      const i18n = article.i18n[0]
      if (!i18n) continue
      const blocksTexts = article.blocks.map((b) => extractTextFromBlock(String(b.type), b.data))
      const hit = matchAndBuildHit({
        id: article.id,
        slug: article.slug,
        title: i18n.title,
        standfirst: i18n.standfirst ?? '',
        blocksTexts,
        queryLower,
        updatedAt: article.updatedAt,
        titleOnly,
        collection: {
          slug: article.category.collection.slug,
          title: article.category.collection.i18n[0]?.title || article.category.collection.slug,
        },
        category: {
          slug: article.category.slug,
          title: article.category.i18n[0]?.title || article.category.slug,
        },
      })
      if (hit) hits.push(hit)
    }

    hits.sort((a, b) => {
      const aTitleMatch = a.question.toLowerCase().includes(queryLower)
      const bTitleMatch = b.question.toLowerCase().includes(queryLower)
      if (aTitleMatch && !bTitleMatch) return -1
      if (!aTitleMatch && bTitleMatch) return 1
      return b.updatedAt.getTime() - a.updatedAt.getTime()
    })

    return NextResponse.json({
      query: query.trim(),
      results: hits.slice(0, limit),
    })
  } catch (error) {
    console.error('[Help Search API] Error:', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        query: '',
        results: [],
      },
      { status: 500 }
    )
  }
}

function buildLegacyWhere(collectionSlug: string | null, categorySlug: string | null) {
  const where: Record<string, unknown> = {
    status: ContentStatus.PUBLISHED,
  }
  if (collectionSlug || categorySlug) {
    where.category = {
      ...(categorySlug ? { slug: categorySlug } : {}),
      isPublished: true,
      collection: {
        ...(collectionSlug ? { slug: collectionSlug } : {}),
        isPublished: true,
      },
    }
  }
  return where
}

function buildUnifiedWhere(collectionSlug: string | null, _categorySlug: string | null) {
  const where: Record<string, unknown> = {
    articleType: 'HELP',
    status: ContentStatus.PUBLISHED,
    helpCollectionId: { not: null },
  }
  if (collectionSlug) {
    where.helpCollection = { slug: collectionSlug, isPublished: true }
  }
  return where
}

function matchAndBuildHit(params: {
  id: string
  slug: string
  title: string
  standfirst: string
  blocksTexts: string[]
  queryLower: string
  updatedAt: Date
  titleOnly: boolean
  collection: { slug: string; title: string }
  category: { slug: string; title: string }
}): SearchHit | null {
  const titleLower = params.title.toLowerCase()
  const standfirstLower = params.standfirst.toLowerCase()

  let matches: boolean
  if (params.titleOnly) {
    matches = titleLower.includes(params.queryLower)
  } else {
    matches = titleLower.includes(params.queryLower) || standfirstLower.includes(params.queryLower)
    if (!matches) {
      for (const text of params.blocksTexts) {
        if (text.toLowerCase().includes(params.queryLower)) {
          matches = true
          break
        }
      }
    }
  }
  if (!matches) return null

  let snippet = params.standfirst || ''
  if (!snippet) snippet = generateSnippet(params.blocksTexts)
  if (snippet.length > 200) snippet = snippet.substring(0, 200) + '...'

  return {
    id: params.id,
    slug: params.slug,
    question: params.title,
    snippet: snippet || params.title,
    collection: params.collection,
    category: params.category,
    updatedAt: params.updatedAt,
  }
}
