/**
 * Sync `defi_vault_registry` depuis PortalMorphoVaultConfig + Morpho GraphQL.
 *
 * Usage :
 *   pnpm morpho:sync-vault-registry
 *   npx tsx scripts/sync-morpho-vault-registry.ts --json
 */
import { prisma } from '../src/lib/prisma'
import { syncMorphoVaultRegistryFromConfigs } from '../src/lib/portal/morphoVaultRegistrySync'

const json = process.argv.includes('--json')

async function main() {
  const result = await syncMorphoVaultRegistryFromConfigs()
  if (json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
  } else {
    console.log(
      `[morpho:sync-vault-registry] scanned=${result.scanned} upserted=${result.upserted} skipped=${result.skipped} errors=${result.errors.length}`,
    )
    for (const err of result.errors) {
      console.log(`  - ${err.vaultAddress}: ${err.message}`)
    }
    console.log(`syncedAt=${result.syncedAt}`)
  }
  await prisma.$disconnect()
  process.exit(result.errors.length > 0 ? 1 : 0)
}

main().catch(async (error) => {
  console.error(error)
  await prisma.$disconnect()
  process.exit(1)
})
