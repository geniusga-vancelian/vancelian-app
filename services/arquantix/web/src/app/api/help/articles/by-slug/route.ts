import { NextRequest, NextResponse } from 'next/server'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import { getHelpArticleByGlobalSlug } from '@/lib/help/get-help-data'
import { markdownFromHelpBlocks } from '@/lib/help/markdown-from-blocks'

/**
 * GET /api/help/articles/by-slug?slug=xxx&locale=fr
 *
 * Retourne le premier article Help (publié) qui matche le slug. Phase 3.3 :
 * cherche d'abord dans `Article(articleType='HELP')` (par `helpSlug` puis
 * `slug`), puis fallback sur `HelpArticle` legacy. La forme du retour est
 * identique au détail `/api/help/.../articles/[article]`.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const slug = (searchParams.get('slug') ?? '').trim()
    const localeParam = searchParams.get('locale') || undefined

    if (!slug) {
      return NextResponse.json({ error: 'Slug required' }, { status: 400 })
    }

    const detail = await getHelpArticleByGlobalSlug(slug, localeParam)
    if (!detail) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    const markdownContent =
      (detail.contentMarkdown && detail.contentMarkdown.trim()) ||
      markdownFromHelpBlocks(
        detail.blocks.map((b) => ({
          type: b.type,
          data: b.data,
        })),
      )

    const coverUrl = await resolveArticleCoverUrlForPublic(detail.coverMedia)

    return NextResponse.json({
      article: {
        id: detail.id,
        slug: detail.slug,
        question: detail.title,
        standfirst: detail.standfirst ?? '',
        coverUrl,
        markdownContent,
        updatedAt: detail.updatedAt,
        publishedAt: detail.publishedAt,
        collection: {
          slug: detail.collection.slug,
          title: detail.collection.title,
          iconKey: detail.collection.iconKey ?? null,
          colorHex: detail.collection.colorHex ?? null,
        },
        category: detail.category,
        blocks: detail.blocks.map((b) => ({
          id: b.id,
          type: b.type,
          order: b.order,
          data: b.data,
          imageUrl: b.imageUrl ?? null,
        })),
      },
    })
  } catch (error) {
    console.error('[Help Article By Slug API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
