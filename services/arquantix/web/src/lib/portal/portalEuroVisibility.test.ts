import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'

import {
  CHAIN_FLOW_ASSETS,
} from '@/components/portal/wallet/chainFlowShared'
import { BASE_SWAP_TRADE_ASSETS } from '@/lib/portal/baseAllowedAssets'
import { buildWalletRows } from '@/lib/portal/dashboardFormat'
import { defaultInvestSources } from '@/lib/portal/portalInvestFlowFormat'
import {
  filterPortalEuroStablecoinSymbols,
  isPortalEuroFeaturesEnabled,
  resolvePortalEvmDepositAssetsLabel,
  resolvePortalSwapEligibleAssetsLabel,
  resolvePortalSwapPayWithLabel,
} from '@/lib/portal/portalEuroVisibility'
import { SWAP_V1_TOKENS } from '@/lib/portal/swapFlowTypes'

describe('portalEuroVisibility', () => {
  const prevEuroEnabled = process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED

  afterEach(() => {
    if (prevEuroEnabled === undefined) delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
    else process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED = prevEuroEnabled
  })

  describe('disabled by default', () => {
    beforeEach(() => {
      delete process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED
    })

    it('isPortalEuroFeaturesEnabled returns false', () => {
      assert.equal(isPortalEuroFeaturesEnabled(), false)
    })

    it('filters EUR/EURC symbols', () => {
      assert.deepEqual(filterPortalEuroStablecoinSymbols(['USDC', 'EURC', 'ETH']), ['USDC', 'ETH'])
    })

    it('hides euro account row on dashboard', () => {
      const rows = buildWalletRows(null, null, null, null, 'EUR')
      assert.equal(rows.some((row) => row.id === 'euro'), false)
    })

    it('removes EURC from deposit, swap and invest entry points', () => {
      assert.equal(CHAIN_FLOW_ASSETS.some((asset) => asset.sym === 'EURC'), false)
      assert.equal(BASE_SWAP_TRADE_ASSETS.includes('EURC'), false)
      assert.equal(SWAP_V1_TOKENS.includes('EURC'), false)
      assert.equal(defaultInvestSources().some((source) => source.key === 'eur'), false)
    })

    it('uses copy without euro stablecoin', () => {
      assert.equal(resolvePortalSwapEligibleAssetsLabel(), 'USDC, ETH, etc.')
      assert.equal(
        resolvePortalSwapPayWithLabel('Base', 'ETH'),
        'Pay with USDC or ETH on Base to buy ETH.',
      )
      assert.equal(resolvePortalEvmDepositAssetsLabel(), 'ETH, USDC ou USDT')
    })
  })

  describe('enabled via env', () => {
    beforeEach(() => {
      process.env.NEXT_PUBLIC_PORTAL_EURO_ENABLED = 'true'
    })

    it('isPortalEuroFeaturesEnabled returns true', () => {
      assert.equal(isPortalEuroFeaturesEnabled(), true)
    })

    it('keeps euro account row on dashboard', () => {
      const rows = buildWalletRows(null, null, null, null, 'EUR')
      assert.equal(rows.some((row) => row.id === 'euro'), true)
    })
  })
})
