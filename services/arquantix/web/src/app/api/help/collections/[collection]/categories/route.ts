import { NextRequest, NextResponse } from 'next/server'
import { getHelpCategories, getHelpCollection } from '@/lib/help/get-help-data'

/**
 * Liste publique des Help Categories d'une collection (web + mobile Flutter).
 *
 * Phase 3.3 : passe par `getHelpCollection()` + `getHelpCategories()` qui
 * agrègent les comptes `Article(HELP)` unifiés ET `HelpArticle` legacy
 * (dédup `helpSlug`). Avant ce refactor, la route ne lisait QUE le legacy.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string }> }
) {
  try {
    const { collection } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const [foundCollection, categories] = await Promise.all([
      getHelpCollection(collection, localeParam),
      getHelpCategories(collection, localeParam),
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
    console.error('[Help Categories API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', categories: [] },
      { status: 500 }
    )
  }
}
