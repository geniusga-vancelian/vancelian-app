import { NextRequest, NextResponse } from 'next/server'
import {
  getAcademyArticles,
  getAcademyCategory,
  getAcademyCollection,
} from '@/lib/academy/get-academy-data'

/**
 * Liste publique des Academy Articles d'une catégorie (web + mobile Flutter).
 * Tri par `publishedAt desc`. Inclut `targetTags`.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string }> },
) {
  try {
    const { collection, category } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const [foundCollection, foundCategory, articles] = await Promise.all([
      getAcademyCollection(collection, localeParam),
      getAcademyCategory(collection, category, localeParam),
      getAcademyArticles(collection, category, localeParam),
    ])

    if (!foundCollection) {
      return NextResponse.json({ error: 'Collection not found', articles: [] }, { status: 404 })
    }
    if (!foundCategory) {
      return NextResponse.json({ error: 'Category not found', articles: [] }, { status: 404 })
    }

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: foundCollection.title,
      },
      category: {
        slug: foundCategory.slug,
        title: foundCategory.title,
      },
      articles: articles.map((a) => ({
        id: a.id,
        slug: a.slug,
        question: a.title,
        standfirst: a.standfirst,
        targetTags: a.targetTags,
        updatedAt: a.updatedAt,
        publishedAt: a.publishedAt,
      })),
    })
  } catch (error) {
    console.error('[Academy Articles API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', articles: [] }, { status: 500 })
  }
}
