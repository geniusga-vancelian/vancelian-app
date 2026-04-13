import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getLocaleOrDefault } from '@/config/locales'
import { cookies } from 'next/headers'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'

function markdownFromBlocks(
  blocks: Array<{ type: string; data: Record<string, unknown> }>
): string {
  const parts: string[] = []
  for (const block of blocks) {
    const data = block.data ?? {}
    if (block.type === 'HEADING') {
      const text = typeof data.text === 'string' ? data.text.trim() : ''
      if (text) parts.push(`## ${text}`)
      continue
    }
    if (block.type === 'PARAGRAPH' || block.type === 'QUOTE') {
      const text = typeof data.text === 'string' ? data.text.trim() : ''
      if (text) parts.push(text)
      continue
    }
    if (block.type === 'BULLET_LIST') {
      const items = Array.isArray(data.items) ? data.items : []
      const list = items
        .map((item) => (typeof item === 'string' ? item.trim() : ''))
        .filter((item) => item.length > 0)
        .map((item) => `- ${item}`)
      if (list.length) parts.push(list.join('\n'))
      continue
    }
    if (block.type === 'DOCUMENT') {
      const title = typeof data.title === 'string' ? data.title.trim() : 'Document'
      const url = typeof data.url === 'string' ? data.url.trim() : ''
      if (url) parts.push(`[${title}](${url})`)
    }
  }
  return parts.join('\n\n').trim()
}

async function resolveMediaUrl(mediaId: string | null | undefined): Promise<string | null> {
  if (!mediaId) return null
  const media = await prisma.media.findUnique({ where: { id: mediaId } })
  if (!media) return null
  try {
    return await getPresignedUrl(media.key, 3600)
  } catch {
    return media.url
  }
}

/**
 * GET /api/help/articles/by-slug?slug=xxx&locale=fr
 * Récupère un article Help par son slug (premier trouvé parmi les articles publiés).
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const slug = (searchParams.get('slug') ?? '').trim()
    const localeParam = searchParams.get('locale')
    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

    if (!slug) {
      return NextResponse.json({ error: 'Slug required' }, { status: 400 })
    }

    const foundArticle = await prisma.helpArticle.findFirst({
      where: {
        slug,
        status: ContentStatus.PUBLISHED,
        category: {
          isPublished: true,
          collection: { isPublished: true },
        },
      },
      include: {
        category: {
          include: {
            collection: {
              include: { i18n: { where: { locale }, take: 1 } },
            },
            i18n: { where: { locale }, take: 1 },
          },
        },
        i18n: { where: { locale }, take: 1 },
        blocks: {
          where: { locale },
          orderBy: { order: 'asc' },
        },
      },
    })

    if (!foundArticle) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    const foundCollection = foundArticle.category.collection
    const foundCategory = foundArticle.category
    const articleI18n = foundArticle.i18n[0]
    if (!articleI18n) {
      return NextResponse.json({ error: 'Article i18n not found' }, { status: 404 })
    }

    const blocks = await Promise.all(
      foundArticle.blocks.map(async (block) => {
        const data = (block.data as Record<string, unknown> | null) ?? {}
        const mediaId = typeof data.mediaId === 'string' ? data.mediaId : null
        const imageUrl = await resolveMediaUrl(mediaId)
        return {
          id: block.id,
          type: block.type,
          order: block.order,
          data,
          imageUrl,
        }
      })
    )

    const markdownContent =
      articleI18n.contentMarkdown?.trim() ||
      markdownFromBlocks(
        blocks.map((block) => ({
          type: String(block.type),
          data: block.data as Record<string, unknown>,
        }))
      )

    return NextResponse.json({
      article: {
        id: foundArticle.id,
        slug: foundArticle.slug,
        question: articleI18n.title,
        standfirst: articleI18n.standfirst ?? '',
        markdownContent,
        updatedAt: foundArticle.updatedAt,
        publishedAt: foundArticle.publishedAt,
        collection: {
          slug: foundCollection.slug,
          title: foundCollection.i18n[0]?.title || foundCollection.slug,
        },
        category: {
          slug: foundCategory.slug,
          title: foundCategory.i18n[0]?.title || foundCategory.slug,
        },
        blocks,
      },
    })
  } catch (error) {
    console.error('[Help Article By Slug API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
