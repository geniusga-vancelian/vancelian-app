/**
 * Script de debug pour inspecter les données des vaults (reorder)
 * Usage: npx tsx scripts/debug-vault-reorder.ts
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

  console.log('=== Pages vault_builder ===')
  console.log('Count:', pages.length)

  for (const p of pages) {
    console.log('\n--- Page:', p.slug, '---')
    console.log('  Sections count:', p.sections.length)
    for (const s of p.sections) {
      console.log('  Section key:', s.key, 'contents:', s.contents.length)
      for (const c of s.contents) {
        const data = c.data as Record<string, unknown> | null
        const inv = data?.investmentTypeSlug
        const order = data?.sortOrder
        console.log('    Content:', c.locale, c.status, '| investmentTypeSlug:', inv, '| sortOrder:', order)
        if (data && Object.keys(data).length < 20) {
          console.log('    Data keys:', Object.keys(data))
        }
      }
    }
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect())
