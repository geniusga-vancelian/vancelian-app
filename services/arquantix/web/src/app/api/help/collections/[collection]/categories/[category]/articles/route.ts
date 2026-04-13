import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ContentStatus } from '@prisma/client'

function normalizeTags(raw: unknown) {
  let source: unknown = raw
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return []
    }
  }
  if (!Array.isArray(source)) return []
  const validTypes = new Set(['THEMATIC_CATEGORY', 'INVESTMENT_TYPE', 'EXCLUSIVE_OFFER'])
  return source
    .filter((item) => {
      if (!item || typeof item !== 'object') return false
      const row = item as Record<string, unknown>
      return (
        typeof row.type === 'string' &&
        validTypes.has(row.type) &&
        typeof row.id === 'string' &&
        typeof row.slug === 'string' &&
        typeof row.label === 'string'
      )
    })
    .map((item) => {
      const row = item as Record<string, string>
      return {
        type: row.type,
        id: row.id,
        slug: row.slug,
        label: row.label,
      }
    })
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string }> }
) {
  try {
    const { collection, category } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

    const foundCollection = await prisma.helpCollection.findUnique({
      where: { slug: collection },
      include: {
        i18n: { where: { locale }, take: 1 },
        categories: {
          where: { slug: category, isPublished: true },
          include: {
            i18n: { where: { locale }, take: 1 },
            articles: {
              where: { status: ContentStatus.PUBLISHED },
              orderBy: { publishedAt: 'desc' },
              include: {
                i18n: { where: { locale }, take: 1 },
              },
            },
          },
        },
      },
    })

    if (!foundCollection || !foundCollection.isPublished) {
      return NextResponse.json({ error: 'Collection not found', articles: [] }, { status: 404 })
    }

    const foundCategory = foundCollection.categories[0]
    if (!foundCategory) {
      return NextResponse.json({ error: 'Category not found', articles: [] }, { status: 404 })
    }

    const collectionI18n = foundCollection.i18n[0]
    const categoryI18n = foundCategory.i18n[0]

    const articles = foundCategory.articles
      .map((article) => {
        const i18n = article.i18n[0]
        if (!i18n) return null
        return {
          id: article.id,
          slug: article.slug,
          question: i18n.title,
          standfirst: i18n.standfirst ?? null,
          targetTags: normalizeTags((article as any).targetTags),
          updatedAt: article.updatedAt,
          publishedAt: article.publishedAt,
        }
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: collectionI18n?.title || foundCollection.slug,
      },
      category: {
        slug: foundCategory.slug,
        title: categoryI18n?.title || foundCategory.slug,
      },
      articles,
    })
  } catch (error) {
    console.error('[Help Articles API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', articles: [] }, { status: 500 })
  }
}
