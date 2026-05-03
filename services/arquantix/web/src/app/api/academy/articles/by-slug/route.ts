import { NextRequest, NextResponse } from 'next/server'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import { getAcademyArticleByGlobalSlug } from '@/lib/academy/get-academy-data'
import { markdownFromHelpBlocks } from '@/lib/help/markdown-from-blocks'

/**
 * GET /api/academy/articles/by-slug?slug=xxx&locale=fr
 *
 * Cherche dans `Article(articleType='ACADEMY')` par `academySlug` puis `slug`.
 * Forme du retour identique au détail
 * `/api/academy/collections/.../articles/[article]`.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const slug = (searchParams.get('slug') ?? '').trim()
    const localeParam = searchParams.get('locale') || undefined

    if (!slug) {
      return NextResponse.json({ error: 'Slug required' }, { status: 400 })
    }

    const detail = await getAcademyArticleByGlobalSlug(slug, localeParam)
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
    console.error('[Academy Article By Slug API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
