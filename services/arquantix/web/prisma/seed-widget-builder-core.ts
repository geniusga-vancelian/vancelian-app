/**
 * Seed idempotent : chapitres Widget Builder, feeds vaults/bundles, widgets associés,
 * et layout `offers_layout` (référence ces widgets).
 * À exécuter après seedDsComponents() (chapitre component_ds_flutter requis).
 */
import { PrismaClient } from '@prisma/client'

const WIDGETS_CHAPTER_SLUG = 'widget_builder_widgets'
const FEEDS_CHAPTER_SLUG = 'widget_builder_feeds'

const SAVING_VAULTS_FEED_SLUG = 'saving-vaults'
const SAVING_VAULTS_WIDGET_SLUG = 'widget-saving-vaults-marketing-paysage'
const CRYPTO_BUNDLES_FEED_SLUG = 'crypto-bundles'
const CRYPTO_BUNDLES_WIDGET_SLUG = 'crypto-bundles-widget'

/** Feed blog top 10 — utilisé par le dashboard Flutter (VaultsMarketingCardsFeed). */
const TOP10_NEWS_FEED_SLUG = 'top10news'
const TOP10_NEWS_WIDGET_SLUG = 'top10news'

const top10NewsFeedSchema = {
  type: 'feed',
  key: TOP10_NEWS_FEED_SLUG,
  title: 'Top10News',
  feedType: 'top10_news',
  source: {
    locale: 'fr',
    limit: 10,
  },
} as const

const top10NewsWidgetSchema = {
  type: 'widget',
  key: TOP10_NEWS_WIDGET_SLUG,
  title: 'Vancelian News',
  titleRedirect: {
    type: 'internal',
    target: 'blog',
  },
  feedSlugs: [TOP10_NEWS_FEED_SLUG],
  modules: [
    {
      type: 'BlogALaUne',
      title: 'Vancelian News',
      feedSlug: TOP10_NEWS_FEED_SLUG,
      feedBinding: {
        list: 'items',
        itemToCard: {
          coverUrl: 'coverUrl',
          redirectUrl: 'slug',
          title: 'title',
          readingTime: 'readingTime',
          tag: 'categoryLabel',
        },
      },
    },
  ],
} as const

const offersLayoutSchema = {
  type: 'layout',
  key: 'offers_layout',
  title: 'Offers layout',
  structure: {
    header: {
      background: {
        imageUrl: 'media/1774391838266-slqzb6n7vfi.png',
      },
    },
    body: {
      widgets: [
        {
          key: 'saving_vaults_widget',
          type: 'widget_builder_widget',
          title: 'Saving Vaults',
          widgetSlug: SAVING_VAULTS_WIDGET_SLUG,
        },
        {
          key: 'crypto_bundles_widget',
          type: 'widget_builder_widget',
          title: 'Thematic investing',
          widgetSlug: CRYPTO_BUNDLES_WIDGET_SLUG,
        },
        {
          key: 'investment_categories',
          type: 'investment_categories_filter',
          title: 'Investment categories',
        },
        {
          key: 'exclusive_offers',
          type: 'exclusive_offers_list_widget',
          title: 'Top exclusive offers',
        },
      ],
    },
  },
} as const

