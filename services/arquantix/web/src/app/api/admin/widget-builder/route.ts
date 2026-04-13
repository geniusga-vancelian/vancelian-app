import { NextRequest, NextResponse } from 'next/server'

import { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

type JsonRecord = Record<string, unknown>

async function ensureChapters() {
  const [widgetsChapter, feedsChapter] = await Promise.all([
    prisma.dsComponentChapter.upsert({
      where: { slug: WIDGETS_CHAPTER_SLUG },
      update: {},
      create: {
        slug: WIDGETS_CHAPTER_SLUG,
        name: 'Widget Builder — Widgets',
        order: 200,
      },
    }),
    prisma.dsComponentChapter.upsert({
      where: { slug: FEEDS_CHAPTER_SLUG },
      update: {},
      create: {
        slug: FEEDS_CHAPTER_SLUG,
        name: 'Widget Builder — Feeds',
        order: 201,
      },
    }),
  ])
  return { widgetsChapter, feedsChapter }
}

function defaultFeedSchema(slug: string, name: string): JsonRecord {
  return {
    type: 'feed',
    key: slug,
    title: name,
    feedType: 'blog_articles',
    source: {
      locale: 'fr',
      categorySlug: '',
      limit: 10,
    },
  }
}

function defaultWidgetSchema(slug: string, name: string): JsonRecord {
  return {
    type: 'widget',
    key: slug,
    title: name,
    modules: [],
    feedSlugs: [],
  }
}

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as JsonRecord
}

/** Widgets page détail asset : Blog à la une + Recherche à la une (visibles dans le Widget Builder). */
async function ensureAssetDetailWidgets(
  widgetsChapter: { id: string },
  feedsChapter: { id: string }
) {
  const blogFeedSlug = 'blog-a-la-une'
  const researchFeedSlug = 'research-a-la-une'

  await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: { chapterId: feedsChapter.id, slug: blogFeedSlug },
    },
    update: {
      name: 'BlogALaUne',
      schemaJson: {
        type: 'feed',
        key: blogFeedSlug,
        title: 'BlogALaUne',
        feedType: 'blog_crypto_asset',
        source: { limit: 10 },
      },
    },
    create: {
      chapterId: feedsChapter.id,
      slug: blogFeedSlug,
      name: 'BlogALaUne',
      schemaJson: {
        type: 'feed',
        key: blogFeedSlug,
        title: 'BlogALaUne',
        feedType: 'blog_crypto_asset',
        source: { limit: 10 },
      },
    },
  })

  await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: { chapterId: feedsChapter.id, slug: researchFeedSlug },
    },
    update: {
      name: 'ResearchALaUne',
      schemaJson: {
        type: 'feed',
        key: researchFeedSlug,
        title: 'ResearchALaUne',
        feedType: 'research_crypto_asset',
        source: { limit: 10 },
      },
    },
    create: {
      chapterId: feedsChapter.id,
      slug: researchFeedSlug,
      name: 'ResearchALaUne',
      schemaJson: {
        type: 'feed',
        key: researchFeedSlug,
        title: 'ResearchALaUne',
        feedType: 'research_crypto_asset',
        source: { limit: 10 },
      },
    },
  })

  const blogWidgetSchema = {
    type: 'widget',
    key: blogFeedSlug,
    title: 'À la une',
    feedSlugs: [blogFeedSlug],
    modules: [
      {
        type: 'BlogALaUne',
        title: 'À la une',
        feedSlug: blogFeedSlug,
        feedBinding: {
          list: 'items',
          itemToCard: {
            coverUrl: 'coverUrl',
            redirectUrl: 'slug',
            title: 'title',
            readingTime: 'readingTime',
            tag: 'categoryLabel',
            metaText: 'publishedDate',
            authorName: 'authorName',
          },
        },
      },
    ],
  }

  await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: { chapterId: widgetsChapter.id, slug: blogFeedSlug },
    },
    update: { name: 'Blog à la une', schemaJson: blogWidgetSchema },
    create: {
      chapterId: widgetsChapter.id,
      slug: blogFeedSlug,
      name: 'Blog à la une',
      schemaJson: blogWidgetSchema,
    },
  })

  const researchWidgetSchema = {
    type: 'widget',
    key: researchFeedSlug,
    title: 'Recherche à la une',
    feedSlugs: [researchFeedSlug],
    modules: [
      {
        type: 'BlogALaUne',
        title: 'Recherche à la une',
        feedSlug: researchFeedSlug,
        feedBinding: {
          list: 'items',
          itemToCard: {
            coverUrl: 'coverUrl',
            redirectUrl: 'slug',
            title: 'title',
            readingTime: 'readingTime',
            tag: 'categoryLabel',
            metaText: 'publishedDate',
            authorName: 'authorName',
          },
        },
      },
    ],
  }

  await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: { chapterId: widgetsChapter.id, slug: researchFeedSlug },
    },
    update: { name: 'Recherche à la une', schemaJson: researchWidgetSchema },
    create: {
      chapterId: widgetsChapter.id,
      slug: researchFeedSlug,
      name: 'Recherche à la une',
      schemaJson: researchWidgetSchema,
    },
  })
}

export async function GET() {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { widgetsChapter, feedsChapter } = await ensureChapters()
    await ensureAssetDetailWidgets(widgetsChapter, feedsChapter)

    const [widgets, feeds] = await Promise.all([
      prisma.dsComponent.findMany({
        where: { chapterId: widgetsChapter.id },
        orderBy: { createdAt: 'desc' },
      }),
      prisma.dsComponent.findMany({
        where: { chapterId: feedsChapter.id },
        orderBy: { createdAt: 'desc' },
      }),
    ])

    return NextResponse.json({ widgets, feeds })
  } catch (error) {
    console.error('[api/admin/widget-builder]', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = (await request.json()) as {
      kind?: 'widget' | 'feed'
      slug?: string
      name?: string
      schemaJson?: unknown
    }
    const kind = body.kind
    const slug = (body.slug ?? '').trim()
    const name = (body.name ?? '').trim()

    if (kind !== 'widget' && kind !== 'feed') {
      return NextResponse.json({ error: 'kind must be "widget" or "feed"' }, { status: 400 })
    }
    if (!slug) {
      return NextResponse.json({ error: 'slug is required' }, { status: 400 })
    }
    if (!name) {
      return NextResponse.json({ error: 'name is required' }, { status: 400 })
    }

    const { widgetsChapter, feedsChapter } = await ensureChapters()
    const chapterId = kind === 'widget' ? widgetsChapter.id : feedsChapter.id
    const schemaInput = asRecord(body.schemaJson)
    const schemaJson =
      schemaInput ??
      (kind === 'widget' ? defaultWidgetSchema(slug, name) : defaultFeedSchema(slug, name))

    const existingBySlug = await prisma.dsComponent.findFirst({
      where: { slug },
      select: { id: true },
    })
    if (existingBySlug) {
      return NextResponse.json({ error: `Slug already exists: "${slug}"` }, { status: 409 })
    }

    const created = await prisma.dsComponent.create({
      data: {
        chapterId,
        slug,
        name,
        schemaJson: schemaJson as Prisma.InputJsonValue,
      },
    })

    return NextResponse.json({ component: created }, { status: 201 })
  } catch (error) {
    console.error('[api/admin/widget-builder POST]', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
