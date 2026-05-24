/**
 * Backfill positions Morpho USDC depuis positions on-chain.
 *
 * Usage :
 *   pnpm morpho:backfill-positions
 *   npx tsx scripts/backfill-morpho-vault-positions.ts --json
 */
import { prisma } from '../src/lib/prisma'
import { backfillMorphoVaultPositions } from '../src/lib/portal/morphoVaultBackfill'

const json = process.argv.includes('--json')

async function main() {
  const result = await backfillMorphoVaultPositions()
  if (json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)
  } else {
    console.log(
      `[morpho:backfill-positions] wallets=${result.walletsScanned} upserted=${result.positionsUpserted} cost_basis_unknown=${result.costBasisUnknown} skipped=${result.skipped} errors=${result.errors.length}`,
    )
    for (const err of result.errors.slice(0, 20)) {
      console.log(`  - person=${err.personId} vault=${err.vaultAddress}: ${err.message}`)
    }
  }
  await prisma.$disconnect()
  process.exit(result.errors.length > 0 ? 1 : 0)
}

main().catch(async (error) => {
  console.error(error)
  await prisma.$disconnect()
  process.exit(1)
})
