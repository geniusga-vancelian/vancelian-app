import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { ContentStatus } from '@prisma/client'

const helpArticleTagSchema = z.object({
  type: z.enum(['THEMATIC_CATEGORY', 'INVESTMENT_TYPE', 'EXCLUSIVE_OFFER']),
  id: z.string().min(1),
  slug: z.string().min(1),
  label: z.string().min(1).max(200),
})

const updateArticleSchema = z.object({
  slug: z.string().min(1).optional(),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  publishedAt: z.string().datetime().optional().nullable(),
  authorName: z.string().optional().nullable(),
  coverMediaId: z.string().optional().nullable(),
  allowAnchors: z.boolean().optional(),
  targetTags: z.array(helpArticleTagSchema).max(100).optional(),
})

type HelpArticleTag = z.infer<typeof helpArticleTagSchema>

function normalizeTags(raw: unknown): HelpArticleTag[] {
  let source: unknown = raw
  if (typeof source === 'string') {
    try {
      source = JSON.parse(source)
    } catch {
      return []
    }
  }
  if (!Array.isArray(source)) return []
  const unique = new Map<string, HelpArticleTag>()
  for (const item of source) {
    const parsed = helpArticleTagSchema.safeParse(item)
    if (!parsed.success) continue
    const tag = parsed.data
    unique.set(`${tag.type}:${tag.id}`, tag)
  }
  return Array.from(unique.values())
}

// GET /api/admin/help/articles/[id]?locale=...
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const locale = searchParams.get('locale') || 'fr'

    const article = await prisma.helpArticle.findUnique({
      where: { id: params.id },
      include: {
        i18n: {
          where: { locale },
          take: 1,
        },
        blocks: {
          where: { locale },
          orderBy: { order: 'asc' },
        },
        category: {
          include: {
            collection: true,
          },
        },
        coverMedia: true,
      },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Backward-compatible enrichment: if Prisma client is older than schema,
    // include markdown content directly from SQL column.
    const markdownRows = await prisma.$queryRaw<Array<{ locale: string; content_markdown: string | null }>>`
      SELECT "locale", "content_markdown"
      FROM "help_article_i18n"
      WHERE "article_id" = ${params.id}
    `
    const markdownByLocale = new Map(
      markdownRows.map((row) => [row.locale, row.content_markdown])
    )
    ;(article as any).i18n = (article.i18n || []).map((row: any) => ({
      ...row,
      contentMarkdown:
        row.contentMarkdown ??
        markdownByLocale.get(row.locale) ??
        null,
    }))

    const tagRows = await prisma.$queryRaw<Array<{ target_tags: unknown }>>`
      SELECT "target_tags"
      FROM "help_articles"
      WHERE "id" = ${params.id}
      LIMIT 1
    `
    ;(article as any).targetTags = normalizeTags(tagRows[0]?.target_tags)

    return NextResponse.json({ article })
  } catch (error) {
    console.error('Error fetching article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/help/articles/[id]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = updateArticleSchema.parse(body)

    const updateData: any = {}
    if (validated.slug !== undefined) updateData.slug = validated.slug
    if (validated.status !== undefined) updateData.status = validated.status
    if (validated.publishedAt !== undefined) {
      updateData.publishedAt = validated.publishedAt ? new Date(validated.publishedAt) : null
    }
    if (validated.authorName !== undefined) updateData.authorName = validated.authorName
    if (validated.coverMediaId !== undefined) updateData.coverMediaId = validated.coverMediaId
    if (validated.allowAnchors !== undefined) updateData.allowAnchors = validated.allowAnchors

    const article = await prisma.helpArticle.update({
      where: { id: params.id },
      data: updateData,
    })

    if (validated.targetTags !== undefined) {
      const normalizedTags = normalizeTags(validated.targetTags)
      await prisma.$executeRaw`
        UPDATE "help_articles"
        SET "target_tags" = ${JSON.stringify(normalizedTags)}::jsonb
        WHERE "id" = ${params.id}
      `
      ;(article as any).targetTags = normalizedTags
    }

    return NextResponse.json({ article })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/help/articles/[id]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    await prisma.helpArticle.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









