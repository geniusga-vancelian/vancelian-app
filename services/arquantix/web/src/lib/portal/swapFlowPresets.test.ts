import assert from 'node:assert/strict'
import test from 'node:test'

import {
  pickDefaultSwapFromOption,
  pickDefaultSwapToOption,
  SWAP_DEFAULT_GENERIC_TARGET_ASSET,
  SWAP_DEFAULT_STABLE_ASSET,
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

test('pickDefaultSwapFromOption — préfère USDC pour un achat', () => {
  const picked = pickDefaultSwapFromOption(catalog, [], 'CBBTC', 'base')
  assert.equal(picked?.asset, SWAP_DEFAULT_STABLE_ASSET)
})

test('pickDefaultSwapToOption — préfère USDC pour une vente', () => {
  const picked = pickDefaultSwapToOption(catalog, 'CBBTC', 'base')
  assert.equal(picked?.asset, SWAP_DEFAULT_STABLE_ASSET)
})

test('pickDefaultSwapToOption — swap générique cible CBBTC', () => {
  const picked = pickDefaultSwapToOption(
    catalog,
    SWAP_DEFAULT_STABLE_ASSET,
    'base',
    SWAP_DEFAULT_GENERIC_TARGET_ASSET,
  )
  assert.equal(picked?.asset, SWAP_DEFAULT_GENERIC_TARGET_ASSET)
})
