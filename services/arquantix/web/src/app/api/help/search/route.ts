import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ArticleBlockType, ContentStatus } from '@prisma/client'

/**
 * Extract plain text from a block's JSON data
 */
function extractTextFromBlock(block: any): string {
  const data = block.data as any
  switch (block.type) {
    case ArticleBlockType.PARAGRAPH:
    case ArticleBlockType.QUOTE:
      return data.text || ''
    case ArticleBlockType.HEADING:
      return data.text || ''
    case ArticleBlockType.BULLET_LIST:
      return Array.isArray(data.items) ? data.items.join(' ') : ''
    default:
      return ''
  }
}

/**
 * Generate a snippet from article blocks (first paragraph or heading)
 */
function generateSnippet(blocks: any[]): string {
  for (const block of blocks) {
    const text = extractTextFromBlock(block)
    if (text && text.length > 20) {
      return text.substring(0, 150) + (text.length > 150 ? '...' : '')
    }
  }
  return ''
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

    if (process.env.NODE_ENV !== 'production') {
      console.debug('[Help Search API] Starting search:', {
        query: query.trim(),
        queryLength: query.trim().length,
        locale,
        collectionSlug,
        categorySlug,
        limit,
      })
    }

    // Build where clause for articles
    const where: any = {
      status: ContentStatus.PUBLISHED,
      i18n: {
        some: {
          locale,
        },
      },
    }

    // Filter by collection if provided
    if (collectionSlug) {
      where.category = {
        collection: {
          slug: collectionSlug,
          isPublished: true,
        },
        isPublished: true,
      }
    }

    // Filter by category if provided
    if (categorySlug) {
      where.category = {
        ...where.category,
        slug: categorySlug,
        isPublished: true,
      }
    }

    // Fetch all published articles with their blocks and i18n
    const articles = await prisma.helpArticle.findMany({
      where,
      include: {
        i18n: {
          where: { locale },
          take: 1,
        },
        blocks: {
          where: { locale },
          orderBy: { order: 'asc' },
        },
        category: {
          include: {
            collection: {
              include: {
                i18n: {
                  where: { locale },
                  take: 1,
                },
              },
            },
            i18n: {
              where: { locale },
              take: 1,
            },
          },
        },
      },
      orderBy: { publishedAt: 'desc' },
    })

    if (process.env.NODE_ENV !== 'production') {
      console.debug('[Help Search API] Found', articles.length, 'articles to search through')
    }

    const queryLower = query.toLowerCase().trim()
    const results: Array<{
      id: string
      slug: string
      question: string
      snippet: string
      collection: { slug: string; title: string }
      category: { slug: string; title: string }
      updatedAt: Date
    }> = []

    // Search through articles
    for (const article of articles) {
      const i18n = article.i18n[0]
      if (!i18n) continue

      const title = i18n.title || ''
      const standfirst = i18n.standfirst || ''
      const titleLower = title.toLowerCase()
      const standfirstLower = standfirst.toLowerCase()

      // Check if query matches title or standfirst
      let matches = titleLower.includes(queryLower) || standfirstLower.includes(queryLower)

      // If not, search in blocks
      if (!matches) {
        for (const block of article.blocks) {
          const blockText = extractTextFromBlock(block).toLowerCase()
          if (blockText.includes(queryLower)) {
            matches = true
            break
          }
        }
      }

      if (matches) {
        // Generate snippet
        let snippet = standfirst || ''
        if (!snippet) {
          snippet = generateSnippet(article.blocks)
        }
        if (snippet.length > 200) {
          snippet = snippet.substring(0, 200) + '...'
        }

        const collectionI18n = article.category.collection.i18n[0]
        const categoryI18n = article.category.i18n[0]

        results.push({
          id: article.id,
          slug: article.slug,
          question: title,
          snippet: snippet || title,
          collection: {
            slug: article.category.collection.slug,
            title: collectionI18n?.title || article.category.collection.slug,
          },
          category: {
            slug: article.category.slug,
            title: categoryI18n?.title || article.category.slug,
          },
          updatedAt: article.updatedAt,
        })
      }
    }

    // Sort by relevance (title matches first, then by date)
    results.sort((a, b) => {
      const aTitleMatch = a.question.toLowerCase().includes(queryLower)
      const bTitleMatch = b.question.toLowerCase().includes(queryLower)
      if (aTitleMatch && !bTitleMatch) return -1
      if (!aTitleMatch && bTitleMatch) return 1
      return b.updatedAt.getTime() - a.updatedAt.getTime()
    })

    const limitedResults = results.slice(0, limit)

    if (process.env.NODE_ENV !== 'production') {
      console.debug('[Help Search API] Search completed:', {
        totalMatches: results.length,
        limitedResults: limitedResults.length,
        query: query.trim(),
      })
    }

    return NextResponse.json({
      query: query.trim(),
      results: limitedResults,
    })
  } catch (error) {
    console.error('[Help Search API] Error:', error)
    if (process.env.NODE_ENV !== 'production') {
      console.error('[Help Search API] Error stack:', error instanceof Error ? error.stack : 'No stack trace')
    }
    return NextResponse.json(
      { 
        error: 'Internal server error', 
        query: '',
        results: [] 
      },
      { status: 500 }
    )
  }
}
