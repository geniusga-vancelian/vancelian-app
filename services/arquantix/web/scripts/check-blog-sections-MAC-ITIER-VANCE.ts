/**
 * Script to check blog sections content by locale
 */

import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('🔍 Checking blog sections content by locale...\n')

  const blogPage = await prisma.page.findUnique({
    where: { slug: 'blog' },
    include: {
      sections: {
        orderBy: { order: 'asc' },
        include: {
          contents: {
            orderBy: [{ locale: 'asc' }, { status: 'asc' }],
          },
        },
      },
    },
  })

  if (!blogPage) {
    console.log('❌ Blog page not found')
    return
  }

  console.log(`📄 Blog page: ${blogPage.slug}\n`)

  for (const section of blogPage.sections) {
    console.log(`\n📦 Section: ${section.key} (order: ${section.order})`)
    if (section.key === 'blog_category_nav') {
      console.log(
        '  ⚠️  Ce type est déprécié et n’est plus rendu sur la liste blog publique (gabarit CMS).',
      )
    }
    console.log('─'.repeat(50))

    for (const content of section.contents) {
      const data = content.data as any
      console.log(`  Locale: ${content.locale} | Status: ${content.status}`)
      
      // Show relevant fields based on section type
      if (section.key === 'blog_hero') {
        console.log(`    eyebrow: ${data.eyebrow || '(empty)'}`)
      } else if (section.key === 'blog_category_nav') {
        console.log(`    title: ${data.title || '(empty)'}`)
        console.log(`    allLabel: ${data.allLabel || '(empty)'}`)
      } else if (section.key === 'blog_mosaic') {
        console.log(`    title: ${data.title || '(empty)'}`)
      } else if (section.key === 'blog_feed') {
        console.log(`    title: ${data.title || '(empty)'}`)
        console.log(`    loadMoreLabel: ${data.loadMoreLabel || '(empty)'}`)
      }
      console.log('')
    }
  }
}

main()
  .catch((e) => {
    console.error('Error:', e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })



