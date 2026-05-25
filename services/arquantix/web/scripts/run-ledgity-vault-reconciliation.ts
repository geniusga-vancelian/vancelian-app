/**
 * Job quotidien de réconciliation Ledgity vault (ledger ↔ lyToken on-chain).
 *
 * Usage :
 *   pnpm ledgity:reconcile
 *   npx tsx scripts/run-ledgity-vault-reconciliation.ts --json
 *
 * Fréquence recommandée : quotidien 06:15 UTC, après chaque batch de tests live.
 */
import { prisma } from '../src/lib/prisma'
import { runLedgityVaultReconciliation } from '../src/lib/portal/ledgity/ledgityVaultReconciliation'

const json = process.argv.includes('--json')

async function main() {
  const summary = await runLedgityVaultReconciliation()
  if (json) {
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`)
  } else {
    console.log(
      `[ledgity:reconcile] runId=${summary.runId} checked=${summary.itemsChecked} matched=${summary.matchedCount} mismatch=${summary.mismatchCount} missing_onchain=${summary.missingOnchainCount} missing_ledger=${summary.missingLedgerCount} pps_unavailable=${summary.ppsUnavailableCount} liquidity_warning=${summary.liquidityWarningCount}`,
    )
  }
  await prisma.$disconnect()
  const exitCode =
    summary.mismatchCount +
      summary.missingOnchainCount +
      summary.missingLedgerCount +
      summary.ppsUnavailableCount +
      summary.liquidityWarningCount >
    0
      ? 1
      : 0
  process.exit(exitCode)
}

main().catch(async (error) => {
  console.error(error)
  await prisma.$disconnect()
  process.exit(1)
})
