/**
 * Liste les lignes portal_morpho_vault_configs (debug / sync).
 * Usage: npx tsx scripts/list-morpho-vault-configs.ts [--json]
 */
import { PrismaClient } from '@prisma/client'

const json = process.argv.includes('--json')
const prisma = new PrismaClient()

async function main() {
  const rows = await prisma.portalMorphoVaultConfig.findMany({
    orderBy: [{ sortOrder: 'asc' }, { createdAt: 'asc' }],
  })
  if (json) {
    process.stdout.write(`${JSON.stringify(rows, null, 2)}\n`)
  } else {
    console.log(`count=${rows.length}`)
    for (const r of rows) {
      console.log(
        `- ${r.label ?? r.vaultAddress} | ${r.integrationMode} | published=${r.isPublished} | ${r.vaultAddress}`,
      )
    }
  }
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
