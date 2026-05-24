/**
 * Job quotidien de réconciliation Morpho vault (ledger ↔ on-chain).
 *
 * Usage :
 *   pnpm morpho:reconcile
 *   npx tsx scripts/run-morpho-vault-reconciliation.ts --json
 */
import { prisma } from '../src/lib/prisma'
import { runMorphoVaultReconciliation } from '../src/lib/portal/morphoVaultReconciliation'

const json = process.argv.includes('--json')

async function main() {
  const summary = await runMorphoVaultReconciliation()
  if (json) {
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`)
  } else {
    console.log(
      `[morpho:reconcile] runId=${summary.runId} checked=${summary.itemsChecked} matched=${summary.matchedCount} mismatch=${summary.mismatchCount} missing_onchain=${summary.missingOnchainCount} missing_ledger=${summary.missingLedgerCount}`,
    )
  }
  await prisma.$disconnect()
  process.exit(summary.mismatchCount + summary.missingOnchainCount + summary.missingLedgerCount > 0 ? 1 : 0)
}

main().catch(async (error) => {
  console.error(error)
  await prisma.$disconnect()
  process.exit(1)
})
