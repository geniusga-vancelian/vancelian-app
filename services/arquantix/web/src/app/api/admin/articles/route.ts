import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidSlug } from '@/lib/utils/slugify'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { defaultLocale } from '@/config/locales'

const createArticleSchema = z.object({
  slug: z.string().min(1).max(255).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }),
  coverMediaId: z.preprocess(
    (v) => (v === '' ? undefined : v),
    z.string().min(1).optional()
  ), // Optional on creation, can be set in editor
  authorName: z.string().min(1),
  authorRole: z.string().optional().nullable(),
  allowComments: z.boolean().default(false),
  isMilestone: z.boolean().optional(),
  articleType: z.enum(['NEWS', 'ANALYSIS']).default('NEWS'),
  // i18n will be created separately
})

async function ensureArticleTypeColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "articles"
    ADD COLUMN IF NOT EXISTS "article_type" TEXT NOT NULL DEFAULT 'NEWS';
  `)
}

// GET /api/admin/articles
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const locale = searchParams.get('locale') || defaultLocale
    const search = searchParams.get('search')

    const where: any = {}
    if (status && (status === 'DRAFT' || status === 'PUBLISHED')) {
      where.status = status
    }

    const articles = await prisma.article.findMany({
      where,
      include: {
        coverMedia: true,
        i18n: {
          where: locale ? { locale } : undefined,
          orderBy: { locale: 'asc' },
        },
      },
      orderBy: { createdAt: 'desc' },
    })

    // Filter by search if provided
    let filteredArticles = articles
    if (search) {
      filteredArticles = articles.filter((article) => {
        const i18n = article.i18n.find((i) => i.locale === locale)
        return i18n?.title.toLowerCase().includes(search.toLowerCase())
      })
    }

    // Compatibility fallback: if runtime Prisma client does not expose isMilestone,
    // read the value directly from SQL and merge it in the response.
    const articleIds = filteredArticles.map((article) => article.id)
    const milestoneRows = articleIds.length > 0
      ? await prisma.$queryRawUnsafe<Array<{ id: string; is_milestone: boolean }>>(
          `SELECT "id", "is_milestone" FROM "articles" WHERE "id" = ANY($1::text[])`,
          articleIds
        )
      : []
    const milestoneById = new Map(milestoneRows.map((row) => [row.id, row.is_milestone]))
    let articleTypeById = new Map<string, string>()
    const companyNewsById = new Map<string, boolean>()
    if (articleIds.length > 0) {
      try {
        const typeRows = await prisma.$queryRawUnsafe<Array<{ id: string; article_type: string | null }>>(
          `SELECT "id", "article_type" FROM "articles" WHERE "id" = ANY($1::text[])`,
          articleIds
        )
        articleTypeById = new Map(typeRows.map((row) => [row.id, row.article_type || 'NEWS']))
      } catch {
        articleTypeById = new Map(articleIds.map((id) => [id, 'NEWS']))
      }
      try {
        await prisma.$executeRawUnsafe(`
          ALTER TABLE "articles" ADD COLUMN IF NOT EXISTS "is_company_news" BOOLEAN NOT NULL DEFAULT false;
        `)
        const cnRows = await prisma.$queryRawUnsafe<Array<{ id: string; is_company_news: boolean }>>(
          `SELECT "id", "is_company_news" FROM "articles" WHERE "id" = ANY($1::text[])`,
          articleIds
        )
        for (const row of cnRows) {
          companyNewsById.set(row.id, row.is_company_news === true)
        }
      } catch {
        for (const id of articleIds) {
          companyNewsById.set(id, false)
        }
      }
    }

    // Generate presigned URLs for cover media
    const articlesWithUrls = await Promise.all(
      filteredArticles.map(async (article) => {
        let coverUrl: string | null = null
        if (article.coverMedia) {
          coverUrl = article.coverMedia.url
          if (article.coverMedia.key) {
            try {
              coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
            } catch {
              // Fallback to original URL
              coverUrl = article.coverMedia.url
            }
          }
        }

        const defaultI18n = article.i18n.find((i) => i.locale === locale) || article.i18n[0]

        return {
          id: article.id,
          slug: article.slug,
          status: article.status,
          publishedAt: article.publishedAt,
          createdAt: article.createdAt,
          updatedAt: article.updatedAt,
          authorName: article.authorName,
          authorRole: article.authorRole,
          coverUrl: coverUrl || '',
          title: defaultI18n?.title || 'Untitled',
          locale: defaultI18n?.locale || locale,
          isFeatured: article.isFeatured,
          isHighlighted: article.isHighlighted,
          isMilestone:
            typeof (article as any).isMilestone === 'boolean'
              ? (article as any).isMilestone
              : milestoneById.get(article.id) ?? false,
          articleType: articleTypeById.get(article.id) === 'ANALYSIS' ? 'ANALYSIS' : 'NEWS',
          isCompanyNews: companyNewsById.get(article.id) ?? false,
        }
      })
    )

    return NextResponse.json({ articles: articlesWithUrls })
  } catch (error) {
    console.error('Error fetching articles:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// POST /api/admin/articles
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validated = createArticleSchema.parse(body)

    // Check if slug already exists
    const existing = await prisma.article.findUnique({
      where: { slug: validated.slug },
    })

    if (existing) {
      return NextResponse.json(
        { error: 'Article with this slug already exists' },
        { status: 400 }
      )
    }

    // Create article (coverMediaId is now optional, can be set in editor)
    const article = await prisma.article.create({
      data: {
        slug: validated.slug,
        coverMediaId: validated.coverMediaId || null,
        authorName: validated.authorName,
        authorRole: validated.authorRole || null,
        allowComments: validated.allowComments,
        isMilestone: validated.isMilestone ?? false,
        status: ContentStatus.DRAFT,
      },
    })

    try {
      await ensureArticleTypeColumn()
      await prisma.$executeRawUnsafe(
        `UPDATE "articles" SET "article_type" = $1 WHERE "id" = $2`,
        validated.articleType,
        article.id
      )
    } catch (error) {
      console.error('Failed to persist article_type:', error)
    }

    return NextResponse.json({ article }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