export async function seedWidgetBuilderCore(db: PrismaClient) {
  const flutterChapter = await db.dsComponentChapter.findUnique({
    where: { slug: 'component_ds_flutter' },
    select: { id: true },
  })
  if (!flutterChapter) {
    throw new Error(
      'Chapter "component_ds_flutter" introuvable : exécuter seedDsComponents() avant seedWidgetBuilderCore()'
    )
  }

  const [widgetsChapter, feedsChapter] = await Promise.all([
    db.dsComponentChapter.upsert({
      where: { slug: WIDGETS_CHAPTER_SLUG },
      update: {},
      create: {
        slug: WIDGETS_CHAPTER_SLUG,
        name: 'Widget Builder — Widgets',
        order: 200,
      },
    }),
    db.dsComponentChapter.upsert({
      where: { slug: FEEDS_CHAPTER_SLUG },
      update: {},
      create: {
        slug: FEEDS_CHAPTER_SLUG,
        name: 'Widget Builder — Feeds',
        order: 201,
      },
    }),
  ])
  console.log('Widget builder chapters:', widgetsChapter.slug, feedsChapter.slug)

  const savingVaultsFeedSchema = {
    type: 'feed',
    key: SAVING_VAULTS_FEED_SLUG,
    title: 'Feed Saving Vaults',
    feedType: 'vaults_by_investment_type',
    source: {
      locale: 'fr',
      investmentTypeSlug: 'saving-vaults',
      limit: 20,
    },
  } as const

  const savingVaultsWidgetSchema = {
    type: 'widget',
    key: SAVING_VAULTS_WIDGET_SLUG,
    title: 'Widget Saving Vaults - Marketing Paysage',
    feedSlugs: [SAVING_VAULTS_FEED_SLUG],
    modules: [
      {
        type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
        title: 'Saving Vaults',
        visibleCardsCount: 1.2,
        cardAspectRatio: '3:4',
        feedSlug: SAVING_VAULTS_FEED_SLUG,
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
  } as const

  const cryptoBundlesFeedSchema = {
    type: 'feed',
    key: CRYPTO_BUNDLES_FEED_SLUG,
    title: 'Crypto Bundles Vault Feed',
    feedType: 'vaults_by_investment_type',
    source: {
      locale: 'fr',
      investmentTypeSlug: 'crypto-bundles',
      limit: 100,
    },
  } as const

  const cryptoBundlesWidgetSchema = {
    type: 'widget',
    key: CRYPTO_BUNDLES_WIDGET_SLUG,
    title: 'Widget Crypto Bundles - Marketing Paysage',
    feedSlugs: [CRYPTO_BUNDLES_FEED_SLUG],
    modules: [
      {
        type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
        title: 'Crypto Bundles',
        visibleCardsCount: 1.2,
        cardAspectRatio: '3:4',
        feedSlug: CRYPTO_BUNDLES_FEED_SLUG,
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
  } as const

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: feedsChapter.id,
        slug: SAVING_VAULTS_FEED_SLUG,
      },
    },
    update: { name: 'Feed Saving Vaults', schemaJson: savingVaultsFeedSchema },
    create: {
      chapterId: feedsChapter.id,
      slug: SAVING_VAULTS_FEED_SLUG,
      name: 'Feed Saving Vaults',
      schemaJson: savingVaultsFeedSchema,
    },
  })

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: widgetsChapter.id,
        slug: SAVING_VAULTS_WIDGET_SLUG,
      },
    },
    update: { name: 'Widget Saving Vaults - Marketing Paysage', schemaJson: savingVaultsWidgetSchema },
    create: {
      chapterId: widgetsChapter.id,
      slug: SAVING_VAULTS_WIDGET_SLUG,
      name: 'Widget Saving Vaults - Marketing Paysage',
      schemaJson: savingVaultsWidgetSchema,
    },
  })

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: feedsChapter.id,
        slug: CRYPTO_BUNDLES_FEED_SLUG,
      },
    },
    update: { name: 'Crypto Bundles Vault Feed', schemaJson: cryptoBundlesFeedSchema },
    create: {
      chapterId: feedsChapter.id,
      slug: CRYPTO_BUNDLES_FEED_SLUG,
      name: 'Crypto Bundles Vault Feed',
      schemaJson: cryptoBundlesFeedSchema,
    },
  })

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: widgetsChapter.id,
        slug: CRYPTO_BUNDLES_WIDGET_SLUG,
      },
    },
    update: { name: 'Widget Crypto Bundles - Marketing Paysage', schemaJson: cryptoBundlesWidgetSchema },
    create: {
      chapterId: widgetsChapter.id,
      slug: CRYPTO_BUNDLES_WIDGET_SLUG,
      name: 'Widget Crypto Bundles - Marketing Paysage',
      schemaJson: cryptoBundlesWidgetSchema,
    },
  })

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: feedsChapter.id,
        slug: TOP10_NEWS_FEED_SLUG,
      },
    },
    update: { name: 'Top10News', schemaJson: top10NewsFeedSchema },
    create: {
      chapterId: feedsChapter.id,
      slug: TOP10_NEWS_FEED_SLUG,
      name: 'Top10News',
      schemaJson: top10NewsFeedSchema,
    },
  })

  await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: widgetsChapter.id,
        slug: TOP10_NEWS_WIDGET_SLUG,
      },
    },
    update: { name: 'Vancelian News', schemaJson: top10NewsWidgetSchema },
    create: {
      chapterId: widgetsChapter.id,
      slug: TOP10_NEWS_WIDGET_SLUG,
      name: 'Vancelian News',
      schemaJson: top10NewsWidgetSchema,
    },
  })

  const offersLayout = await db.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: flutterChapter.id,
        slug: 'offers_layout',
      },
    },
    update: {
      name: 'Offers layout',
      schemaJson: offersLayoutSchema,
    },
    create: {
      chapterId: flutterChapter.id,
      slug: 'offers_layout',
      name: 'Offers layout',
      schemaJson: offersLayoutSchema,
    },
  })
  console.log('Component:', offersLayout.slug, offersLayout.id)
}
