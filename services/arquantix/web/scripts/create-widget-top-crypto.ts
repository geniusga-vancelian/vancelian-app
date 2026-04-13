import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

const FEED_SLUG = 'top-crypto'
const FEED_NAME = 'Top Crypto Feed (Mock)'
const WIDGET_SLUG = 'top-crypto-widget'
const WIDGET_NAME = 'Widget Top Crypto'

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
        feedType: 'top_crypto_mock',
        source: {
          locale: 'fr',
          limit: 5,
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
        feedType: 'top_crypto_mock',
        source: {
          locale: 'fr',
          limit: 5,
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
        title: 'Top Crypto',
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'TopCryptoModule',
            title: 'Top Crypto',
            seeMoreLabel: 'See more',
            seeMoreRedirect: 'all_crypto',
            tabs: {
              popular: 'Populaires',
              gainers: 'Top Gainers',
              losers: 'Top Losers',
            },
            feedSlug: FEED_SLUG,
            feedBinding: {
              popular: 'popular',
              gainers: 'topGainers',
              losers: 'topLosers',
              itemToAsset: {
                name: 'name',
                ticker: 'ticker',
                price: 'price',
                variationPercent: 'variationPercent',
                redirectUrl: 'redirectUrl',
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
        title: 'Top Crypto',
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'TopCryptoModule',
            title: 'Top Crypto',
            seeMoreLabel: 'See more',
            seeMoreRedirect: 'all_crypto',
            tabs: {
              popular: 'Populaires',
              gainers: 'Top Gainers',
              losers: 'Top Losers',
            },
            feedSlug: FEED_SLUG,
            feedBinding: {
              popular: 'popular',
              gainers: 'topGainers',
              losers: 'topLosers',
              itemToAsset: {
                name: 'name',
                ticker: 'ticker',
                price: 'price',
                variationPercent: 'variationPercent',
                redirectUrl: 'redirectUrl',
              },
            },
          },
        ],
      },
    },
  })

  console.log('Feed created/updated:', feed.slug, feed.id)
  console.log('Widget created/updated:', widget.slug, widget.id)
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
