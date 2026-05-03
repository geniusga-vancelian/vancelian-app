import { NextRequest, NextResponse } from 'next/server'
import { getHelpCollections } from '@/lib/help/get-help-data'

/**
 * Liste publique des Help Collections (web + mobile Flutter).
 *
 * Phase 3.3 : passe par `getHelpCollections()` qui agrège les comptes
 * `Article(HELP)` unifiés ET `HelpArticle` legacy (dédup `helpSlug`).
 * Avant ce refactor, la route ne lisait QUE le legacy, donc l'app mobile ne
 * voyait pas les nouveaux articles créés via le builder unifié.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const collections = await getHelpCollections(localeParam)

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
        coverImageUrl: c.coverImageUrl,
      })),
    })
  } catch (error) {
    console.error('[Help Collections API] Error:', error)
    return NextResponse.json({ error: 'Internal server error', collections: [] }, { status: 500 })
  }
}
