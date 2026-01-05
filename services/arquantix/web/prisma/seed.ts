import { PrismaClient, UserRole } from '@prisma/client'
import bcrypt from 'bcryptjs'

// Use vanilla PrismaClient (no adapter/accelerate) for local development
const prisma = new PrismaClient()

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

  // Upsert user (create or update if exists)
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

  console.log(`✅ Seed OK: ${user.email} (ID: ${user.id}, Role: ${user.role})`)

  // Seed initial content: home page with sections
  console.log('🌱 Seeding initial content (home page)...')

  const homePage = await prisma.page.upsert({
    where: { slug: 'home' },
    update: {},
    create: { slug: 'home' },
  })

  const sections = [
    { key: 'hero', order: 0 },
    { key: 'features', order: 1 },
    { key: 'projects', order: 2 },
    { key: 'pricing', order: 3 },
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

    // Create default published content for French locale
    const defaultData = getDefaultSectionData(sectionDef.key)
    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: 'fr',
          status: 'PUBLISHED',
        },
      },
      update: {},
      create: {
        sectionId: section.id,
        locale: 'fr',
        status: 'PUBLISHED',
        data: defaultData,
        updatedByUserId: user.id,
      },
    })

    console.log(`  ✅ Section "${sectionDef.key}" created`)
  }

  console.log('✅ Initial content seeded successfully!')
}

function getDefaultSectionData(key: string): any {
  switch (key) {
    case 'hero':
      return {
        title: 'Bienvenue sur Arquantix',
        subtitle: 'Fractional Real Estate, Institutional Rigor.',
        ctaText: 'En savoir plus',
        ctaLink: '#',
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
    case 'projects':
      return {
        title: 'Nos Projets',
        items: [],
      }
    case 'pricing':
      return {
        title: 'Tarifs',
        plans: [],
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
