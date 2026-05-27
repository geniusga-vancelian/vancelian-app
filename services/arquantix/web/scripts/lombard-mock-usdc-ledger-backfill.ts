/**
 * Backfill crédit USDC mock Lombard → ledger Privy (local dev).
 * Usage: npx tsx scripts/lombard-mock-usdc-ledger-backfill.ts [personId] [walletAddress]
 */
import path from 'node:path'
import { config as loadEnv } from 'dotenv'
import { ensureLombardMockPrivyLedgerCredits } from '../src/lib/portal/lombard/lombardMockPrivyLedgerCredit'

loadEnv({ path: path.resolve(process.cwd(), '.env') })
loadEnv({ path: path.resolve(process.cwd(), '.env.local'), override: true })

const personId = process.argv[2] ?? '8b0e0044-f1ef-47a5-99d4-370598a77492'
const walletAddress = process.argv[3] ?? '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44'

async function main() {
  await ensureLombardMockPrivyLedgerCredits({ personId, walletAddress })
  console.log('Lombard mock USDC ledger backfill completed.')
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
