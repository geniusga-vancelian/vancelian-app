/**
 * Phase 8 — Vérification post-migration du registre Exclusive Offers.
 *
 * Usage :
 *   npx tsx scripts/verify-exclusive-offer-registry.ts
 *   npx tsx scripts/verify-exclusive-offer-registry.ts --json > report.json
 *
 * Variables : DATABASE_URL (voir .env)
 */
import { prisma } from '../src/lib/prisma'

import { verifyExclusiveOfferRegistry } from '../src/lib/registry/verifyExclusiveOfferRegistry'

const json = process.argv.includes('--json')

async function main() {
  const report = await verifyExclusiveOfferRegistry(prisma)
  if (json) {
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`)
  } else {
    console.log(`[verify-exclusive-offer-registry] status=${report.status} scanned=${report.scanned}`)
    if (report.anomalies.length === 0) {
      console.log('No anomalies.')
    } else {
      for (const a of report.anomalies) {
        const line = `[${a.severity}] ${a.code} slug=${a.slug} id=${a.packagedProductId} — ${a.message}`
        console.log(line)
      }
    }
    console.log(`generatedAt=${report.generatedAt}`)
  }
  await prisma.$disconnect()
  process.exit(report.status === 'ok' ? 0 : 1)
}

main().catch(async (e) => {
  console.error(e)
  await prisma.$disconnect()
  process.exit(1)
})
