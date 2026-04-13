/**
 * Seed script to create Help Center CMS template pages
 * Run with: npm run db:seed-help-cms
 */

import { PrismaClient, ContentStatus } from '@prisma/client'
import { defaultLocale } from '../src/config/locales'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding Help Center CMS pages...')

  // 1. Create /help page (collections landing)
  const helpPage = await prisma.page.upsert({
    where: { slug: 'help' },
    update: {},
    create: {
      slug: 'help',
      urlPath: '/help',
      template: 'default',
      themeColor: 'light',
    },
  })

  // Sections for /help page
  const helpHeroSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpPage.id, key: 'help_hero_v1' } },
    update: {},
    create: {
      pageId: helpPage.id,
      key: 'help_hero_v1',
      order: 0,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpHeroSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpHeroSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        title: 'Conseils et réponses de l\'équipe Arquantix',
        placeholderSearch: 'Rechercher un article…',
        backgroundStyle: 'purple',
      },
    },
  })

  const helpSearchSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpPage.id, key: 'help_search_v1' } },
    update: {},
    create: {
      pageId: helpPage.id,
      key: 'help_search_v1',
      order: 1,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpSearchSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpSearchSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        placeholder: 'Rechercher un article…',
        hint: 'Recherchez par mot-clé, question, sujet…',
        clearLabel: 'Effacer',
        noResultsTitle: 'Aucun résultat',
        noResultsSubtitle: 'Essayez un autre mot-clé.',
      },
    },
  })

  const helpCollectionsSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpPage.id, key: 'help_collections_grid_v1' } },
    update: {},
    create: {
      pageId: helpPage.id,
      key: 'help_collections_grid_v1',
      order: 2,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCollectionsSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCollectionsSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        sectionTitle: 'Collections',
        sectionSubtitle: 'Parcourir par thème',
        cardCtaLabel: 'Voir',
        articlesCountLabel: 'articles',
        emptyTitle: 'Aucune collection',
        emptySubtitle: 'Créez votre première collection dans l\'admin.',
      },
    },
  })

  // 2. Create /help/[collection] page template
  const helpCollectionPage = await prisma.page.upsert({
    where: { slug: 'help-collection' },
    update: {},
    create: {
      slug: 'help-collection',
      urlPath: '/help/[collection]',
      template: 'default',
      themeColor: 'light',
    },
  })

  const helpCollectionHeroSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCollectionPage.id, key: 'help_hero_v1' } },
    update: {},
    create: {
      pageId: helpCollectionPage.id,
      key: 'help_hero_v1',
      order: 0,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCollectionHeroSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCollectionHeroSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        title: 'Centre d\'aide',
        placeholderSearch: 'Rechercher un article…',
        backgroundStyle: 'purple',
        showBreadcrumbs: true,
        breadcrumbsRootLabel: 'Toutes les collections',
        breadcrumbsSeparator: '›',
      },
    },
  })

  const helpCollectionSearchSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCollectionPage.id, key: 'help_search_v1' } },
    update: {},
    create: {
      pageId: helpCollectionPage.id,
      key: 'help_search_v1',
      order: 1,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCollectionSearchSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCollectionSearchSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        placeholder: 'Rechercher un article…',
        hint: 'Recherchez par mot-clé, question, sujet…',
        clearLabel: 'Effacer',
        noResultsTitle: 'Aucun résultat',
        noResultsSubtitle: 'Essayez un autre mot-clé.',
      },
    },
  })

  const helpCollectionBreadcrumbsSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCollectionPage.id, key: 'help_breadcrumbs_v1' } },
    update: {},
    create: {
      pageId: helpCollectionPage.id,
      key: 'help_breadcrumbs_v1',
      order: 2,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCollectionBreadcrumbsSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCollectionBreadcrumbsSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        rootLabel: 'Toutes les collections',
        separator: '›',
      },
    },
  })

  const helpCollectionBodySection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCollectionPage.id, key: 'help_collection_body_v1' } },
    update: {},
    create: {
      pageId: helpCollectionPage.id,
      key: 'help_collection_body_v1',
      order: 3,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCollectionBodySection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCollectionBodySection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        emptyCategoriesTitle: 'Aucune catégorie',
        emptyCategoriesSubtitle: 'Aucune catégorie disponible dans cette collection.',
        emptyArticlesTitle: 'Aucun article',
        emptyArticlesSubtitle: 'Aucun article disponible dans cette catégorie.',
      },
    },
  })

  // 3. Create /help/[collection]/[category] page template
  const helpCategoryPage = await prisma.page.upsert({
    where: { slug: 'help-category' },
    update: {},
    create: {
      slug: 'help-category',
      urlPath: '/help/[collection]/[category]',
      template: 'default',
      themeColor: 'light',
    },
  })

  // Similar sections as collection page but with search_results instead of categories_grid
  const helpCategoryHeroSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCategoryPage.id, key: 'help_hero_v1' } },
    update: {},
    create: {
      pageId: helpCategoryPage.id,
      key: 'help_hero_v1',
      order: 0,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCategoryHeroSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCategoryHeroSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        title: 'Centre d\'aide',
        placeholderSearch: 'Rechercher un article…',
        backgroundStyle: 'purple',
        showBreadcrumbs: true,
        breadcrumbsRootLabel: 'Toutes les collections',
        breadcrumbsSeparator: '›',
      },
    },
  })

  const helpCategorySearchSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCategoryPage.id, key: 'help_search_v1' } },
    update: {},
    create: {
      pageId: helpCategoryPage.id,
      key: 'help_search_v1',
      order: 1,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCategorySearchSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCategorySearchSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        placeholder: 'Rechercher un article…',
        hint: 'Recherchez par mot-clé, question, sujet…',
        clearLabel: 'Effacer',
        noResultsTitle: 'Aucun résultat',
        noResultsSubtitle: 'Essayez un autre mot-clé.',
      },
    },
  })

  const helpCategoryBreadcrumbsSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCategoryPage.id, key: 'help_breadcrumbs_v1' } },
    update: {},
    create: {
      pageId: helpCategoryPage.id,
      key: 'help_breadcrumbs_v1',
      order: 2,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCategoryBreadcrumbsSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCategoryBreadcrumbsSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        rootLabel: 'Toutes les collections',
        separator: '›',
      },
    },
  })

  const helpCategoryResultsSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpCategoryPage.id, key: 'help_search_results_v1' } },
    update: {},
    create: {
      pageId: helpCategoryPage.id,
      key: 'help_search_results_v1',
      order: 3,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpCategoryResultsSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpCategoryResultsSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        resultsTitle: 'Résultats',
        resultsCountLabel: 'résultats',
        emptyTitle: 'Aucun article trouvé',
        emptySubtitle: 'Essayez une autre recherche.',
      },
    },
  })

  // 4. Create /help/[collection]/[category]/[article] page template
  const helpArticlePage = await prisma.page.upsert({
    where: { slug: 'help-article' },
    update: {},
    create: {
      slug: 'help-article',
      urlPath: '/help/[collection]/[category]/[article]',
      template: 'default',
      themeColor: 'light',
    },
  })

  const helpArticleBreadcrumbsSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpArticlePage.id, key: 'help_breadcrumbs_v1' } },
    update: {},
    create: {
      pageId: helpArticlePage.id,
      key: 'help_breadcrumbs_v1',
      order: 0,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpArticleBreadcrumbsSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpArticleBreadcrumbsSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        rootLabel: 'Toutes les collections',
        separator: '›',
      },
    },
  })

  const helpArticleReaderSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpArticlePage.id, key: 'help_article_reader_v1' } },
    update: {},
    create: {
      pageId: helpArticlePage.id,
      key: 'help_article_reader_v1',
      order: 1,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpArticleReaderSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpArticleReaderSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        updatedLabel: 'Mis à jour',
        byLabel: 'Par',
        readingTimeLabel: 'min de lecture',
        relatedTitle: 'Articles associés',
      },
    },
  })

  const helpArticleTocSection = await prisma.section.upsert({
    where: { pageId_key: { pageId: helpArticlePage.id, key: 'help_sidebar_toc_v1' } },
    update: {},
    create: {
      pageId: helpArticlePage.id,
      key: 'help_sidebar_toc_v1',
      order: 2,
      schemaVersion: 'v1',
    },
  })

  await prisma.sectionContent.upsert({
    where: {
      sectionId_locale_status: {
        sectionId: helpArticleTocSection.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
      },
    },
    update: {},
    create: {
      sectionId: helpArticleTocSection.id,
      locale: defaultLocale,
      status: ContentStatus.PUBLISHED,
      data: {
        tocTitle: 'Sur cette page',
      },
    },
  })

  console.log('✅ Help Center CMS pages seeded successfully!')
  console.log('   - /help (collections landing)')
  console.log('   - /help-collection (categories view)')
  console.log('   - /help-category (articles list)')
  console.log('   - /help-article (article reader)')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding Help Center CMS pages:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })

