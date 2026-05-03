import { NextRequest, NextResponse } from 'next/server'
import { tagSlugToDisplayTitle } from '@/lib/articles/collectionTags'
import {
  getHelpArticles,
  getHelpCategory,
  getHelpCollection,
} from '@/lib/help/get-help-data'

/**
 * Liste publique des Help Articles d'une catégorie (web + mobile Flutter).
 *
 * Phase 3.3 : passe par `getHelpArticles()` qui agrège `Article(HELP)`
 * unifiés + `HelpArticle` legacy (dédup `helpSlug`, statut PUBLISHED).
 * Tri par `publishedAt desc`. Inclut `targetTags`.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string }> }
) {
  try {
    const { collection, category } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const [foundCollection, foundCategory, articles] = await Promise.all([
      getHelpCollection(collection, localeParam),
      getHelpCategory(collection, category, localeParam),
      getHelpArticles(collection, category, localeParam),
    ])

    if (!foundCollection) {
      return NextResponse.json({ error: 'Collection not found', articles: [] }, { status: 404 })
    }

    // Segment = slug catégorie legacy OU tag `collection_tags` : pas de ligne HelpCategory requise.
    if (articles.length === 0) {
      return NextResponse.json({ error: 'Category not found', articles: [] }, { status: 404 })
    }

    const categoryPayload = foundCategory
      ? { slug: foundCategory.slug, title: foundCategory.title }
      : { slug: category, title: tagSlugToDisplayTitle(category) }

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: foundCollection.title,
      },
      category: categoryPayload,
      articles: articles.map((a) => ({
        id: a.id,
        slug: a.slug,
        question: a.title,
        standfirst: a.standfirst,
        targetTags: a.targetTags,
        collectionTags: a.collectionTags,
        updatedAt: a.updatedAt,
        publishedAt: a.publishedAt,
      })),
    })
  } catch (error) {
    console.error('[Help Articles API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', articles: [] }, { status: 500 })
  }
}
