/**
 * Corrige la visibilité publique de la homepage Vancelian :
 * - defaultLocale → fr (contenu seedé en FR)
 * - multilingual → true (/fr accessible sans redirect)
 * - copie SectionContent PUBLISHED fr → en pour toutes les sections home
 *
 * Usage : npx tsx scripts/fix-homepage-cms-visibility.ts
 */

import { PrismaClient, ContentStatus, Prisma } from '@prisma/client'

const prisma = new PrismaClient()
const PAGE_SLUG = 'home'

async function main() {
  const settings = await prisma.appSettings.findFirst()
  if (settings) {
    await prisma.appSettings.update({
      where: { id: settings.id },
      data: {
        defaultLocale: 'fr',
        multilingualEnabled: true,
      },
    })
    console.log('AppSettings → defaultLocale=fr, multilingualEnabled=true')
  } else {
    await prisma.appSettings.create({
      data: {
        defaultLocale: 'fr',
        multilingualEnabled: true,
      },
    })
    console.log('AppSettings créés (fr, multilingue)')
  }

  const page = await prisma.page.findUnique({
    where: { slug: PAGE_SLUG },
    include: {
      sections: {
        orderBy: { order: 'asc' },
        include: { contents: true },
      },
    },
  })

  if (!page) {
    throw new Error(`Page "${PAGE_SLUG}" introuvable — lancez seed-cms-home-vancelian.ts`)
  }

  let copied = 0
  for (const section of page.sections) {
    const frPublished = section.contents.find(
      (c) => c.locale === 'fr' && c.status === ContentStatus.PUBLISHED,
    )
    if (!frPublished?.data) {
      console.warn(`  skip ${section.key} — pas de PUBLISHED fr`)
      continue
    }

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: 'en',
          status: ContentStatus.PUBLISHED,
        },
      },
      update: { data: frPublished.data as Prisma.InputJsonValue },
      create: {
        sectionId: section.id,
        locale: 'en',
        status: ContentStatus.PUBLISHED,
        data: frPublished.data as Prisma.InputJsonValue,
      },
    })
    copied++
    console.log(`  copied fr→en PUBLISHED: ${section.key}`)
  }

  console.log(`Done. ${copied} sections synchronisées. Visitez http://localhost:3100/fr`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
