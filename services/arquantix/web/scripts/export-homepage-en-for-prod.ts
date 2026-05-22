/**
 * Exporte homepage EN (PUBLISHED) + médias vancelian-home pour sync prod.
 *
 * Usage :
 *   cd services/arquantix/web
 *   npx tsx scripts/export-homepage-en-for-prod.ts
 */
import fs from 'node:fs'
import path from 'node:path'
import { PrismaClient, ContentStatus } from '@prisma/client'

const prisma = new PrismaClient()
const PAGE_SLUG = 'home'
const LOCALE = 'en'
const OUT_DIR =
  process.env.HOMEPAGE_SYNC_OUT_DIR ||
  path.join(process.env.HOME || '/tmp', 'backups', `homepage_en_sync_${Date.now()}`)

async function main() {
  const page = await prisma.page.findUnique({ where: { slug: PAGE_SLUG } })
  if (!page) throw new Error(`Page ${PAGE_SLUG} introuvable`)

  const sections = await prisma.section.findMany({
    where: { pageId: page.id },
    orderBy: { order: 'asc' },
    include: {
      contents: {
        where: { locale: LOCALE, status: ContentStatus.PUBLISHED },
      },
    },
  })

  const sectionPayload = sections
    .filter((s) => s.contents.length > 0)
    .map((s) => ({
      key: s.key,
      data: s.contents[0].data,
    }))

  const pageI18n = await prisma.pageI18n.findUnique({
    where: { pageId_locale: { pageId: page.id, locale: LOCALE } },
  })

  const media = await prisma.media.findMany({
    where: { key: { startsWith: 'cms/vancelian-home/' } },
  })

  fs.mkdirSync(OUT_DIR, { recursive: true })
  const payload = {
    pageSlug: PAGE_SLUG,
    locale: LOCALE,
    pageI18n: pageI18n
      ? { title: pageI18n.title, description: pageI18n.description, ogTitle: pageI18n.ogTitle, ogDescription: pageI18n.ogDescription }
      : null,
    sections: sectionPayload,
    media: media.map((m) => ({
      id: m.id,
      key: m.key,
      url: m.url,
      filename: m.filename,
      mimeType: m.mimeType,
      size: m.size,
      width: m.width,
      height: m.height,
      alt: m.alt,
    })),
  }

  const jsonPath = path.join(OUT_DIR, 'homepage-en-sync.json')
  fs.writeFileSync(jsonPath, JSON.stringify(payload, null, 2))
  console.log(`Export : ${jsonPath}`)
  console.log(`  sections EN PUBLISHED : ${sectionPayload.length}`)
  console.log(`  médias vancelian-home : ${media.length}`)
  console.log(`OUT_DIR=${OUT_DIR}`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(() => prisma.$disconnect())
