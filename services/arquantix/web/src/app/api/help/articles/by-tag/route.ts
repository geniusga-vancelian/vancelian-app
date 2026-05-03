import { NextRequest, NextResponse } from 'next/server'
import {
  getHelpArticlesByTargetTag,
  type HelpTargetTagDTO,
} from '@/lib/help/get-help-data'

/**
 * GET /api/help/articles/by-tag?type=EXCLUSIVE_OFFER&id=<projectId>&locale=fr
 *
 * Phase 3.3 : passe par `getHelpArticlesByTargetTag()` qui agrège les
 * articles ciblés (`target_tags @>`) côté `Article(HELP)` unifié ET
 * `HelpArticle` legacy, déduplique par `helpSlug`, et résout les titres
 * collection/category dans la locale demandée.
 */
const VALID_TAG_TYPES = new Set<HelpTargetTagDTO['type']>([
  'THEMATIC_CATEGORY',
  'INVESTMENT_TYPE',
  'EXCLUSIVE_OFFER',
])

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const typeParam = (searchParams.get('type') || '').trim().toUpperCase() as HelpTargetTagDTO['type']
    const id = (searchParams.get('id') || '').trim()
    const localeParam = searchParams.get('locale') || undefined

    if (!typeParam || !id) {
      return NextResponse.json({ error: 'Missing tag type or id', articles: [] }, { status: 400 })
    }
    if (!VALID_TAG_TYPES.has(typeParam)) {
      return NextResponse.json({ error: 'Invalid tag type', articles: [] }, { status: 400 })
    }

    const articles = await getHelpArticlesByTargetTag(typeParam, id, localeParam)

    return NextResponse.json({
      tag: { type: typeParam, id },
      articles: articles.map((a) => ({
        id: a.id,
        slug: a.slug,
        question: a.title,
        standfirst: a.standfirst,
        collection: a.collection,
        category: a.category,
        updatedAt: a.updatedAt,
      })),
    })
  } catch (error) {
    console.error('[Help by tag API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', articles: [] },
      { status: 500 }
    )
  }
}
