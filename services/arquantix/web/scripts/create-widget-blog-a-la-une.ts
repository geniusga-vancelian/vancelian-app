import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

const FEED_SLUG = 'blog-a-la-une'
const FEED_NAME = 'BlogALaUne'
const WIDGET_SLUG = 'blog-a-la-une'
const WIDGET_NAME = 'Blog à la une'

/**
 * Crée le feed et le widget "Blog à la une" pour la page détail d'un asset crypto.
 * Le feed est filtré par crypto via le paramètre assetSlug (ex. btc, eth) passé en query à l'API.
 * GET /api/mobile/flutter/widgets/blog-a-la-une?locale=fr&assetSlug=btc
 */
async function main() {
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

  const feed = await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: feedsChapter.id,
        slug: FEED_SLUG,
      },
    },
    update: {
      name: FEED_NAME,
      schemaJson: {
        type: 'feed',
        key: FEED_SLUG,
        title: FEED_NAME,
        feedType: 'blog_crypto_asset',
        source: {
          limit: 10,
        },
      },
    },
    create: {
      chapterId: feedsChapter.id,
      slug: FEED_SLUG,
      name: FEED_NAME,
      schemaJson: {
        type: 'feed',
        key: FEED_SLUG,
        title: FEED_NAME,
        feedType: 'blog_crypto_asset',
        source: {
          limit: 10,
        },
      },
    },
  })

  const widget = await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: widgetsChapter.id,
        slug: WIDGET_SLUG,
      },
    },
    update: {
      name: WIDGET_NAME,
      schemaJson: {
        type: 'widget',
        key: WIDGET_SLUG,
        title: 'À la une',
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'BlogALaUne',
            title: 'À la une',
            feedSlug: FEED_SLUG,
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
      },
    },
    create: {
      chapterId: widgetsChapter.id,
      slug: WIDGET_SLUG,
      name: WIDGET_NAME,
      schemaJson: {
        type: 'widget',
        key: WIDGET_SLUG,
        title: 'À la une',
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'BlogALaUne',
            title: 'À la une',
            feedSlug: FEED_SLUG,
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
      },
    },
  })

  console.log('Feed created/updated:', feed.slug, feed.id)
  console.log('Widget created/updated:', widget.slug, widget.id)
  console.log('Use: GET /api/mobile/flutter/widgets/blog-a-la-une?locale=fr&assetSlug=btc')
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
