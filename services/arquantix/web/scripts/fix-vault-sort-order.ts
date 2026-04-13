/**
 * Corrige les sortOrder des vaults : un sortOrder par page (vault), pas par content.
 * Usage: npx tsx scripts/fix-vault-sort-order.ts
 */
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const VAULT_TEMPLATE = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const LOCALE = 'fr'

async function main() {
  const pages = await prisma.page.findMany({
    where: { template: VAULT_TEMPLATE },
    include: {
      sections: {
        where: { key: VAULT_SECTION_KEY },
        include: {
          contents: {
            where: { locale: LOCALE },
          },
        },
      },
    },
  })

  const byCategory = new Map<
    string,
    Array<{ pageId: string; sectionId: string; slug: string; sortOrder: number }>
  >()

  for (const p of pages) {
    const section = p.sections[0]
    if (!section) continue
    const draftContent = section.contents.find((c) => c.status === 'DRAFT')
    const data = draftContent?.data as Record<string, unknown> | null
    const inv = (typeof data?.investmentTypeSlug === 'string' ? data.investmentTypeSlug.trim() : '') || '__none__'
    const order = typeof data?.sortOrder === 'number' ? data.sortOrder : 999
    if (!byCategory.has(inv)) byCategory.set(inv, [])
    byCategory.get(inv)!.push({
      pageId: p.id,
      sectionId: section.id,
      slug: p.slug,
      sortOrder: order,
    })
  }

  for (const [cat, items] of byCategory) {
    const sorted = [...items].sort((a, b) => {
      if (a.sortOrder !== b.sortOrder) return a.sortOrder - b.sortOrder
      return a.slug.localeCompare(b.slug)
    })
    console.log(`[${cat}] ${items.length} vaults. Assigning sortOrder 0..${sorted.length - 1}`)
    for (let i = 0; i < sorted.length; i++) {
      const item = sorted[i]
      const contents = await prisma.sectionContent.findMany({
        where: { sectionId: item.sectionId, locale: LOCALE },
      })
      for (const c of contents) {
        const data = (c.data ?? {}) as Record<string, unknown>
        await prisma.sectionContent.update({
          where: { id: c.id },
          data: { data: { ...data, sortOrder: i } },
        })
      }
    }
  }
  console.log('Done.')
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
