/**
 * Script to initialize the blog page with default sections
 * Run with: npx tsx scripts/init-blog-page.ts
 */

import { PrismaClient, ContentStatus } from '@prisma/client'
import { SECTION_TYPES } from '../src/lib/sections/library'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Initializing blog page with CMS sections...')

  // Create or update blog page
  const blogPage = await prisma.page.upsert({
    where: { slug: 'blog' },
    update: {
      template: 'blog',
      themeColor: 'light',
      title: 'Blog',
      urlPath: '/blog',
    },
    create: {
      slug: 'blog',
      template: 'blog',
      themeColor: 'light',
      title: 'Blog',
      urlPath: '/blog',
    },
  })

  console.log(`✅ Blog page created/updated: ${blogPage.slug}`)

  // Define default sections in order
  const sectionKeys = ['blog_hero', 'blog_category_nav', 'blog_mosaic', 'blog_feed']

  for (let i = 0; i < sectionKeys.length; i++) {
    const sectionKey = sectionKeys[i]
    const sectionType = SECTION_TYPES.find((t) => t.key === sectionKey)

    if (!sectionType) {
      console.warn(`⚠️  Section type "${sectionKey}" not found in library, skipping...`)
      continue
    }

    // Create or update section
    const section = await prisma.section.upsert({
      where: {
        pageId_key: {
          pageId: blogPage.id,
          key: sectionKey,
        },
      },
      update: {
        order: i,
        schemaVersion: sectionType.schemaVersion,
      },
      create: {
        pageId: blogPage.id,
        key: sectionKey,
        order: i,
        schemaVersion: sectionType.schemaVersion,
      },
    })

    console.log(`  ✅ Section "${sectionKey}" created/updated`)

    // Create default content for French locale (default)
    const defaultData = sectionType.defaultData

    // DRAFT content
    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: 'fr',
          status: ContentStatus.DRAFT,
        },
      },
      update: {
        data: defaultData,
      },
      create: {
        sectionId: section.id,
        locale: 'fr',
        status: ContentStatus.DRAFT,
        data: defaultData,
      },
    })

    // PUBLISHED content
    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: 'fr',
          status: ContentStatus.PUBLISHED,
        },
      },
      update: {
        data: defaultData,
      },
      create: {
        sectionId: section.id,
        locale: 'fr',
        status: ContentStatus.PUBLISHED,
        data: defaultData,
      },
    })

    console.log(`    ✅ Content created for locale "fr" (DRAFT and PUBLISHED)`)
  }

  console.log('✅ Blog page initialization complete!')
  console.log('')
  console.log('Next steps:')
  console.log('1. Go to /admin/pages/blog to edit section content')
  console.log('2. Use "Auto-translate" to translate sections to other locales')
  console.log('3. Reorder sections if needed')
}

main()
  .catch((e) => {
    console.error('Error:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })



