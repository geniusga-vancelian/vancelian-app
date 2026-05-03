import { NextRequest, NextResponse } from 'next/server'
import { resolveArticleCoverUrlForPublic } from '@/lib/blog/resolveArticleCoverUrlForPublic'
import { getHelpArticle } from '@/lib/help/get-help-data'
import { markdownFromHelpBlocks } from '@/lib/help/markdown-from-blocks'

/**
 * Détail public d'un Help Article (web + mobile Flutter).
 *
 * Phase 3.3 : passe par `getHelpArticle()` qui tente la lecture
 * `Article(HELP)` unifié puis fallback `HelpArticle` legacy. Le markdown
 * est issu de `i18n.contentMarkdown` quand disponible (legacy uniquement),
 * sinon dérivé des blocs via `markdownFromHelpBlocks` (cas Article unifié).
 *
 * Les blocs renvoyés par `resolveArticleBlocksForPublic` portent déjà
 * `imageUrl` (pré-signé) pour `IMAGE`, et la `data` enrichie pour les
 * carrousels / steps / vidéos.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string; article: string }> }
) {
  try {
    const { collection, category, article } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const detail = await getHelpArticle(collection, article, localeParam)
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
    console.error('[Help Article Detail API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
