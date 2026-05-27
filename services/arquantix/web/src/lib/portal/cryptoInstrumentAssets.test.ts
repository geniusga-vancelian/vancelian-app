import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { normalizeCryptoBaseTicker } from './cryptoInstrumentAssets'

describe('normalizeCryptoBaseTicker', () => {
  it('preserves stablecoin tickers like EURC', () => {
    assert.equal(normalizeCryptoBaseTicker('EURC'), 'EURC')
    assert.equal(normalizeCryptoBaseTicker('USDC'), 'USDC')
  })

  it('strips quote suffix from trading pairs', () => {
    assert.equal(normalizeCryptoBaseTicker('ETHUSDT'), 'ETH')
    assert.equal(normalizeCryptoBaseTicker('BTCUSDC'), 'BTC')
  })

  it('maps wrapped BTC variants to BTC avatar', () => {
    assert.equal(normalizeCryptoBaseTicker('CBBTC'), 'BTC')
  })

  it('maps wrapped ETH variants to ETH avatar for market quotes', () => {
    assert.equal(normalizeCryptoBaseTicker('CBETH'), 'ETH')
  })
})
