import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { mapAllCryptoList, mergeAllCryptoSparklines } from '@/lib/portal/marketsFormat'

describe('mapAllCryptoList', () => {
  it('merges sparkline_24h from market-summary when all-crypto rows omit it', () => {
    const bars5m = Array.from({ length: 288 }, (_, index) => 2000 + index * 0.5)
    const merged = mergeAllCryptoSparklines(
      [
        {
          symbol: 'ETHUSDT',
          provider_symbol: 'ETHUSDT',
          price: 2000,
          change_24h_pct: 1,
          market_cap_rank: 1,
        },
      ],
      [{ symbol: 'ETHUSDT', sparkline_24h: bars5m }],
    )
    const items = mapAllCryptoList(merged, { currency: 'USD' })
    assert.equal(items[0]?.sparkline24h.length, 24)
  })

  it('maps sparkline_24h from all-crypto rows', () => {
    const bars5m = Array.from({ length: 288 }, (_, index) => 1000 + index)
    const items = mapAllCryptoList([
      {
        symbol: 'ETH',
        provider_symbol: 'ETHUSDT',
        name: 'Ethereum',
        price: 2069.22,
        change_24h_pct: -2.72,
        market_cap_rank: 2,
        sparkline_24h: bars5m,
      },
    ])

    assert.equal(items[0]?.sparkline24h.length, 24)
    assert.equal(items[0]?.sparkline24h[23], bars5m[bars5m.length - 1])
  })

  it('maps ETH and CBETH as distinct tickers sharing ETHUSDT quotes', () => {
    const items = mapAllCryptoList([
      {
        symbol: 'ETH',
        provider_symbol: 'ETHUSDT',
        name: 'Ethereum',
        price: 2069.22,
        change_24h_pct: -2.72,
        market_cap_rank: 2,
      },
      {
        symbol: 'CBETH',
        provider_symbol: 'ETHUSDT',
        name: 'Ethereum',
        price: 2069.22,
        change_24h_pct: -2.72,
        market_cap_rank: 9,
      },
    ])

    const tickers = items.map((row) => row.ticker)
    assert.deepEqual(tickers.filter((t) => t === 'ETH').length, 1)
    assert.deepEqual(tickers.filter((t) => t === 'CBETH').length, 1)
  })

  it('does not duplicate ETH when backend sends ETH + CBETH on ETHUSDT', () => {
    const items = mapAllCryptoList([
      {
        symbol: 'CBBTC',
        provider_symbol: 'BTCUSDT',
        name: 'Bitcoin',
        price: 75000,
        change_24h_pct: -2,
        market_cap_rank: 1,
      },
      {
        symbol: 'ETH',
        provider_symbol: 'ETHUSDT',
        name: 'Ethereum',
        price: 2069,
        change_24h_pct: -2.7,
        market_cap_rank: 2,
      },
      {
        symbol: 'CBETH',
        provider_symbol: 'ETHUSDT',
        name: 'Ethereum',
        price: 2069,
        change_24h_pct: -2.7,
        market_cap_rank: 3,
      },
    ])

    assert.equal(new Set(items.map((row) => row.ticker)).size, items.length)
    assert.ok(items.some((row) => row.ticker === 'ETH'))
    assert.ok(items.some((row) => row.ticker === 'CBETH'))
  })
})
