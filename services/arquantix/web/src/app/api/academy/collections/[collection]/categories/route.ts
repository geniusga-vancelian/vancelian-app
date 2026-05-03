import { NextRequest, NextResponse } from 'next/server'
import { getAcademyCategories, getAcademyCollection } from '@/lib/academy/get-academy-data'

/**
 * Liste publique des Academy Categories d'une collection (web + mobile Flutter).
 * Symétrique à `/api/help/collections/[collection]/categories`.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string }> },
) {
  try {
    const { collection } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const [foundCollection, categories] = await Promise.all([
      getAcademyCollection(collection, localeParam),
      getAcademyCategories(collection, localeParam),
    ])

    if (!foundCollection) {
      return NextResponse.json({ error: 'Collection not found', categories: [] }, { status: 404 })
    }

    return NextResponse.json({
      collection: {
        slug: foundCollection.slug,
        title: foundCollection.title,
      },
      categories: categories.map((c) => ({
        id: c.id,
        slug: c.slug,
        order: c.order,
        title: c.title,
        description: c.description,
        articleCount: c.articleCount,
      })),
    })
  } catch (error) {
    console.error('[Academy Categories API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', categories: [] },
      { status: 500 },
    )
  }
}
