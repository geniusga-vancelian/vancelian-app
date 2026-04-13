import { PrismaClient, ContentStatus, TranslationStatus } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding Help Center...')

  // Create collection
  const collection = await prisma.helpCollection.upsert({
    where: { slug: 'getting-started' },
    update: {},
    create: {
      slug: 'getting-started',
      order: 0,
      isPublished: true,
      i18n: {
        create: [
          {
            locale: 'fr',
            title: 'Pour commencer',
            subtitle: 'Découvrez Arquantix',
            description: 'Tout ce dont vous avez besoin pour démarrer avec Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            title: 'Getting Started',
            subtitle: 'Discover Arquantix',
            description: 'Everything you need to get started with Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            title: 'Per iniziare',
            subtitle: 'Scopri Arquantix',
            description: 'Tutto ciò di cui hai bisogno per iniziare con Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  console.log('✅ Created collection:', collection.slug)

  // Create categories
  const category1 = await prisma.helpCategory.upsert({
    where: {
      collectionId_slug: {
        collectionId: collection.id,
        slug: 'account-setup',
      },
    },
    update: {},
    create: {
      collectionId: collection.id,
      slug: 'account-setup',
      order: 0,
      isPublished: true,
      i18n: {
        create: [
          {
            locale: 'fr',
            title: 'Configuration du compte',
            description: 'Comment créer et configurer votre compte Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            title: 'Account Setup',
            description: 'How to create and configure your Arquantix account',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            title: 'Configurazione account',
            description: 'Come creare e configurare il tuo account Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  const category2 = await prisma.helpCategory.upsert({
    where: {
      collectionId_slug: {
        collectionId: collection.id,
        slug: 'investing-basics',
      },
    },
    update: {},
    create: {
      collectionId: collection.id,
      slug: 'investing-basics',
      order: 1,
      isPublished: true,
      i18n: {
        create: [
          {
            locale: 'fr',
            title: 'Bases de l\'investissement',
            description: 'Apprenez les fondamentaux de l\'investissement',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            title: 'Investing Basics',
            description: 'Learn the fundamentals of investing',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            title: 'Basi dell\'investimento',
            description: 'Impara i fondamenti dell\'investimento',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  console.log('✅ Created categories:', category1.slug, category2.slug)

  // Create articles
  const article1 = await prisma.helpArticle.upsert({
    where: {
      categoryId_slug: {
        categoryId: category1.id,
        slug: 'create-account',
      },
    },
    update: {},
    create: {
      categoryId: category1.id,
      slug: 'create-account',
      status: ContentStatus.PUBLISHED,
      publishedAt: new Date(),
      allowAnchors: true,
      i18n: {
        create: [
          {
            locale: 'fr',
            title: 'Comment créer un compte',
            standfirst: 'Suivez ces étapes simples pour créer votre compte Arquantix et commencer à investir.',
            metaTitle: 'Créer un compte Arquantix',
            metaDescription: 'Guide étape par étape pour créer votre compte Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            title: 'How to create an account',
            standfirst: 'Follow these simple steps to create your Arquantix account and start investing.',
            metaTitle: 'Create Arquantix account',
            metaDescription: 'Step-by-step guide to create your Arquantix account',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            title: 'Come creare un account',
            standfirst: 'Segui questi semplici passaggi per creare il tuo account Arquantix e iniziare a investire.',
            metaTitle: 'Crea account Arquantix',
            metaDescription: 'Guida passo-passo per creare il tuo account Arquantix',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
      blocks: {
        create: [
          {
            locale: 'fr',
            type: 'HEADING',
            order: 0,
            data: { text: 'Étape 1 : Inscription' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            type: 'PARAGRAPH',
            order: 1,
            data: { text: 'Rendez-vous sur la page d\'inscription et remplissez le formulaire avec vos informations personnelles.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            type: 'HEADING',
            order: 2,
            data: { text: 'Étape 2 : Vérification' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            type: 'PARAGRAPH',
            order: 3,
            data: { text: 'Vérifiez votre adresse email en cliquant sur le lien reçu dans votre boîte mail.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'HEADING',
            order: 0,
            data: { text: 'Step 1: Registration' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'PARAGRAPH',
            order: 1,
            data: { text: 'Go to the registration page and fill out the form with your personal information.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'HEADING',
            order: 2,
            data: { text: 'Step 2: Verification' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'PARAGRAPH',
            order: 3,
            data: { text: 'Verify your email address by clicking the link received in your mailbox.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'HEADING',
            order: 0,
            data: { text: 'Passaggio 1: Registrazione' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'PARAGRAPH',
            order: 1,
            data: { text: 'Vai alla pagina di registrazione e compila il modulo con le tue informazioni personali.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'HEADING',
            order: 2,
            data: { text: 'Passaggio 2: Verifica' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'PARAGRAPH',
            order: 3,
            data: { text: 'Verifica il tuo indirizzo email cliccando sul link ricevuto nella tua casella di posta.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  const article2 = await prisma.helpArticle.upsert({
    where: {
      categoryId_slug: {
        categoryId: category2.id,
        slug: 'what-is-investing',
      },
    },
    update: {},
    create: {
      categoryId: category2.id,
      slug: 'what-is-investing',
      status: ContentStatus.PUBLISHED,
      publishedAt: new Date(),
      allowAnchors: true,
      i18n: {
        create: [
          {
            locale: 'fr',
            title: 'Qu\'est-ce que l\'investissement ?',
            standfirst: 'Découvrez les bases de l\'investissement et comment commencer.',
            metaTitle: 'Qu\'est-ce que l\'investissement ?',
            metaDescription: 'Guide complet sur les bases de l\'investissement',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            title: 'What is investing?',
            standfirst: 'Discover the basics of investing and how to get started.',
            metaTitle: 'What is investing?',
            metaDescription: 'Complete guide on investing basics',
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            title: 'Cos\'è l\'investimento?',
            standfirst: 'Scopri le basi dell\'investimento e come iniziare.',
            metaTitle: 'Cos\'è l\'investimento?',
            metaDescription: 'Guida completa sulle basi dell\'investimento',
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
      blocks: {
        create: [
          {
            locale: 'fr',
            type: 'PARAGRAPH',
            order: 0,
            data: { text: 'L\'investissement consiste à placer de l\'argent dans des actifs financiers dans l\'espoir de générer des rendements au fil du temps.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            type: 'HEADING',
            order: 1,
            data: { text: 'Types d\'investissements' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'fr',
            type: 'BULLET_LIST',
            order: 2,
            data: { items: ['Actions', 'Obligations', 'Fonds communs de placement', 'Cryptomonnaies'] },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'PARAGRAPH',
            order: 0,
            data: { text: 'Investing involves putting money into financial assets with the hope of generating returns over time.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'HEADING',
            order: 1,
            data: { text: 'Types of investments' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'en',
            type: 'BULLET_LIST',
            order: 2,
            data: { items: ['Stocks', 'Bonds', 'Mutual funds', 'Cryptocurrencies'] },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'PARAGRAPH',
            order: 0,
            data: { text: 'Investire significa mettere denaro in attività finanziarie con la speranza di generare rendimenti nel tempo.' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'HEADING',
            order: 1,
            data: { text: 'Tipi di investimenti' },
            translationStatus: TranslationStatus.ORIGINAL,
          },
          {
            locale: 'it',
            type: 'BULLET_LIST',
            order: 2,
            data: { items: ['Azioni', 'Obbligazioni', 'Fondi comuni', 'Criptovalute'] },
            translationStatus: TranslationStatus.ORIGINAL,
          },
        ],
      },
    },
  })

  console.log('✅ Created articles:', article1.slug, article2.slug)
  console.log('🎉 Help Center seeded successfully!')
}

main()
  .catch((e) => {
    console.error('❌ Error seeding Help Center:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })


