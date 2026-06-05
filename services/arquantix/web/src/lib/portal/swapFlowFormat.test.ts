import assert from 'node:assert/strict'
import test from 'node:test'

import {
  formatSwapCryptoAmount,
  resolveSwapAssetDecimals,
} from '@/lib/portal/swapFlowFormat'
import type { SwapCatalogAsset } from '@/lib/portal/swapFlowTypes'

const catalog: SwapCatalogAsset[] = [
  {
    symbol: 'USDC',
    display_name: 'USD Coin',
    chains: ['base'],
    decimals: 6,
    min_amount: '1',
    max_amount: '1000000',
  },
  {
    symbol: 'CBBTC',
    display_name: 'Coinbase Wrapped BTC',
    chains: ['base'],
    decimals: 8,
    min_amount: '0.0001',
    max_amount: '100',
  },
]

test('formatSwapCryptoAmount — petits montants BTC en décimal, jamais en scientifique', () => {
  assert.equal(formatSwapCryptoAmount(0.0000159, 'CBBTC'), '0.0000159')
  assert.equal(formatSwapCryptoAmount('0.00001580', 'CBBTC'), '0.0000158')
  assert.equal(formatSwapCryptoAmount(1.59e-5, 'CBBTC'), '0.0000159')
  assert.equal(formatSwapCryptoAmount(0.00000001, 'CBBTC'), '0.00000001')
})

test('formatSwapCryptoAmount — montants >= 1 adaptés par actif', () => {
  assert.equal(formatSwapCryptoAmount(1, 'USDC'), '1')
  assert.equal(formatSwapCryptoAmount(244.677797, 'USDC'), '244.677797')
  assert.equal(formatSwapCryptoAmount(0.5, 'ETH'), '0.5')
})

test('resolveSwapAssetDecimals — catalogue prioritaire', () => {
  assert.equal(resolveSwapAssetDecimals('CBBTC', catalog), 8)
  assert.equal(resolveSwapAssetDecimals('USDC', catalog), 6)
  assert.equal(resolveSwapAssetDecimals('CBBTC'), 8)
})
