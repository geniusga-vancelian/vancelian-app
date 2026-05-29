/**
 * Vérifie que tous les instruments All crypto ont une sparkline 24h (24 points horaires).
 * Usage: npx tsx scripts/_verify-all-crypto-sparklines.ts
 */
import {
  mapAllCryptoList,
  mergeAllCryptoSparklines,
  PORTAL_DEFAULT_CRYPTO_SYMBOLS,
} from '../src/lib/portal/marketsFormat'
import { MARKETS_SPARKLINE_HOURLY_POINTS } from '../src/lib/portal/marketsSparkline'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

async function main() {
  const symbols = PORTAL_DEFAULT_CRYPTO_SYMBOLS.join(',')
  const [allCryptoRes, summaryRes] = await Promise.all([
    fetch(`${BACKEND_URL}/api/market-data/all-crypto`, {
      signal: AbortSignal.timeout(20_000),
    }),
    fetch(
      `${BACKEND_URL}/api/market-data/market-summary?symbols=${encodeURIComponent(symbols)}`,
      { signal: AbortSignal.timeout(20_000) },
    ),
  ])

  if (!allCryptoRes.ok) {
    throw new Error(`all-crypto upstream ${allCryptoRes.status}`)
  }
  if (!summaryRes.ok) {
    throw new Error(`market-summary upstream ${summaryRes.status}`)
  }

  const allCryptoPayload = (await allCryptoRes.json()) as { summaries?: unknown }
  const summaryPayload = (await summaryRes.json()) as { summaries?: unknown }
  const rawRows = allCryptoPayload.summaries
  if (!Array.isArray(rawRows)) {
    throw new Error('missing summaries array')
  }

  const mergedRows = mergeAllCryptoSparklines(rawRows, summaryPayload.summaries)
  const items = mapAllCryptoList(mergedRows, { currency: 'USD' })
  const issues: string[] = []

  console.log(`Instruments All crypto (après merge BFF + mapAllCryptoList): ${items.length}\n`)

  for (const asset of items) {
    const len = asset.sparkline24h.length
    const finite = asset.sparkline24h.every((value) => Number.isFinite(value))
    const ok = len === MARKETS_SPARKLINE_HOURLY_POINTS && finite
    const status = ok ? 'OK' : 'FAIL'
    console.log(
      `${status.padEnd(4)} ${asset.ticker.padEnd(8)} ${asset.symbol.padEnd(10)} points=${String(len).padStart(2)} change=${asset.changePct.toFixed(2)}%`,
    )
    if (!ok) {
      issues.push(
        `${asset.ticker} (${asset.symbol}): expected ${MARKETS_SPARKLINE_HOURLY_POINTS} finite points, got ${len}${finite ? '' : ' (non-finite values)'}`,
      )
    }
  }

  const rawMissing = mergedRows.filter((row) => {
    const r = row as { sparkline_24h?: unknown; symbol?: string }
    const spark = r.sparkline_24h
    return !Array.isArray(spark) || spark.length === 0
  })

  if (rawMissing.length > 0) {
    console.log('\nLignes sans sparkline_24h après merge:')
    for (const row of rawMissing) {
      const r = row as { symbol?: string; provider_symbol?: string }
      console.log(`  - ${r.symbol ?? '?'} (${r.provider_symbol ?? '?'})`)
    }
  }

  if (issues.length > 0) {
    console.error('\nProblèmes:')
    for (const issue of issues) console.error(`  - ${issue}`)
    process.exit(1)
  }

  console.log(`\nTous les ${items.length} instruments ont ${MARKETS_SPARKLINE_HOURLY_POINTS} points horaires.`)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
