import { NextRequest, NextResponse } from 'next/server'
import { cookies } from 'next/headers'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { isValidSlug } from '@/lib/utils/slugify'
import { ContentStatus, Prisma } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { awaitRouteParams } from '@/lib/api/routeParams'
import { ARTICLE_TYPE_KEYS, normalizeArticleType } from '@/lib/admin/articleTypes'
import { normalizeCollectionTagsList } from '@/lib/articles/collectionTags'

const updateArticleSchema = z.object({
  slug: z.string().min(1).max(255).refine(isValidSlug, {
    message: 'Slug must be lowercase, alphanumeric with hyphens only',
  }).optional(),
  coverMediaId: z.preprocess(
    (v) => (v === '' ? null : v),
    z.union([z.string().min(1), z.null()]).optional()
  ),
  galleryMediaIds: z.array(z.string()).max(20).optional().nullable(),
  videoUrl: z.preprocess(
    (v) => (v === '' ? null : v),
    z.union([z.string().url(), z.null()]).optional()
  ),
  categorySlugs: z.array(z.string()).max(10).optional().nullable(),
  documents: z.array(z.object({
    mediaId: z.string(),
    title: z.string(),
  })).optional().nullable(),
  isFeatured: z.boolean().optional(),
  isHighlighted: z.boolean().optional(),
  isMilestone: z.boolean().optional(),
  coverTitle: z.string().max(240).optional().nullable(),
  coverCredit: z.string().max(120).optional().nullable(),
  coverSource: z.string().max(120).optional().nullable(),
  authorName: z.string().min(1).optional(),
  authorRole: z.string().optional().nullable(),
  allowComments: z.boolean().optional(),
  articleType: z.enum(ARTICLE_TYPE_KEYS).optional(),
  /** Uniquement pour les NEWS ; forcé à false pour les autres types côté serveur. */
  isCompanyNews: z.boolean().optional(),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  publishedAt: z.string().datetime().optional().nullable(),
  // -------- Champs HELP (Phase 3.3) --------
  helpCollectionId: z.string().min(1).optional().nullable(),
  helpCategoryId: z.string().min(1).optional().nullable(),
  helpSlug: z
    .string()
    .min(1)
    .max(255)
    .refine(isValidSlug, {
      message: 'helpSlug must be lowercase, alphanumeric with hyphens only',
    })
    .optional()
    .nullable(),
  allowAnchors: z.boolean().optional(),
  targetTags: z.array(z.string().min(1).max(64)).max(50).optional().nullable(),
  // -------- Champs ACADEMY (Phase 4 — symétrique HELP) --------
  academyCollectionId: z.string().min(1).optional().nullable(),
  academyCategoryId: z.string().min(1).optional().nullable(),
  academySlug: z
    .string()
    .min(1)
    .max(255)
    .refine(isValidSlug, {
      message: 'academySlug must be lowercase, alphanumeric with hyphens only',
    })
    .optional()
    .nullable(),
  /** Tags de regroupement sous collection (Help, Academy, NEWS, …). */
  collectionTags: z.array(z.string()).max(20).optional().nullable(),
})

async function ensureArticleMilestoneColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "articles"
    ADD COLUMN IF NOT EXISTS "is_milestone" BOOLEAN NOT NULL DEFAULT false;
  `)

  await prisma.$executeRawUnsafe(`
    CREATE INDEX IF NOT EXISTS "articles_is_milestone_idx"
    ON "articles"("is_milestone");
  `)
}

async function ensureArticleTypeColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "articles"
    ADD COLUMN IF NOT EXISTS "article_type" TEXT NOT NULL DEFAULT 'NEWS';
  `)
}

async function ensureArticleCompanyNewsColumn() {
  await prisma.$executeRawUnsafe(`
    ALTER TABLE "articles"
    ADD COLUMN IF NOT EXISTS "is_company_news" BOOLEAN NOT NULL DEFAULT false;
  `)
  await prisma.$executeRawUnsafe(`
    CREATE INDEX IF NOT EXISTS "articles_is_company_news_idx"
    ON "articles"("is_company_news");
  `)
}

function isUnknownMilestoneArgumentError(error: unknown): boolean {
  return (
    error instanceof Error &&
    error.message.includes('Unknown argument `isMilestone`')
  )
}

