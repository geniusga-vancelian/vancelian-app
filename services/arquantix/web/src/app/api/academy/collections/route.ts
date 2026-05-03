import { NextRequest, NextResponse } from 'next/server'
import { getAcademyCollections } from '@/lib/academy/get-academy-data'

/**
 * Liste publique des Academy Collections (web + mobile Flutter).
 *
 * Symétrique à `/api/help/collections` mais exclusivement basé sur le schéma
 * unifié `Article(articleType='ACADEMY')` — pas de table legacy à agréger.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const collections = await getAcademyCollections(localeParam)

    return NextResponse.json({
      collections: collections.map((c) => ({
        id: c.id,
        slug: c.slug,
        iconKey: c.iconKey,
        colorHex: c.colorHex,
        order: c.order,
        title: c.title,
        subtitle: c.subtitle,
        description: c.description,
        articleCount: c.articleCount,
      })),
    })
  } catch (error) {
    console.error('[Academy Collections API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', collections: [] }, { status: 500 })
  }
}
