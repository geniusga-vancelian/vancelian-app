import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ArticleBlockType, ContentStatus } from '@prisma/client'
import { mergeArticleBlockLocalizedData } from '@/lib/blog/normalizeArticleBlocks'
import { deriveGroupingTags, tagSlugToDisplayTitle } from '@/lib/articles/collectionTags'

function matchesAcademyCategoryFilter(
  categorySlug: string | null,
  collectionTagsRaw: unknown,
  academyCategorySlug: string | null,
): boolean {
  if (!categorySlug) return true
  const tags = deriveGroupingTags(collectionTagsRaw, academyCategorySlug)
  return tags.includes(categorySlug)
}

/**
 * GET /api/academy/search?q=&locale=&collection=&category=&limit=
 *
 * Recherche fulltext (côté JS, sur titre + standfirst + texte des blocs)
 * sur `Article(articleType='ACADEMY')`. Tri : matches dans le titre d'abord,
 * puis par `updatedAt desc`. Symétrique à `/api/help/search` mais sans branch
 * legacy puisque Academy n'a pas de table dédiée.
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

    if (!query.trim() || query.trim().length < 2) {
      return NextResponse.json({ query: query.trim(), results: [] })
    }

    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)
    const queryLower = query.toLowerCase().trim()

    const articles = await prisma.article.findMany({
      where: buildAcademyWhere(collectionSlug, categorySlug),
      include: {
        i18n: { where: { locale }, take: 1 },
        blocks: {
          orderBy: { order: 'asc' },
          include: { i18n: { where: { locale }, take: 1 } },
        },
        academyCollection: { include: { i18n: { where: { locale }, take: 1 } } },
        academyCategory: { include: { i18n: { where: { locale }, take: 1 } } },
      },
      orderBy: { publishedAt: 'desc' },
    })

    const hits: SearchHit[] = []

    for (const article of articles) {
      if (!article.academyCollection) continue
      if (
        !matchesAcademyCategoryFilter(
          categorySlug,
          article.collectionTags,
          article.academyCategory?.slug ?? null,
        )
      ) {
        continue
      }
      const i18n = article.i18n[0]
      if (!i18n) continue
      const slug = article.academySlug ?? article.slug
      const blocksTexts = article.blocks.map((b) =>
        extractTextFromBlock(String(b.type), mergeArticleBlockLocalizedData(b)),
      )
      const tags = deriveGroupingTags(article.collectionTags, article.academyCategory?.slug ?? null)
      const catSlug = tags[0] ?? article.academyCategory?.slug ?? 'general'
      const catTitle = article.academyCategory?.i18n[0]?.title ?? tagSlugToDisplayTitle(catSlug)
      const hit = matchAndBuildHit({
        id: article.id,
        slug,
        title: i18n.title,
        standfirst: i18n.standfirst ?? '',
        blocksTexts,
        queryLower,
        updatedAt: article.updatedAt,
        collection: {
          slug: article.academyCollection.slug,
          title: article.academyCollection.i18n[0]?.title ?? article.academyCollection.slug,
        },
        category: {
          slug: catSlug,
          title: catTitle,
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
    console.error('[Academy Search API] Error:', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        query: '',
        results: [],
      },
      { status: 500 },
    )
  }
}

function buildAcademyWhere(collectionSlug: string | null, _categorySlug: string | null) {
  const where: Record<string, unknown> = {
    articleType: 'ACADEMY',
    status: ContentStatus.PUBLISHED,
    academyCollectionId: { not: null },
  }
  if (collectionSlug) {
    where.academyCollection = { slug: collectionSlug, isPublished: true }
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
  collection: { slug: string; title: string }
  category: { slug: string; title: string }
}): SearchHit | null {
  const titleLower = params.title.toLowerCase()
  const standfirstLower = params.standfirst.toLowerCase()

  let matches = titleLower.includes(params.queryLower) || standfirstLower.includes(params.queryLower)
  if (!matches) {
    for (const text of params.blocksTexts) {
      if (text.toLowerCase().includes(params.queryLower)) {
        matches = true
        break
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