/** Client Prisma obsolète (ex. bundle Next `.next` pas régénéré après `prisma generate`). */
function isUnknownCompanyNewsArgumentError(error: unknown): boolean {
  return (
    error instanceof Error &&
    error.message.includes('Unknown argument `isCompanyNews`')
  )
}

// GET /api/admin/articles/[id]
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get locale from query param or cookie for block i18n
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    
    let locale: string
    if (localeParam) {
      const { isValidLocale, defaultLocale: defLocale } = await import('@/config/locales')
      locale = isValidLocale(localeParam) ? localeParam : defLocale
    } else {
      const cookieStore = await cookies()
      const { getLocaleFromCookies } = await import('@/lib/i18n/locale-server')
      const { defaultLocale: defLocale } = await import('@/config/locales')
      locale = await getLocaleFromCookies(cookieStore) || defLocale
    }

    const article = await prisma.article.findUnique({
      where: { id },
      include: {
        coverMedia: true,
        projects: {
          include: {
            project: {
              include: {
                i18n: {
                  where: { locale },
                  take: 1,
                },
              },
            },
          },
        },
        i18n: {
          orderBy: { locale: 'asc' },
        },
        blocks: {
          orderBy: { order: 'asc' },
          include: {
            i18n: {
              where: { locale },
              take: 1,
            },
          },
        },
      },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Generate presigned URL for cover media
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

    // Use localized block data if available, otherwise fallback to canonical block data
    const blocksWithLocalizedData = article.blocks.map((block) => {
      const blockData = block.i18n[0]?.data || block.data
      return {
        ...block,
        data: blockData,
        i18n: undefined, // Remove i18n from response to avoid confusion
      }
    })

    let resolvedIsMilestone = (article as any).isMilestone
    if (typeof resolvedIsMilestone !== 'boolean') {
      const milestoneRows = await prisma.$queryRawUnsafe<Array<{ is_milestone: boolean }>>(
        `SELECT "is_milestone" FROM "articles" WHERE "id" = $1 LIMIT 1`,
        id
      )
      resolvedIsMilestone = milestoneRows[0]?.is_milestone ?? false
    }

    let resolvedArticleType: string = 'NEWS'
    try {
      await ensureArticleTypeColumn()
      const typeRows = await prisma.$queryRawUnsafe<Array<{ article_type: string | null }>>(
        `SELECT "article_type" FROM "articles" WHERE "id" = $1 LIMIT 1`,
        id
      )
      resolvedArticleType = normalizeArticleType(typeRows[0]?.article_type)
    } catch {
      resolvedArticleType = 'NEWS'
    }

    let resolvedIsCompanyNews = false
    try {
      await ensureArticleCompanyNewsColumn()
      const cnRows = await prisma.$queryRawUnsafe<Array<{ is_company_news: boolean }>>(
        `SELECT "is_company_news" FROM "articles" WHERE "id" = $1 LIMIT 1`,
        id
      )
      resolvedIsCompanyNews = cnRows[0]?.is_company_news === true
    } catch {
      resolvedIsCompanyNews = false
    }

    return NextResponse.json({
      article: {
        ...article,
        isMilestone: resolvedIsMilestone,
        articleType: resolvedArticleType,
        isCompanyNews: resolvedIsCompanyNews,
        blocks: blocksWithLocalizedData,
        coverUrl: coverUrl || '',
      },
    })
  } catch (error) {
    console.error('Error fetching article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/articles/[id]
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    console.log('[PUT /api/admin/articles/[id]] Request body:', JSON.stringify(body, null, 2))
    
    let validated
    try {
      validated = updateArticleSchema.parse(body)
      console.log('[PUT /api/admin/articles/[id]] Validation successful')
    } catch (validationError) {
      console.error('[PUT /api/admin/articles/[id]] Validation error:', validationError)
      throw validationError
    }

    const article = await prisma.article.findUnique({
      where: { id },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    // Check slug uniqueness if changed
    if (validated.slug && validated.slug !== article.slug) {
      const existing = await prisma.article.findUnique({
        where: { slug: validated.slug },
      })
      if (existing) {
        return NextResponse.json(
          { error: 'Article with this slug already exists' },
          { status: 400 }
        )
      }
    }

    // Normalize optional fields
    const normalizedCoverTitle = validated.coverTitle === '' || validated.coverTitle === undefined ? null : validated.coverTitle
    const normalizedCoverCredit = validated.coverCredit === '' || validated.coverCredit === undefined ? null : validated.coverCredit
    const normalizedCoverSource = validated.coverSource === '' || validated.coverSource === undefined ? null : validated.coverSource
    const normalizedPublishedAt = validated.publishedAt
      ? new Date(validated.publishedAt)
      : validated.publishedAt === null
      ? null
      : undefined
    const normalizedGalleryMediaIds = validated.galleryMediaIds === undefined ? undefined : (validated.galleryMediaIds === null || validated.galleryMediaIds.length === 0 ? null : validated.galleryMediaIds)
    const normalizedCategorySlugs = validated.categorySlugs === undefined ? undefined : (validated.categorySlugs === null || validated.categorySlugs.length === 0 ? null : validated.categorySlugs)
    const normalizedDocuments = validated.documents === undefined ? undefined : (validated.documents === null || validated.documents.length === 0 ? null : validated.documents)
    const normalizedCollectionTags =
      validated.collectionTags === undefined
        ? undefined
        : validated.collectionTags === null || validated.collectionTags.length === 0
          ? []
          : normalizeCollectionTagsList(validated.collectionTags)

    await ensureArticleCompanyNewsColumn()
    await ensureArticleTypeColumn()
    const articleTypeRows = await prisma.$queryRawUnsafe<Array<{ article_type: string | null }>>(
      `SELECT "article_type" FROM "articles" WHERE "id" = $1 LIMIT 1`,
      id
    )
    const currentArticleType = (articleTypeRows[0]?.article_type || 'NEWS').toUpperCase()
    const nextArticleType =
      validated.articleType !== undefined ? validated.articleType : currentArticleType

    // Toujours dériver une valeur booléenne : si le client n’envoie pas `isCompanyNews`
    // (payload minimal, ancien front), reprendre la valeur en base pour éviter `updateData`
    // vide combiné à d’autres chemins et pour rester aligné avec l’article courant.
    let nextIsCompanyNews: boolean
    if (nextArticleType !== 'NEWS') {
      nextIsCompanyNews = false
    } else if (validated.isCompanyNews !== undefined) {
      nextIsCompanyNews = validated.isCompanyNews
    } else {
      nextIsCompanyNews = article.isCompanyNews
    }

    // Validate videoUrl (must be YouTube or Vimeo if provided)
    if (validated.videoUrl) {
      const youtubePattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/
      const vimeoPattern = /^(https?:\/\/)?(www\.)?vimeo\.com\/.+/
      if (!youtubePattern.test(validated.videoUrl) && !vimeoPattern.test(validated.videoUrl)) {
        return NextResponse.json(
          { error: 'Video URL must be from YouTube or Vimeo' },
          { status: 400 }
        )
      }
    }

    // Tags / catégories article (ArticleCategory) ou catégories offres (InvestmentCategory) — les deux sont acceptées.
    if (normalizedCategorySlugs && normalizedCategorySlugs.length > 0) {
      const [articleCats, investmentCats] = await Promise.all([
        prisma.articleCategory.findMany({
          where: { slug: { in: normalizedCategorySlugs }, isActive: true },
          select: { slug: true },
        }),
        prisma.investmentCategory.findMany({
          where: { slug: { in: normalizedCategorySlugs } },
          select: { slug: true },
        }),
      ])
      const allowed = new Set([
        ...articleCats.map((c) => c.slug),
        ...investmentCats.map((c) => c.slug),
      ])
      const missingSlugs = normalizedCategorySlugs.filter((slug) => !allowed.has(slug))
      if (missingSlugs.length > 0) {
        return NextResponse.json(
          {
            error: `Unknown categories (use Article or Investment category slugs): ${missingSlugs.join(', ')}`,
          },
          { status: 400 }
        )
      }
    }

    // If setting isFeatured=true, unset it on all other articles
    if (validated.isFeatured === true) {
      await prisma.article.updateMany({
        where: {
          id: { not: id },
          isFeatured: true,
        },
        data: {
          isFeatured: false,
        },
      })
    }

    // -------- Validation HELP : collection + helpSlug ; tags dans collection_tags.
    const nextHelpCollectionId =
      validated.helpCollectionId !== undefined
        ? validated.helpCollectionId
        : (article as any).helpCollectionId
    const nextHelpCategoryId =
      validated.helpCategoryId !== undefined
        ? validated.helpCategoryId
        : (article as any).helpCategoryId
    const nextHelpSlug =
      validated.helpSlug !== undefined ? validated.helpSlug : (article as any).helpSlug
    const nextAllowAnchors =
      validated.allowAnchors !== undefined
        ? validated.allowAnchors
        : (article as any).allowAnchors

    if (nextArticleType === 'HELP') {
      if (!nextHelpCollectionId || !nextHelpSlug) {
        return NextResponse.json(
          {
            error:
              'For articleType=HELP, helpCollectionId + helpSlug are required.',
          },
          { status: 400 },
        )
      }
      if (
        validated.helpSlug !== undefined ||
        validated.helpCollectionId !== undefined
      ) {
        const collision = await prisma.article.findFirst({
          where: {
            articleType: 'HELP',
            helpCollectionId: nextHelpCollectionId,
            helpSlug: nextHelpSlug,
            id: { not: id },
          },
          select: { id: true, slug: true },
        })
        if (collision) {
          return NextResponse.json(
            {
              error: `Un autre article HELP existe déjà dans cette collection avec helpSlug="${nextHelpSlug}" (id=${collision.id}).`,
            },
            { status: 400 },
          )
        }
      }
    }

    // -------- Validation ACADEMY : collection + academySlug (symétrique HELP).
    const nextAcademyCollectionId =
      validated.academyCollectionId !== undefined
        ? validated.academyCollectionId
        : (article as any).academyCollectionId
    const nextAcademyCategoryId =
      validated.academyCategoryId !== undefined
        ? validated.academyCategoryId
        : (article as any).academyCategoryId
    const nextAcademySlug =
      validated.academySlug !== undefined
        ? validated.academySlug
        : (article as any).academySlug

    if (nextArticleType === 'ACADEMY') {
      if (!nextAcademyCollectionId || !nextAcademySlug) {
        return NextResponse.json(
          {
            error:
              'For articleType=ACADEMY, academyCollectionId + academySlug are required.',
          },
          { status: 400 },
        )
      }
      if (
        validated.academySlug !== undefined ||
        validated.academyCollectionId !== undefined
      ) {
        const collision = await prisma.article.findFirst({
          where: {
            articleType: 'ACADEMY',
            academyCollectionId: nextAcademyCollectionId,
            academySlug: nextAcademySlug,
            id: { not: id },
          },
          select: { id: true, slug: true },
        })
        if (collision) {
          return NextResponse.json(
            {
              error: `Un autre article ACADEMY existe déjà dans cette collection avec academySlug="${nextAcademySlug}" (id=${collision.id}).`,
            },
            { status: 400 },
          )
        }
      }
    }

    // Build update data object
    const updateData: any = {}
    if (validated.slug) updateData.slug = validated.slug
    if (validated.coverMediaId !== undefined) updateData.coverMediaId = validated.coverMediaId
    if (validated.galleryMediaIds !== undefined) updateData.galleryMediaIds = normalizedGalleryMediaIds
    if (validated.videoUrl !== undefined) updateData.videoUrl = validated.videoUrl
    if (validated.categorySlugs !== undefined) updateData.categorySlugs = normalizedCategorySlugs
    if (validated.documents !== undefined) updateData.documents = normalizedDocuments
    if (validated.isFeatured !== undefined) updateData.isFeatured = validated.isFeatured
    if (validated.isHighlighted !== undefined) updateData.isHighlighted = validated.isHighlighted
    if (validated.isMilestone !== undefined) updateData.isMilestone = validated.isMilestone
    if (validated.coverTitle !== undefined) updateData.coverTitle = normalizedCoverTitle
    if (validated.coverCredit !== undefined) updateData.coverCredit = normalizedCoverCredit
    if (validated.coverSource !== undefined) updateData.coverSource = normalizedCoverSource
    if (validated.authorName) updateData.authorName = validated.authorName
    if (validated.authorRole !== undefined) updateData.authorRole = validated.authorRole
    if (validated.allowComments !== undefined) updateData.allowComments = validated.allowComments
    if (validated.status) updateData.status = validated.status
    if (normalizedPublishedAt !== undefined) updateData.publishedAt = normalizedPublishedAt
    updateData.isCompanyNews = nextIsCompanyNews

    if (normalizedCollectionTags !== undefined) {
      updateData.collectionTags = normalizedCollectionTags
    }
    // Champs HELP : on les set/clear selon le type final.
    if (nextArticleType === 'HELP') {
      updateData.helpCollectionId = nextHelpCollectionId
      updateData.helpCategoryId = nextHelpCategoryId
      updateData.helpSlug = nextHelpSlug
      if (validated.allowAnchors !== undefined) updateData.allowAnchors = nextAllowAnchors
      if (validated.targetTags !== undefined) {
        updateData.targetTags =
          validated.targetTags === null || validated.targetTags.length === 0
            ? null
            : validated.targetTags
      }
    } else if (
      validated.articleType !== undefined &&
      currentArticleType === 'HELP' &&
      validated.articleType !== 'HELP'
    ) {
      // Switch HELP → autre type : détache les liens HELP pour rester cohérent
      // avec la sémantique « N'ont de sens que lorsque articleType=HELP ».
      updateData.helpCollectionId = null
      updateData.helpCategoryId = null
      updateData.helpSlug = null
      updateData.targetTags = null
    } else {
      if (validated.helpCollectionId !== undefined)
        updateData.helpCollectionId = validated.helpCollectionId
      if (validated.helpCategoryId !== undefined)
        updateData.helpCategoryId = validated.helpCategoryId
      if (validated.helpSlug !== undefined) updateData.helpSlug = validated.helpSlug
      if (validated.allowAnchors !== undefined)
        updateData.allowAnchors = validated.allowAnchors
      if (validated.targetTags !== undefined) {
        updateData.targetTags =
          validated.targetTags === null || validated.targetTags.length === 0
            ? null
            : validated.targetTags
      }
    }

    // Champs ACADEMY (Phase 4 — symétrique HELP) : set/clear selon le type final.
    if (nextArticleType === 'ACADEMY') {
      updateData.academyCollectionId = nextAcademyCollectionId
      updateData.academyCategoryId = nextAcademyCategoryId
      updateData.academySlug = nextAcademySlug
      // allowAnchors + targetTags sont partagés entre HELP/ACADEMY ;
      // on les applique aussi côté ACADEMY si le client les envoie.
      if (validated.allowAnchors !== undefined && updateData.allowAnchors === undefined) {
        updateData.allowAnchors = validated.allowAnchors
      }
      if (validated.targetTags !== undefined && updateData.targetTags === undefined) {
        updateData.targetTags =
          validated.targetTags === null || validated.targetTags.length === 0
            ? null
            : validated.targetTags
      }
    } else if (
      validated.articleType !== undefined &&
      currentArticleType === 'ACADEMY' &&
      validated.articleType !== 'ACADEMY'
    ) {
      // Switch ACADEMY → autre type : détache les liens ACADEMY pour rester
      // cohérent avec la sémantique du schéma.
      updateData.academyCollectionId = null
      updateData.academyCategoryId = null
      updateData.academySlug = null
    } else {
      if (validated.academyCollectionId !== undefined)
        updateData.academyCollectionId = validated.academyCollectionId
      if (validated.academyCategoryId !== undefined)
        updateData.academyCategoryId = validated.academyCategoryId
      if (validated.academySlug !== undefined) updateData.academySlug = validated.academySlug
    }

    // Prisma rejette `update({ data: {} })`. Ex. : body avec seulement `articleType: "NEWS"` sans
    // `isCompanyNews` → aucun champ dans updateData avant le SQL `article_type`.
    const hasPrismaUpdates = Object.keys(updateData).length > 0

    // Update article
    let updated
    try {
      if (!hasPrismaUpdates) {
        updated = await prisma.article.findUnique({
          where: { id: id },
        })
        if (!updated) {
          return NextResponse.json({ error: 'Article not found' }, { status: 404 })
        }
      } else {
        updated = await prisma.article.update({
          where: { id: id },
          data: updateData,
        })
      }
    } catch (error) {
      if (isUnknownCompanyNewsArgumentError(error)) {
        await ensureArticleCompanyNewsColumn()
        await prisma.$executeRawUnsafe(
          `UPDATE "articles" SET "is_company_news" = $1 WHERE "id" = $2`,
          nextIsCompanyNews,
          id
        )
        const { isCompanyNews: _ignoredCompanyNews, ...updateDataWithoutCompanyNews } = updateData
        const hasAfterCn = Object.keys(updateDataWithoutCompanyNews).length > 0
        try {
          if (!hasAfterCn) {
            updated = await prisma.article.findUnique({
              where: { id: id },
            })
            if (!updated) {
              return NextResponse.json({ error: 'Article not found' }, { status: 404 })
            }
          } else {
            updated = await prisma.article.update({
              where: { id: id },
              data: updateDataWithoutCompanyNews,
            })
          }
        } catch (errorAfterCn) {
          if (isUnknownMilestoneArgumentError(errorAfterCn)) {
            if (validated.isMilestone !== undefined) {
              await ensureArticleMilestoneColumn()
              await prisma.$executeRawUnsafe(
                `UPDATE "articles" SET "is_milestone" = $1 WHERE "id" = $2`,
                validated.isMilestone,
                id
              )
            }
            const { isMilestone: _ignoredMilestone2, ...updateDataWithoutMilestone2 } =
              updateDataWithoutCompanyNews
            const hasOther2 = Object.keys(updateDataWithoutMilestone2).length > 0
            if (hasOther2) {
              updated = await prisma.article.update({
                where: { id: id },
                data: updateDataWithoutMilestone2,
              })
            } else {
              updated = await prisma.article.findUnique({
                where: { id: id },
              })
            }
          } else {
            const isMissingMilestoneColumn2 =
              errorAfterCn instanceof Prisma.PrismaClientKnownRequestError &&
              errorAfterCn.code === 'P2022' &&
              typeof errorAfterCn.meta?.column === 'string' &&
              errorAfterCn.meta.column.includes('is_milestone')
            if (isMissingMilestoneColumn2) {
              await ensureArticleMilestoneColumn()
              updated = await prisma.article.update({
                where: { id: id },
                data: updateDataWithoutCompanyNews,
              })
            } else {
              throw errorAfterCn
            }
          }
        }
      } else if (isUnknownMilestoneArgumentError(error)) {
        // Runtime Prisma client can be temporarily behind schema generation.
        // Fallback: persist milestone via SQL and retry Prisma update without that field.
        if (validated.isMilestone !== undefined) {
          await ensureArticleMilestoneColumn()
          await prisma.$executeRawUnsafe(
            `UPDATE "articles" SET "is_milestone" = $1 WHERE "id" = $2`,
            validated.isMilestone,
            id
          )
        }

        const { isMilestone: _ignoredMilestone, ...updateDataWithoutMilestone } = updateData
        const hasOtherUpdates = Object.keys(updateDataWithoutMilestone).length > 0

        if (hasOtherUpdates) {
          updated = await prisma.article.update({
            where: { id: id },
            data: updateDataWithoutMilestone,
          })
        } else {
          updated = await prisma.article.findUnique({
            where: { id: id },
          })
        }
      } else {
      const isMissingMilestoneColumn =
        error instanceof Prisma.PrismaClientKnownRequestError &&
        error.code === 'P2022' &&
        typeof error.meta?.column === 'string' &&
        error.meta.column.includes('is_milestone')

        if (isMissingMilestoneColumn) {
          await ensureArticleMilestoneColumn()
          updated = await prisma.article.update({
            where: { id: id },
            data: updateData,
          })
        } else {
          throw error
        }
      }
    }

    if (validated.articleType !== undefined) {
      await ensureArticleTypeColumn()
      await prisma.$executeRawUnsafe(
        `UPDATE "articles" SET "article_type" = $1 WHERE "id" = $2`,
        validated.articleType,
        id
      )
      // `is_company_news` n'a de sens que pour `NEWS` — on le désarme pour
      // tous les autres types (ANALYSIS, RESEARCH, ACADEMY, USER_BLOG…).
      if (validated.articleType !== 'NEWS') {
        await ensureArticleCompanyNewsColumn()
        await prisma.$executeRawUnsafe(
          `UPDATE "articles" SET "is_company_news" = false WHERE "id" = $1`,
          id
        )
      }
    }

    return NextResponse.json({ article: updated })
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('Zod validation error:', error.issues)
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating article:', error)
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: errorMessage,
        ...(process.env.NODE_ENV === 'development' && { stack: error instanceof Error ? error.stack : undefined })
      },
      { status: 500 }
    )
  }
}

// DELETE /api/admin/articles/[id]
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } | Promise<{ id: string }> }
) {
  try {
    const { id } = await awaitRouteParams(params)
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const article = await prisma.article.findUnique({
      where: { id },
    })

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    await prisma.article.delete({
      where: { id },
    })

    return NextResponse.json({ message: 'Article deleted' })
  } catch (error) {
    console.error('Error deleting article:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

