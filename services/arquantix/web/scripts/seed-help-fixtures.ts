/**
 * Sub-script ÉPHÉMÈRE — fixtures pour valider `migrate-help-to-article.ts`.
 *
 * Crée :
 *   - 1 HelpCollection slug='fixtures-test-collection' + i18n EN/FR
 *   - 1 HelpCategory slug='fixtures-test-category' + i18n EN/FR
 *   - HelpArticle 'fixtures-article-aligned' :
 *       2 locales (en, fr), 3 blocs alignés par order/type
 *       contentMarkdown vide
 *   - HelpArticle 'fixtures-article-mismatched' :
 *       2 locales (en, fr), 3 blocs en EN, 1 bloc en FR (déséquilibré)
 *       + type mismatch sur order=0
 *       contentMarkdown non vide en FR sans aucun bloc → warning
 *   - HelpArticle 'fixtures-article-no-blocks' :
 *       1 locale en, 0 bloc, contentMarkdown non vide → warning
 *
 * Modes :
 *   --apply   Crée les fixtures.
 *   --clean   Supprime les fixtures + les Article/ArticleBlock dérivés.
 *   (défaut)  Affiche ce qui serait créé.
 */

import { PrismaClient, ArticleBlockType, ContentStatus, TranslationStatus } from '@prisma/client'

const prisma = new PrismaClient()

const COLLECTION_SLUG = 'fixtures-test-collection'
const CATEGORY_SLUG = 'fixtures-test-category'
const ARTICLE_SLUGS = [
  'fixtures-article-aligned',
  'fixtures-article-mismatched',
  'fixtures-article-no-blocks',
]

async function clean() {
  const cat = await prisma.helpCategory.findFirst({
    where: { slug: CATEGORY_SLUG, collection: { slug: COLLECTION_SLUG } },
    select: { id: true },
  })
  if (cat) {
    await prisma.article.deleteMany({ where: { helpCategoryId: cat.id } })
  }
  const col = await prisma.helpCollection.findUnique({ where: { slug: COLLECTION_SLUG }, select: { id: true } })
  if (col) {
    await prisma.helpCollection.delete({ where: { id: col.id } })
  }
  console.log('Cleanup OK : fixtures supprimées + Article HELP rattachés à la catégorie supprimés.')
}

async function apply() {
  const existing = await prisma.helpCollection.findUnique({ where: { slug: COLLECTION_SLUG } })
  if (existing) {
    console.log(`Collection ${COLLECTION_SLUG} existe déjà — clean d'abord (--clean).`)
    return
  }

  const collection = await prisma.helpCollection.create({
    data: {
      slug: COLLECTION_SLUG,
      iconKey: 'article',
      colorHex: '#0F172A',
      order: 999,
      isPublished: false,
      i18n: {
        create: [
          { locale: 'en', title: 'Fixtures Test Collection', subtitle: 'Test', description: 'Eph.' },
          { locale: 'fr', title: 'Collection de test (fixtures)', subtitle: 'Test', description: 'Éph.' },
        ],
      },
      categories: {
        create: [
          {
            slug: CATEGORY_SLUG,
            order: 0,
            isPublished: false,
            i18n: {
              create: [
                { locale: 'en', title: 'Test Category', description: 'Eph.' },
                { locale: 'fr', title: 'Catégorie de test', description: 'Éph.' },
              ],
            },
          },
        ],
      },
    },
    include: { categories: true },
  })
  const category = collection.categories[0]

  await prisma.helpArticle.create({
    data: {
      categoryId: category.id,
      slug: 'fixtures-article-aligned',
      status: ContentStatus.PUBLISHED,
      publishedAt: new Date(),
      authorName: 'Vancelian',
      allowAnchors: true,
      i18n: {
        create: [
          {
            locale: 'en',
            title: 'Aligned article (EN)',
            standfirst: 'Standfirst EN',
            metaTitle: 'Meta EN',
            metaDescription: 'Desc EN',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            title: 'Article aligné (FR)',
            standfirst: 'Chapeau FR',
            metaTitle: 'Meta FR',
            metaDescription: 'Desc FR',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
      blocks: {
        create: [
          { locale: 'en', order: 0, type: ArticleBlockType.HEADING, data: { text: 'Heading EN' } },
          { locale: 'en', order: 1, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para 1 EN' } },
          { locale: 'en', order: 2, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para 2 EN' } },
          { locale: 'fr', order: 0, type: ArticleBlockType.HEADING, data: { text: 'Titre FR' } },
          { locale: 'fr', order: 1, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para 1 FR' } },
          { locale: 'fr', order: 2, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para 2 FR' } },
        ],
      },
    },
  })

  await prisma.helpArticle.create({
    data: {
      categoryId: category.id,
      slug: 'fixtures-article-mismatched',
      status: ContentStatus.PUBLISHED,
      publishedAt: new Date(),
      authorName: null,
      allowAnchors: true,
      i18n: {
        create: [
          {
            locale: 'en',
            title: 'Mismatched article (EN)',
            standfirst: 'Standfirst EN',
            metaTitle: null,
            metaDescription: null,
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            title: 'Article désynchro (FR)',
            standfirst: null,
            contentMarkdown: '# Markdown FR non migré (pas de bloc fr)',
            metaTitle: null,
            metaDescription: null,
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
      blocks: {
        create: [
          { locale: 'en', order: 0, type: ArticleBlockType.HEADING, data: { text: 'Heading EN' } },
          { locale: 'en', order: 1, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para EN' } },
          { locale: 'en', order: 2, type: ArticleBlockType.QUOTE, data: { text: 'Quote EN' } },
          { locale: 'fr', order: 0, type: ArticleBlockType.PARAGRAPH, data: { text: 'Para FR (mismatch type)' } },
        ],
      },
    },
  })

  await prisma.helpArticle.create({
    data: {
      categoryId: category.id,
      slug: 'fixtures-article-no-blocks',
      status: ContentStatus.PUBLISHED,
      publishedAt: new Date(),
      authorName: 'Author X',
      allowAnchors: true,
      i18n: {
        create: [
          {
            locale: 'en',
            title: 'No-blocks article (EN)',
            standfirst: 'Standfirst EN',
            contentMarkdown: '# Some markdown that will warn',
            metaTitle: null,
            metaDescription: null,
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  console.log('Fixtures créées : 1 collection + 1 catégorie + 3 HelpArticle.')
}

async function main() {
  const argv = process.argv.slice(2)
  if (argv.includes('--clean')) {
    await clean()
    return
  }
  if (argv.includes('--apply')) {
    await apply()
    return
  }
  console.log(`Usage : npx tsx scripts/seed-help-fixtures.ts [--apply | --clean]`)
}

main()
  .catch((err) => {
    console.error(err)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
