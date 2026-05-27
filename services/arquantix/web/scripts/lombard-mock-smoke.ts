/**
 * Smoke Lombard mock mode (no HTTP, no Morpho GraphQL).
 *
 * Usage:
 *   pnpm lombard:mock
 */
import { getLombardMockMarketSummaries } from '../src/lib/portal/lombard/mocks/lombardLocalMock'
import { buildLombardMockQuote } from '../src/lib/portal/lombard/mocks/lombardLocalMock'
import { isLombardMockEnabled } from '../src/lib/portal/lombard/lombardMockConfig'

async function main() {
  if (!isLombardMockEnabled()) {
    console.error('[lombard:mock] LOMBARD_V1_MOCK_ENABLED is not active (dev only)')
    process.exit(1)
  }

  const markets = getLombardMockMarketSummaries()
  console.log(`[lombard:mock] markets=${markets.length}`)

  const quote = await buildLombardMockQuote({
    collateral: 'cbBTC',
    borrowAmount: '75',
    walletAddress: '0x1111111111111111111111111111111111111111',
  })

  console.log(
    `[lombard:mock] quote borrow=${quote.borrowAmount} guarantee=${quote.guaranteeAmount} ltv=${quote.projectedLtvPercent}%`,
  )
  console.log('[lombard:mock] OK — enable in .env.local:')
  console.log('  LOMBARD_V1_MOCK_ENABLED=true')
  console.log('  LOMBARD_V1_MOCK_POSITION_ENABLED=true')
  console.log('  LOMBARD_V1_BETA_ENABLED=false   # optional for unrestricted local QA')
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
