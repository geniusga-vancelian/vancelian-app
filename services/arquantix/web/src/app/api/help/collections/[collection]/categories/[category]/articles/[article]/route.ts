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

function normalizeTags(raw: unknown) {
  let source: unknown = raw
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return []
    }
  }
  if (!Array.isArray(source)) return []
  const validTypes = new Set(['THEMATIC_CATEGORY', 'INVESTMENT_TYPE', 'EXCLUSIVE_OFFER'])
  return source
    .filter((item) => {
      if (!item || typeof item !== 'object') return false
      const row = item as Record<string, unknown>
      return (
        typeof row.type === 'string' &&
        validTypes.has(row.type) &&
        typeof row.id === 'string' &&
        typeof row.slug === 'string' &&
        typeof row.label === 'string'
      )
    })
    .map((item) => {
      const row = item as Record<string, string>
      return {
        type: row.type,
        id: row.id,
        slug: row.slug,
        label: row.label,
      }
    })
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

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string; category: string; article: string }> }
) {
  try {
    const { collection, category, article } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    const cookieStore = await cookies()
    const locale = localeParam || getLocaleOrDefault(cookieStore.get('arquantix-locale')?.value)

    const foundCollection = await prisma.helpCollection.findUnique({
      where: { slug: collection },
      include: {
        i18n: { where: { locale }, take: 1 },
        categories: {
          where: { slug: category, isPublished: true },
          include: {
            i18n: { where: { locale }, take: 1 },
            articles: {
              where: { slug: article, status: ContentStatus.PUBLISHED },
              include: {
                i18n: { where: { locale }, take: 1 },
                blocks: {
                  where: { locale },
                  orderBy: { order: 'asc' },
                },
              },
            },
          },
        },
      },
    })

    if (!foundCollection || !foundCollection.isPublished) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    const foundCategory = foundCollection.categories[0]
    const foundArticle = foundCategory?.articles[0]
    const articleI18n = foundArticle?.i18n[0]
    if (!foundCategory || !foundArticle || !articleI18n) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
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
        targetTags: normalizeTags((foundArticle as any).targetTags),
      },
    })
  } catch (error) {
    console.error('[Help Article Detail API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
