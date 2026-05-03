import { NextRequest, NextResponse } from 'next/server'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import { getAcademyArticle } from '@/lib/academy/get-academy-data'
import { markdownFromHelpBlocks } from '@/lib/help/markdown-from-blocks'

/**
 * Détail public d'un Academy Article (web + mobile Flutter).
 *
 * Le markdown est dérivé des blocs via `markdownFromHelpBlocks` (le module
 * est générique, partagé avec Help). Les blocs renvoyés par
 * `resolveArticleBlocksForPublic` portent déjà `imageUrl` (pré-signé) pour
 * `IMAGE`, et la `data` enrichie pour les carrousels / steps / vidéos.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string; article: string }> },
) {
  try {
    const { collection, category, article } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const detail = await getAcademyArticle(collection, article, localeParam)
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
        targetTags: detail.targetTags,
      },
    })
  } catch (error) {
    console.error('[Academy Article Detail API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
