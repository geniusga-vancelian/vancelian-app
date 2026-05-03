import { Prisma, PrismaClient, UserRole, ContentStatus, ArticleBlockType } from '@prisma/client'
import bcrypt from 'bcryptjs'

import { seedDsComponents } from './seed-ds-components'
import { seedWidgetBuilderCore } from './seed-widget-builder-core'
import { seedVancelianCompanyNews } from './seed-vancelian-company-news'
import { config as loadEnv } from 'dotenv'
import path from 'path'

// Même résolution que Next : `.env.local` surcharge `.env` (ADMIN_SEED_*, BFF_ANONYMOUS_BACKEND_ADMIN_ID).
loadEnv({ path: path.resolve(process.cwd(), '.env') })
loadEnv({ path: path.resolve(process.cwd(), '.env.local'), override: true })

// Use vanilla PrismaClient (no adapter/accelerate) for local development
const prisma = new PrismaClient()

async function publicTableExists(tableName: 'users' | 'pages'): Promise<boolean> {
  const rows = await prisma.$queryRaw<Array<{ exists: boolean }>>`
    SELECT EXISTS (
      SELECT 1
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name = ${tableName}
    ) AS "exists"
  `
  return Boolean(rows[0]?.exists)
}

async function main() {
  const adminEmail = process.env.ADMIN_SEED_EMAIL
  const adminPassword = process.env.ADMIN_SEED_PASSWORD

  if (!adminEmail || !adminPassword) {
    throw new Error(
      'ADMIN_SEED_EMAIL and ADMIN_SEED_PASSWORD must be set in environment variables'
    )
  }

  console.log('🌱 Seeding admin user...')

  // Hash password
  const passwordHash = await bcrypt.hash(adminPassword, 10)

  const hasUsersTable = await publicTableExists('users')
  let cmsUserId: string | undefined

  if (hasUsersTable) {
    const user = await prisma.user.upsert({
      where: { email: adminEmail },
      update: {
        passwordHash,
        role: UserRole.SUPER_ADMIN,
      },
      create: {
        email: adminEmail,
        passwordHash,
        role: UserRole.SUPER_ADMIN,
      },
    })
    cmsUserId = user.id
    console.log(`✅ Seed OK: ${user.email} (ID: ${user.id}, Role: ${user.role})`)
  } else {
    console.log(
      'ℹ️  Table public.users absente — upsert admin_users uniquement (pas de lien users.admin_user_id).'
    )
  }

  const bffIdRaw = process.env.BFF_ANONYMOUS_BACKEND_ADMIN_ID
  const bffAdminId =
    bffIdRaw !== undefined && String(bffIdRaw).trim() !== ''
      ? Number.parseInt(String(bffIdRaw).trim(), 10)
      : NaN
  const useBffId = Number.isFinite(bffAdminId) && bffAdminId > 0

  let adminApi
  if (useBffId) {
    adminApi = await prisma.adminUser.upsert({
      where: { id: bffAdminId },
      update: {
        email: adminEmail,
        hashedPassword: passwordHash,
        updatedAt: new Date(),
      },
      create: {
        id: bffAdminId,
        email: adminEmail,
        hashedPassword: passwordHash,
      },
    })
    await prisma.$executeRaw`
      SELECT setval(
        pg_get_serial_sequence('admin_users', 'id'),
        COALESCE((SELECT MAX(id) FROM admin_users), 1)
      )
    `
    console.log(
      `✅ admin_users aligné sur BFF_ANONYMOUS_BACKEND_ADMIN_ID=${bffAdminId} (BFF JWT)`
    )
  } else {
    adminApi = await prisma.adminUser.findFirst({
      where: { email: { equals: adminEmail, mode: 'insensitive' } },
      orderBy: { id: 'asc' },
    })
    if (!adminApi) {
      adminApi = await prisma.adminUser.create({
        data: {
          email: adminEmail,
          hashedPassword: passwordHash,
        },
      })
      console.log(`✅ admin_users créé pour le BFF JWT (id=${adminApi.id})`)
      console.log(
        `👉 Mettre BFF_ANONYMOUS_BACKEND_ADMIN_ID=${adminApi.id} dans services/arquantix/web/.env.local (requis par le BFF)`
      )
    }
  }
  if (hasUsersTable && cmsUserId) {
    await prisma.user.update({
      where: { id: cmsUserId },
      data: { adminUserId: adminApi.id },
    })
    console.log(`✅ users.admin_user_id → admin_users.id = ${adminApi.id}`)
  }

  const hasPagesTable = await publicTableExists('pages')
  if (!hasPagesTable) {
    console.log(
      'ℹ️  Table public.pages absente — fin du seed après admin_users (pas de seed contenu CMS Prisma).'
    )
    return
  }

  // Seed initial content: home page with sections
  console.log('🌱 Seeding initial content (home page)...')

  const homePage = await prisma.page.upsert({
    where: { slug: 'home' },
    update: {},
    create: {
      slug: 'home',
      urlPath: '/',
      template: 'homepage',
      title: 'Home',
    },
  })

  // Metadata EN pilote (Phase 2A — table `page_i18n`)
  await prisma.pageI18n.upsert({
    where: {
      pageId_locale: { pageId: homePage.id, locale: 'en' },
    },
    update: {
      title: 'Home (EN)',
      description: 'Arquantix — EN metadata seed (Phase 2A)',
    },
    create: {
      pageId: homePage.id,
      locale: 'en',
      title: 'Home (EN)',
      description: 'Arquantix — EN metadata seed (Phase 2A)',
    },
  })

  const sections = [
    { key: 'hero', order: 0 },
    { key: 'features', order: 1 },
    { key: 'projects', order: 2 },
    { key: 'cta', order: 3 },
    { key: 'footer', order: 4 },
  ]

  for (const sectionDef of sections) {
    const section = await prisma.section.upsert({
      where: {
        pageId_key: {
          pageId: homePage.id,
          key: sectionDef.key,
        },
      },
      update: {},
      create: {
        pageId: homePage.id,
        key: sectionDef.key,
        order: sectionDef.order,
        schemaVersion: 'v1',
      },
    })

    // Create default DRAFT and PUBLISHED content for French locale
    const defaultData = getDefaultSectionData(sectionDef.key)
    const defaultLocale = 'fr'

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: defaultLocale,
          status: ContentStatus.DRAFT,
        },
      },
      update: {},
      create: {
        sectionId: section.id,
        locale: defaultLocale,
        status: ContentStatus.DRAFT,
        data: defaultData,
        ...(cmsUserId !== undefined ? { updatedByUserId: cmsUserId } : {}),
      },
    })

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: defaultLocale,
          status: ContentStatus.PUBLISHED,
        },
      },
      update: {},
      create: {
        sectionId: section.id,
        locale: defaultLocale,
        status: ContentStatus.PUBLISHED,
        data: defaultData,
        ...(cmsUserId !== undefined ? { updatedByUserId: cmsUserId } : {}),
      },
    })

    console.log(`  ✅ Section "${sectionDef.key}" created with DRAFT and PUBLISHED content`)
  }

  console.log('✅ Initial content seeded successfully!')

  // Seed primary menu
  console.log('🌱 Seeding primary menu...')

  const primaryMenu = await prisma.menu.upsert({
    where: { key: 'primary' },
    update: {},
    create: {
      key: 'primary',
      name: 'Primary Menu',
    },
  })

  // Check if Home item already exists
  const existingHomeItem = await prisma.menuItem.findFirst({
    where: {
      menuId: primaryMenu.id,
      isRoot: true,
    },
  })

  if (!existingHomeItem) {
    await prisma.menuItem.create({
      data: {
        menuId: primaryMenu.id,
        label: 'Home',
        isRoot: true,
        pageId: null,
        order: 0,
        enabled: true,
      },
    })
    console.log('  ✅ Home menu item created')
  } else {
    console.log('  ℹ️  Home menu item already exists')
  }

  console.log('✅ Primary menu seeded successfully!')

  // Seed catégories d'investissement (offres)
  console.log('🌱 Seeding investment categories...')
  const investmentCategories = [
    { slug: 'real-estate', label: 'Real estate', sortOrder: 0 },
    { slug: 'energy', label: 'Energy', sortOrder: 1 },
    { slug: 'commodity', label: 'Commodity', sortOrder: 2 },
    { slug: 'art', label: 'Art', sortOrder: 3 },
    { slug: 'infrastructure', label: 'Infrastructure', sortOrder: 4 },
    { slug: 'private-equity', label: 'Private equity', sortOrder: 5 },
    { slug: 'crypto', label: 'Crypto', sortOrder: 6 },
  ]
  for (const cat of investmentCategories) {
    await prisma.investmentCategory.upsert({
      where: { slug: cat.slug },
      update: { label: cat.label, sortOrder: cat.sortOrder },
      create: { slug: cat.slug, label: cat.label, sortOrder: cat.sortOrder },
    })
  }
  console.log(`  ✅ ${investmentCategories.length} investment categories seeded`)
  console.log('✅ Investment categories seeded successfully!')

  // Seed investment types
  console.log('🌱 Seeding investment types...')
  const investmentTypes = [
    {
      slug: 'crypto-assets',
      label: 'Crypto Assets',
      sortOrder: 0,
      colorHex: '#F59E0B',
      iconKey: 'trending-up',
    },
    {
      slug: 'crypto-bundles',
      label: 'Crypto Bundles',
      sortOrder: 1,
      colorHex: '#6366F1',
      iconKey: 'boxes',
    },
    {
      slug: 'saving-vaults',
      label: 'Saving Vaults',
      sortOrder: 2,
      colorHex: '#10B981',
      iconKey: 'shield',
    },
    {
      slug: 'exclusive-offers',
      label: 'Exclusive offers',
      sortOrder: 3,
      colorHex: '#EC4899',
      iconKey: 'tag',
    },
    {
      slug: 'mandates',
      label: 'Mandates',
      sortOrder: 4,
      colorHex: '#0EA5E9',
      iconKey: 'file-text',
    },
  ]
  for (const type of investmentTypes) {
    await prisma.investmentTypes.upsert({
      where: { slug: type.slug },
      update: {
        label: type.label,
        sortOrder: type.sortOrder,
        colorHex: type.colorHex,
        iconKey: type.iconKey,
      },
      create: {
        slug: type.slug,
        label: type.label,
        sortOrder: type.sortOrder,
        colorHex: type.colorHex,
        iconKey: type.iconKey,
      },
    })
  }
  console.log(`  ✅ ${investmentTypes.length} investment types seeded`)
  console.log('✅ Investment types seeded successfully!')

  // Sample article for GET /api/blog + Flutter (idempotent)
  const blogSlug = 'arquantix-bienvenue'
  const existingBlog = await prisma.article.findUnique({ where: { slug: blogSlug } })
  if (!existingBlog) {
    console.log('🌱 Seeding sample published blog article...')
    await prisma.article.create({
      data: {
        slug: blogSlug,
        status: ContentStatus.PUBLISHED,
        publishedAt: new Date(),
        authorName: 'Arquantix',
        authorRole: null,
        articleType: 'NEWS',
        isFeatured: true,
        isHighlighted: false,
        categorySlugs: ['crypto'],
        blocks: {
          create: [
            {
              order: 0,
              type: ArticleBlockType.PARAGRAPH,
              data: { text: 'Bienvenue sur Arquantix.' },
              i18n: {
                create: {
                  locale: 'fr',
                  data: { text: 'Bienvenue sur Arquantix.' },
                },
              },
            },
          ],
        },
        i18n: {
          create: {
            locale: 'fr',
            title: 'Bienvenue',
            standfirst: 'Actualités et analyses Arquantix.',
          },
        },
      },
    })
    console.log(`  ✅ Blog article "${blogSlug}" created (fr i18n + 1 block)`)
  } else {
    console.log(`  ℹ️  Blog article "${blogSlug}" already exists`)
  }

  // Page CMS dédiée aux tests E2E Playwright (multilingue) — voir services/arquantix/web/e2e/
  console.log('🌱 Seeding E2E smoke CMS page (e2e-smoke)...')
  const e2eSmokePage = await prisma.page.upsert({
    where: { slug: 'e2e-smoke' },
    update: {},
    create: {
      slug: 'e2e-smoke',
      urlPath: '/e2e-smoke',
      template: 'default',
      title: 'E2E smoke',
      description: 'Seed pour tests Playwright (multilingue)',
    },
  })
  const e2eSection = await prisma.section.upsert({
    where: {
      pageId_key: {
        pageId: e2eSmokePage.id,
        key: 'hero',
      },
    },
    update: {},
    create: {
      pageId: e2eSmokePage.id,
      key: 'hero',
      order: 0,
      schemaVersion: 'v1',
    },
  })
  const e2eHeroData = getDefaultSectionData('hero')
  for (const st of [ContentStatus.DRAFT, ContentStatus.PUBLISHED] as const) {
    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: e2eSection.id,
          locale: 'fr',
          status: st,
        },
      },
      update: {},
      create: {
        sectionId: e2eSection.id,
        locale: 'fr',
        status: st,
        data: e2eHeroData,
        ...(cmsUserId !== undefined ? { updatedByUserId: cmsUserId } : {}),
      },
    })
  }
  console.log('  ✅ e2e-smoke page OK')

  // Footer global FR/EN distincts pour les E2E Playwright (voir e2e/multilingual.spec.ts).
  // Écrase `global_settings.footer_json` à chaque seed : rééditer depuis l’admin si besoin hors E2E.
  console.log('🌱 Seeding E2E footer markers (global_settings.footer_json v2)...')
  const e2eFooterJson: Prisma.InputJsonValue = {
    version: 2,
    defaultLocale: 'fr',
    locales: {
      fr: { copyright: '© E2E-FOOTER-FR' },
      en: { copyright: '© E2E-FOOTER-EN' },
    },
  }
  const gsRow = await prisma.globalSettings.findFirst()
  if (gsRow) {
    await prisma.globalSettings.update({
      where: { id: gsRow.id },
      data: { footerJson: e2eFooterJson },
    })
  } else {
    await prisma.globalSettings.create({
      data: { footerJson: e2eFooterJson },
    })
  }
  console.log('  ✅ E2E footer markers OK')

  console.log('🌱 Seeding Flutter DS + widget builder (dashboard, offers, vaults, bundles)…')
  await seedDsComponents(prisma)
  await seedWidgetBuilderCore(prisma)
  console.log('✅ DS / widget builder seed OK')

  console.log('🌱 Seeding Vancelian company news (articles + tags)…')
  await seedVancelianCompanyNews(prisma)
  console.log('✅ Vancelian company news OK')
}

