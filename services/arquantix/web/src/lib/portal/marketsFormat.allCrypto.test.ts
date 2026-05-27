import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { mapAllCryptoList } from '@/lib/portal/marketsFormat'

describe('mapAllCryptoList', () => {
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
