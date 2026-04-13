/**
 * Seed idempotent : layouts Flutter DS + widget builder (dashboard, offers, vaults, bundles).
 * Usage : depuis web/ → npx tsx prisma/seed_dashboard_builder.ts
 */
import { PrismaClient } from '@prisma/client'

import { seedDsComponents } from './seed-ds-components'
import { seedWidgetBuilderCore } from './seed-widget-builder-core'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 seed_dashboard_builder: DS Flutter + widget builder…')
  await seedDsComponents(prisma)
  await seedWidgetBuilderCore(prisma)
  console.log('✅ seed_dashboard_builder terminé')
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
