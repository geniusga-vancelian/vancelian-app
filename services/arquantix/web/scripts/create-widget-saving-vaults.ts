import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

const FEED_SLUG = 'saving-vaults'
const FEED_NAME = 'Feed Saving Vaults'
const WIDGET_SLUG = 'widget-saving-vaults-marketing-paysage'
const WIDGET_NAME = 'Widget Saving Vaults - Marketing Paysage'

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
        feedType: 'vaults_by_investment_type',
        source: {
          locale: 'fr',
          investmentTypeSlug: 'saving-vaults',
          limit: 20,
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
        feedType: 'vaults_by_investment_type',
        source: {
          locale: 'fr',
          investmentTypeSlug: 'saving-vaults',
          limit: 20,
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
        title: WIDGET_NAME,
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
            title: 'Saving Vaults',
            visibleCardsCount: 1.2,
            cardAspectRatio: '3:4',
            feedSlug: FEED_SLUG,
            feedBinding: {
              list: 'items',
              itemToCard: {
                imageUrl: 'coverImage',
                redirectUrl: 'urlPath',
                title: 'title',
                description: 'description',
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
        title: WIDGET_NAME,
        feedSlugs: [FEED_SLUG],
        modules: [
          {
            type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
            title: 'Saving Vaults',
            visibleCardsCount: 1.2,
            cardAspectRatio: '3:4',
            feedSlug: FEED_SLUG,
            feedBinding: {
              list: 'items',
              itemToCard: {
                imageUrl: 'coverImage',
                redirectUrl: 'urlPath',
                title: 'title',
                description: 'description',
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
