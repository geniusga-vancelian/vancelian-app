import { ContentStatus } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { getCompanyNewsArticleIds } from '@/lib/blog/articleService'
import { pickArticleI18n } from '@/lib/blog/articleI18nFallback'
import { absolutizeMediaUrlForApiClient } from '@/lib/catalog/packagedCatalogHelpers'
import {
  parseTop10NewsWidget,
  type PortalNewsWidgetData,
} from '@/lib/portal/parseTop10NewsWidget'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { getPresignedUrl } from '@/lib/storage/storageClient'

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'
const TOP10_NEWS_SLUG = 'top10news'

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asInt(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return Math.floor(value)
  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function estimateReadingTime(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length
  if (words <= 0) return 1
  return Math.max(1, Math.round(words / 200))
}

function categoryLabelsForSlugs(
  categorySlugs: unknown,
  labelBySlug: Map<string, string>,
): string[] {
  if (!Array.isArray(categorySlugs)) return []
  const out: string[] = []
  for (const raw of categorySlugs) {
    const slug = String(raw).trim()
    if (!slug) continue
    const label = labelBySlug.get(slug)
    if (label && label.trim().length > 0) out.push(label.trim())
  }
  return out
}

async function resolveTop10NewsFeedItems(
  feedSchema: Record<string, unknown>,
  locale: string,
  publicOrigin: string | null,
): Promise<Array<Record<string, unknown>>> {
  const absCover = (url: string | null | undefined): string =>
    absolutizeMediaUrlForApiClient(url ?? null, publicOrigin) ?? ''

  const source = asRecord(feedSchema.source) ?? {}
  const limit = Math.max(1, Math.min(50, asInt(source.limit, 10)))
  const dateFormatter = new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })

  const companyIds = await getCompanyNewsArticleIds()
  const raw =
    companyIds.length === 0
      ? []
      : await prisma.article.findMany({
          where: {
            id: { in: companyIds },
            status: ContentStatus.PUBLISHED,
          },
          orderBy: [{ publishedAt: 'desc' }, { createdAt: 'desc' }],
          include: {
            i18n: true,
            coverMedia: true,
          },
          take: limit,
        })

  const allCategorySlugs = raw
    .flatMap((a) => (Array.isArray(a.categorySlugs) ? a.categorySlugs : []))
    .map((v) => String(v))
    .filter(Boolean)
  const uniqueCategorySlugs = Array.from(new Set(allCategorySlugs))
  const categories = uniqueCategorySlugs.length
    ? await prisma.articleCategory.findMany({
        where: { slug: { in: uniqueCategorySlugs } },
        include: {
          i18n: {
            where: { locale },
            take: 1,
          },
        },
      })
    : []
  const categoryLabelBySlug = new Map<string, string>()
  for (const cat of categories) {
    categoryLabelBySlug.set(cat.slug, cat.i18n[0]?.label ?? cat.label)
  }

  return Promise.all(
    raw.map(async (a) => {
      let coverUrl = a.coverMedia?.url || ''
      if (a.coverMedia?.key) {
        try {
          coverUrl = await getPresignedUrl(a.coverMedia.key, 3600)
        } catch {
          coverUrl = a.coverMedia.url
        }
      }
      const publishedRef = a.publishedAt ?? a.createdAt
      const categorySlug =
        Array.isArray(a.categorySlugs) && a.categorySlugs.length > 0 ? String(a.categorySlugs[0]) : ''
      const categoryLabel = categorySlug ? (categoryLabelBySlug.get(categorySlug) ?? '') : ''
      const categoryLabels = categoryLabelsForSlugs(a.categorySlugs, categoryLabelBySlug)
      const i18n = pickArticleI18n(a.i18n, locale)
      const standfirst = i18n?.standfirst ?? ''
      return {
        id: a.id,
        slug: a.slug,
        title: i18n?.title ?? a.slug,
        authorName: a.authorName,
        publishedAt: a.publishedAt?.toISOString() ?? null,
        publishedDate: publishedRef ? dateFormatter.format(publishedRef) : '',
        coverUrl: absCover(coverUrl),
        readingTime: estimateReadingTime(standfirst),
        categorySlug: categorySlug || null,
        categoryLabel: categoryLabel || null,
        categoryLabels: categoryLabels.length > 0 ? categoryLabels : null,
        articleType: a.articleType,
        isCompanyNews: true,
      }
    }),
  )
}

/** Charge le widget dashboard news sans fetch HTTP loopback. */
export async function loadPortalTop10NewsWidget(
  locale: string,
  publicOrigin: string | null = null,
): Promise<PortalNewsWidgetData | null> {
  const widget = await prisma.dsComponent.findFirst({
    where: {
      slug: TOP10_NEWS_SLUG,
      chapter: { slug: WIDGETS_CHAPTER_SLUG },
    },
  })
  if (!widget) return null

  const feed = await prisma.dsComponent.findFirst({
    where: {
      slug: TOP10_NEWS_SLUG,
      chapter: { slug: FEEDS_CHAPTER_SLUG },
    },
  })
  if (!feed) return null

  const feedSchema = asRecord(feed.schemaJson) ?? {}
  const items = await resolveTop10NewsFeedItems(feedSchema, locale, publicOrigin)
  const payload = {
    widget: {
      id: widget.id,
      slug: widget.slug,
      name: widget.name,
      schemaJson: widget.schemaJson,
    },
    feeds: {
      [TOP10_NEWS_SLUG]: {
        feedType: asString(feedSchema.feedType, 'top10_news'),
        items,
      },
    },
    meta: { locale, assetSlug: null },
  }

  const parsed = parseTop10NewsWidget(payload)
  if (!parsed || parsed.items.length === 0) {
    return { title: 'Latest news', items: [], headerHref: PORTAL_ROUTES.academy }
  }
  return parsed
}
