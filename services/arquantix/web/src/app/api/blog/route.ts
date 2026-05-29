import { NextRequest, NextResponse } from 'next/server'
import { Prisma } from '@prisma/client'

import { logMobileApiFailure, mobileApiJsonError, safeApiMessageForClient } from '@/lib/api/mobile-json-error'
import { prisma } from '@/lib/prisma'
import { defaultLocale, getLocaleOrDefault } from '@/config/locales'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { absolutizeBlogFeedResultForMobile } from '@/lib/blog/absolutizeBlogApiForMobile'
import { getBlogFeed, type BlogFeedSegment } from '@/lib/blog/articleService'
import { formatDatabaseUrlTarget } from '@/lib/db/diagnostics'
import { resolveRequestPublicOrigin } from '@/lib/http/resolveRequestPublicOrigin'
import { resolveLabelWithFallback } from '@/lib/i18n/resolveLabel'

export async function GET(request: NextRequest) {
  const routeStarted = Date.now()
  const dbTarget = formatDatabaseUrlTarget(process.env.DATABASE_URL)

  try {
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || defaultLocale
    const locale = getLocaleOrDefault(localeParam)
    const category = searchParams.get('category') ?? undefined
    const articleTypeParam = (searchParams.get('articleType') || '').toUpperCase()
    const articleType =
      articleTypeParam === 'ANALYSIS' || articleTypeParam === 'NEWS'
        ? (articleTypeParam as 'NEWS' | 'ANALYSIS')
        : undefined
    const page = parseInt(searchParams.get('page') || '1', 10)
    const pageSize = Math.min(
      Math.max(parseInt(searchParams.get('pageSize') || '10', 10), 1),
      50
    )

    const segmentRaw = (searchParams.get('segment') || '').toLowerCase()
    const segment: BlogFeedSegment | undefined =
      segmentRaw === 'market' || segmentRaw === 'company' || segmentRaw === 'analysis'
        ? (segmentRaw as BlogFeedSegment)
        : undefined

    console.info('[api/blog] GET start', {
      db: dbTarget,
      locale,
      category,
      articleType,
      segment,
      page,
      pageSize,
    })

    // Thematic categories (investment_categories) — used by Flutter + web.
    const catStarted = Date.now()
    let categoriesRaw: Awaited<ReturnType<typeof prisma.investmentCategory.findMany>>
    try {
      categoriesRaw = await prisma.investmentCategory.findMany({
        orderBy: [{ sortOrder: 'asc' }, { label: 'asc' }],
      })
    } catch (err) {
      logPrismaFailure('[api/blog] investmentCategory.findMany failed', err, {
        db: dbTarget,
        ms: Date.now() - catStarted,
      })
      throw err
    }
    console.info('[api/blog] investmentCategory.findMany ok', {
      ms: Date.now() - catStarted,
      count: categoriesRaw.length,
    })

    const categories = categoriesRaw.map((cat) => ({
      id: cat.id,
      slug: cat.slug,
      label: cat.label,
    }))

    const articleCategoriesStarted = Date.now()
    let articleCategories: Array<{ id: string; slug: string; label: string }> = []
    try {
      const articleCatsRaw = await prisma.articleCategory.findMany({
        where: { isActive: true },
        orderBy: [{ order: 'asc' }, { label: 'asc' }],
        include: { i18n: true },
      })
      articleCategories = articleCatsRaw.map((cat) => ({
        id: cat.id,
        slug: cat.slug,
        label: resolveLabelWithFallback({
          requestedLocale: locale,
          baseLabel: cat.label,
          i18nRows: cat.i18n.map((i) => ({ locale: i.locale, label: i.label })),
        }),
      }))
    } catch (err) {
      logPrismaFailure('[api/blog] articleCategory.findMany failed', err, {
        db: dbTarget,
        ms: Date.now() - articleCategoriesStarted,
      })
      throw err
    }

    const feedStarted = Date.now()
    const feed = absolutizeBlogFeedResultForMobile(
      await getBlogFeed(
        {
          locale,
          category,
          articleType,
          segment,
          page,
          pageSize,
        },
        calculateReadingTime,
      ),
      resolveRequestPublicOrigin(request),
    )
    console.info('[api/blog] getBlogFeed ok', {
      ms: Date.now() - feedStarted,
      total: feed.pagination.total,
      featured: !!feed.featured,
      highlighted: feed.highlighted.length,
      articles: feed.articles.length,
    })

    const cmsEmpty =
      categories.length === 0 &&
      articleCategories.length === 0 &&
      !feed.featured &&
      feed.highlighted.length === 0 &&
      feed.companyNews.length === 0 &&
      feed.articles.length === 0 &&
      feed.pagination.total === 0
    if (cmsEmpty) {
      console.warn('[api/blog] blog feed empty (no categories and no published articles)', {
        db: dbTarget,
        locale,
      })
    }

    console.info('[api/blog] GET done', { ms: Date.now() - routeStarted })

    return NextResponse.json({
      featured: feed.featured,
      highlighted: feed.highlighted,
      companyNews: feed.companyNews,
      articles: feed.articles,
      categories,
      articleCategories,
      pagination: {
        page: feed.pagination.page,
        pageSize: feed.pagination.pageSize,
        total: feed.pagination.total,
        hasMore: feed.pagination.hasMore,
      },
    })
  } catch (error) {
    logMobileApiFailure('[api/blog] GET', error, {
      db: dbTarget,
      ms: Date.now() - routeStarted,
      ...serializeError(error),
    })
    return mobileApiJsonError(500, safeApiMessageForClient(error))
  }
}

function serializeError(error: unknown): { name?: string; message: string; code?: string; meta?: unknown } {
  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    return {
      name: error.name,
      message: error.message,
      code: error.code,
      meta: error.meta,
    }
  }
  if (error instanceof Prisma.PrismaClientValidationError) {
    return { name: error.name, message: error.message }
  }
  if (error instanceof Error) {
    return { name: error.name, message: error.message }
  }
  return { message: String(error) }
}

function logPrismaFailure(
  label: string,
  err: unknown,
  extra: Record<string, unknown>
): void {
  const base = { ...extra, ...serializeError(err) }
  console.error(label, base)
}
