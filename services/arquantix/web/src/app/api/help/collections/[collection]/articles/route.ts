import { NextRequest, NextResponse } from 'next/server'
import { getHelpArticlesAllInCollection, getHelpCollection } from '@/lib/help/get-help-data'

/**
 * Liste plate : tous les articles Help publiés d’une collection (mobile « flat »).
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string }> },
) {
  try {
    const { collection } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const [foundCollection, articles] = await Promise.all([
      getHelpCollection(collection, localeParam),
      getHelpArticlesAllInCollection(collection, localeParam),
    ])

    if (!foundCollection) {
      return NextResponse.json({ error: 'Collection not found', articles: [] }, { status: 404 })
    }

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: foundCollection.title,
      },
      category: {
        slug: '__all__',
        title: foundCollection.title,
      },
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
    console.error('[Help Collection Articles API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', articles: [] }, { status: 500 })
  }
}
