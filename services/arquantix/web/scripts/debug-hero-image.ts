/**
 * Debug script to check hero section background image data
 */

import { prisma } from '../src/lib/prisma'
import { getPageSections } from '../src/lib/cms/content'
import { defaultLocale } from '../src/config/locales'

async function main() {
  console.log('=== Debug Hero Image ===\n')

  // 1. Check page and section
  const page = await prisma.page.findUnique({
    where: { slug: 'home' },
    include: {
      sections: {
        where: { key: 'hero' },
        include: {
          contents: true,
        },
      },
    },
  })

  if (!page) {
    console.error('Page "home" not found')
    return
  }

  const heroSection = page.sections.find(s => s.key === 'hero')
  if (!heroSection) {
    console.error('Hero section not found')
    return
  }

  console.log('Hero Section ID:', heroSection.id)
  console.log('Hero Section Contents:', heroSection.contents.length)
  console.log('\n--- Section Contents ---')
  for (const content of heroSection.contents) {
    console.log(`\nLocale: ${content.locale}, Status: ${content.status}`)
    const data = content.data as any
    console.log('Data keys:', Object.keys(data))
    console.log('backgroundMediaId:', data.backgroundMediaId)
    console.log('backgroundImage:', data.backgroundImage)
    console.log('backgroundMediaUrl:', data.backgroundMediaUrl)
    
    if (data.backgroundMediaId) {
      // Check if media exists
      const media = await prisma.media.findUnique({
        where: { id: data.backgroundMediaId },
      })
      if (media) {
        console.log('Media found:')
        console.log('  - ID:', media.id)
        console.log('  - Key:', media.key)
        console.log('  - URL:', media.url)
        console.log('  - Filename:', media.filename)
        console.log('  - MimeType:', media.mimeType)
      } else {
        console.log('Media NOT found for ID:', data.backgroundMediaId)
      }
    }
  }

  // 2. Check resolved sections
  console.log('\n\n=== Resolved Sections ===')
  const sections = await getPageSections('home', defaultLocale, 'published')
  const resolvedHero = sections.find(s => s.key === 'hero')
  if (resolvedHero) {
    console.log('Resolved Hero Data:')
    console.log(JSON.stringify(resolvedHero.data, null, 2))
  } else {
    console.log('Resolved hero section not found')
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())