function getDefaultSectionData(key: string): any {
  switch (key) {
    case 'hero':
      return {
        title: 'Premium Real Estate Yield,\nDelivered On-Chain.',
        subtitle:
          'Earn reliable yield backed by premium real estate operations. Built with institutional-grade transparency and real asset backing.',
        ctaText: 'Explore projects',
        ctaLink: '#projects',
        backgroundImageOpacity: 1,
      }
    case 'hero_secondary':
      return {
        title: 'Page title,\nSecond line',
        subtitle: '',
        ctaText: 'Explore projects',
        ctaLink: '#contact',
        backgroundImageOpacity: 1,
        hideCta: false,
      }
    case 'features':
      return {
        title: 'Nos Services',
        items: [
          { title: 'Service 1', description: 'Description du service 1' },
          { title: 'Service 2', description: 'Description du service 2' },
          { title: 'Service 3', description: 'Description du service 3' },
        ],
      }
    case 'how_it_works':
      return {
        label: 'HOW IT WORKS',
        title: '',
        subtitle: '',
        surface: 'light',
        steps: [
          {
            number: '01',
            title: 'Access the platform',
            description:
              "Create an account or connect a wallet. A simple, secure onboarding. In a few guided steps, you're in.",
          },
          {
            number: '02',
            title: 'Explore the Projects',
            description:
              'Browse curated real estate projects with full documentation: location, expected return, maturity, risk profile. Everything you need to decide with confidence.',
          },
          {
            number: '03',
            title: 'Deposit and Start Earning',
            description:
              'Choose a project, deposit in one click, and start earning immediately. Your returns are backed by real assets.',
          },
        ],
        primaryCtaText: 'START EARNING',
        primaryCtaHref: '#projects',
      }
    case 'projects':
      return {
        title: 'Nos Projets',
        items: [],
      }
    case 'cta':
      return {
        title: 'Prêt à investir ?',
        description: '',
        primaryButtonText: 'Nous contacter',
        primaryButtonHref: '#contact',
      }
    case 'footer':
      return {
        copyright: '© 2026 Arquantix. Tous droits réservés.',
        links: [],
      }
    default:
      return {}
  }
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
