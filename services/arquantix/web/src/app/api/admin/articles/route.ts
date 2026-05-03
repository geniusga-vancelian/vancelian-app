import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidSlug } from '@/lib/utils/slugify'
import { ContentStatus } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { defaultLocale } from '@/config/locales'
import {
  ARTICLE_TYPE_KEYS,
  type ArticleTypeKey,
  normalizeArticleType,
} from '@/lib/admin/articleTypes'
import { normalizeCollectionTagsList } from '@/lib/articles/collectionTags'

const createArticleSchema = z
  .object({
    slug: z
      .string()
      .min(1)
      .max(255)
      .refine(isValidSlug, {
        message: 'Slug must be lowercase, alphanumeric with hyphens only',
      })
      .optional(),
    coverMediaId: z.preprocess(
      (v) => (v === '' ? undefined : v),
      z.string().min(1).optional()
    ), // Optional on creation, can be set in editor
    authorName: z.string().min(1),
    authorRole: z.string().optional().nullable(),
    allowComments: z.boolean().default(false),
    isMilestone: z.boolean().optional(),
    articleType: z.enum(ARTICLE_TYPE_KEYS).default('NEWS'),
    /** Tags de regroupement sous collection (Help, Academy, etc.). */
    collectionTags: z.array(z.string()).max(20).optional(),
    // -------- Champs HELP (Phase 3.3) --------
    helpCollectionId: z.string().min(1).optional(),
    helpCategoryId: z.string().min(1).optional().nullable(),
    helpSlug: z
      .string()
      .min(1)
      .max(255)
      .refine(isValidSlug, {
        message: 'helpSlug must be lowercase, alphanumeric with hyphens only',
      })
      .optional(),
    // -------- Champs ACADEMY (Phase 4 — symétrique HELP) --------
    academyCollectionId: z.string().min(1).optional(),
    academyCategoryId: z.string().min(1).optional().nullable(),
    academySlug: z
      .string()
      .min(1)
      .max(255)
      .refine(isValidSlug, {
        message: 'academySlug must be lowercase, alphanumeric with hyphens only',
      })
      .optional(),
    // i18n will be created separately
  })
  .refine(
    (data) =>
      data.articleType !== 'HELP' ||
      (!!data.helpCollectionId && !!data.helpSlug),
    {
      message:
        'For articleType=HELP, helpCollectionId + helpSlug are required.',
      path: ['articleType'],
    },
  )
  .refine(
    (data) =>
      data.articleType !== 'ACADEMY' ||
      (!!data.academyCollectionId && !!data.academySlug),
    {
      message:
        'For articleType=ACADEMY, academyCollectionId + academySlug are required.',
      path: ['articleType'],
    },
  )
  .refine(
    (data) =>
      data.articleType === 'HELP' || data.articleType === 'ACADEMY' || !!data.slug,
    {
      message: 'slug is required for non-HELP/ACADEMY article types.',
      path: ['slug'],
    },
  )

/**
 * Slug global technique `articles.slug` pour HELP : `help-{collection}-{helpSlug}`.
 */
async function buildUniqueHelpSlug(collectionId: string, helpSlug: string): Promise<string> {
  const collection = await prisma.helpCollection.findUnique({
    where: { id: collectionId },
    select: { slug: true },
  })
  if (!collection) throw new Error(`HelpCollection ${collectionId} introuvable`)

  const base = `help-${collection.slug}-${helpSlug}`
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  let candidate = base
  let i = 2
  while (await prisma.article.findUnique({ where: { slug: candidate }, select: { id: true } })) {
    candidate = `${base}-${i}`
    i++
    if (i > 1000) throw new Error(`Impossible de générer un slug unique pour HELP "${base}"`)
  }
  return candidate
}

/**
 * Slug global technique pour ACADEMY : `academy-{collection}-{academySlug}`.
 */
async function buildUniqueAcademySlug(collectionId: string, academySlug: string): Promise<string> {
  const collection = await prisma.academyCollection.findUnique({
    where: { id: collectionId },
    select: { slug: true },
  })
  if (!collection) throw new Error(`AcademyCollection ${collectionId} introuvable`)

  const base = `academy-${collection.slug}-${academySlug}`
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')

  let candidate = base
  let i = 2
  while (await prisma.article.findUnique({ where: { slug: candidate }, select: { id: true } })) {
    candidate = `${base}-${i}`
    i++
    if (i > 1000) throw new Error(`Impossible de générer un slug unique pour ACADEMY "${base}"`)
  }
  return candidate
}

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
    const rawArticleType = searchParams.get('articleType')
    const articleTypeFilter: ArticleTypeKey | null =
      rawArticleType && (ARTICLE_TYPE_KEYS as readonly string[]).includes(rawArticleType)
        ? (rawArticleType as ArticleTypeKey)
        : null

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
    let articleTypeById = new Map<string, ArticleTypeKey>()
    const companyNewsById = new Map<string, boolean>()
    if (articleIds.length > 0) {
      try {
        const typeRows = await prisma.$queryRawUnsafe<Array<{ id: string; article_type: string | null }>>(
          `SELECT "id", "article_type" FROM "articles" WHERE "id" = ANY($1::text[])`,
          articleIds
        )
        articleTypeById = new Map(
          typeRows.map((row) => [row.id, normalizeArticleType(row.article_type)])
        )
      } catch {
        articleTypeById = new Map(articleIds.map((id) => [id, 'NEWS' as ArticleTypeKey]))
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

    // Filtre par articleType (post-fetch car la colonne SQL `article_type`
    // n'est pas exposée par le client Prisma — voir `ensureArticleTypeColumn`).
    if (articleTypeFilter) {
      filteredArticles = filteredArticles.filter(
        (article) => (articleTypeById.get(article.id) ?? 'NEWS') === articleTypeFilter
      )
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
          articleType: articleTypeById.get(article.id) ?? 'NEWS',
          isCompanyNews: companyNewsById.get(article.id) ?? false,
          // Champs HELP (Phase 3.3) — exposés pour permettre au hub de
          // dédupliquer Article HELP unifiés vs HelpArticle legacy.
          helpCollectionId: (article as any).helpCollectionId ?? null,
          helpCategoryId: (article as any).helpCategoryId ?? null,
          helpSlug: (article as any).helpSlug ?? null,
          // Champs ACADEMY (Phase 4 — symétrique HELP).
          academyCollectionId: (article as any).academyCollectionId ?? null,
          academyCategoryId: (article as any).academyCategoryId ?? null,
          academySlug: (article as any).academySlug ?? null,
          allowAnchors:
            typeof (article as any).allowAnchors === 'boolean'
              ? (article as any).allowAnchors
              : true,
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

    let finalSlug = validated.slug
    const normalizedCreateTags = normalizeCollectionTagsList(validated.collectionTags ?? [])
    if (validated.articleType === 'HELP') {
      finalSlug = await buildUniqueHelpSlug(validated.helpCollectionId!, validated.helpSlug!)

      const collision = await prisma.article.findFirst({
        where: {
          articleType: 'HELP',
          helpCollectionId: validated.helpCollectionId!,
          helpSlug: validated.helpSlug!,
        },
        select: { id: true, slug: true },
      })
      if (collision) {
        return NextResponse.json(
          {
            error: `Un article HELP existe déjà dans cette collection avec le helpSlug "${validated.helpSlug}" (id=${collision.id}).`,
          },
          { status: 400 },
        )
      }
    } else if (validated.articleType === 'ACADEMY') {
      finalSlug = await buildUniqueAcademySlug(
        validated.academyCollectionId!,
        validated.academySlug!,
      )

      const collision = await prisma.article.findFirst({
        where: {
          articleType: 'ACADEMY',
          academyCollectionId: validated.academyCollectionId!,
          academySlug: validated.academySlug!,
        },
        select: { id: true, slug: true },
      })
      if (collision) {
        return NextResponse.json(
          {
            error: `Un article ACADEMY existe déjà dans cette collection avec le academySlug "${validated.academySlug}" (id=${collision.id}).`,
          },
          { status: 400 },
        )
      }
    } else {
      const existing = await prisma.article.findUnique({
        where: { slug: validated.slug! },
      })
      if (existing) {
        return NextResponse.json(
          { error: 'Article with this slug already exists' },
          { status: 400 }
        )
      }
    }

    const article = await prisma.article.create({
      data: {
        slug: finalSlug!,
        coverMediaId: validated.coverMediaId || null,
        authorName: validated.authorName,
        authorRole: validated.authorRole || null,
        allowComments: validated.allowComments,
        isMilestone: validated.isMilestone ?? false,
        status: ContentStatus.DRAFT,
        helpCollectionId:
          validated.articleType === 'HELP' ? validated.helpCollectionId! : null,
        helpCategoryId:
          validated.articleType === 'HELP' ? validated.helpCategoryId ?? null : null,
        helpSlug: validated.articleType === 'HELP' ? validated.helpSlug! : null,
        academyCollectionId:
          validated.articleType === 'ACADEMY' ? validated.academyCollectionId! : null,
        academyCategoryId:
          validated.articleType === 'ACADEMY' ? validated.academyCategoryId ?? null : null,
        academySlug: validated.articleType === 'ACADEMY' ? validated.academySlug! : null,
        collectionTags: normalizedCreateTags,
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

