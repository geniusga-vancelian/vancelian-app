/**
 * Migration Phase 6 : Projects (Exclusive Offers) → Vault Builder + Product Registry + lien lending.
 *
 * Usage (depuis services/arquantix/web, DATABASE_URL requis) :
 *
 *   npx tsx scripts/migrate-exclusive-offers-to-vault.ts --dry-run
 *   npx tsx scripts/migrate-exclusive-offers-to-vault.ts --project-id=<cuid>
 *   npx tsx scripts/migrate-exclusive-offers-to-vault.ts --filter=lending-linked
 *   npx tsx scripts/migrate-exclusive-offers-to-vault.ts --filter=has-i18n
 *   npx tsx scripts/migrate-exclusive-offers-to-vault.ts --filter=all
 *
 * Filtres :
 *   lending-linked (défaut) — projets ayant un lending_pool_products.project_id
 *   has-i18n — tout projet avec au moins une ligne project_i18n
 *   all — tous les projets (à utiliser avec prudence)
 *
 * Sortie : JSON sur stdout + résumé console.
 */

import { PrismaClient } from '@prisma/client'

import {
  type MigrationFilter,
  runExclusiveOfferMigration,
} from '../src/lib/migration/exclusiveOfferMigrationRunner'

const prisma = new PrismaClient()

function parseArgs(argv: string[]) {
  let dryRun = false
  let projectId: string | undefined
  let filter: MigrationFilter = 'lending-linked'

  for (const a of argv) {
    if (a === '--dry-run') dryRun = true
    else if (a.startsWith('--project-id=')) projectId = a.slice('--project-id='.length).trim() || undefined
    else if (a.startsWith('--filter=')) {
      const v = a.slice('--filter='.length).trim() as MigrationFilter
      if (v === 'lending-linked' || v === 'has-i18n' || v === 'all') filter = v
      else {
        console.error('Filtre invalide. Utiliser lending-linked | has-i18n | all')
        process.exit(1)
      }
    }
  }

  return { dryRun, projectId, filter }
}

async function main() {
  const { dryRun, projectId, filter } = parseArgs(process.argv.slice(2))

  if (dryRun) {
    console.error('[migration] Mode DRY-RUN — aucune écriture en base.\n')
  }

  const result = await runExclusiveOfferMigration(prisma, {
    dryRun,
    projectId,
    filter,
  })

  console.error(
    `[migration] Résumé : migrated=${result.summary.migrated} skipped=${result.summary.skipped} conflicts=${result.summary.conflicts} errors=${result.summary.errors}`
  )
  console.log(JSON.stringify(result, null, 2))
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
