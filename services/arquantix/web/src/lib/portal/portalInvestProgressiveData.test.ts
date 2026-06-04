import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'
import {
  resolveInvestHubBundles,
  shouldShowInvestFullSkeleton,
} from '@/lib/portal/portalInvestProgressiveData'

const MARKETS_DIRECT: PortalMarketsPayload = {
  popular: [],
  topGainers: [],
  topLosers: [],
  favorites: [],
  bundles: [{ id: 'direct', name: 'Direct basket' } as PortalMarketsPayload['bundles'][number]],
  news: [],
}

const MARKETS_FALLBACK: PortalMarketsPayload = {
  popular: [],
  topGainers: [],
  topLosers: [],
  favorites: [],
  bundles: [{ id: 'fallback', name: 'Fallback basket' } as PortalMarketsPayload['bundles'][number]],
  news: [],
}

describe('portalInvestProgressiveData — G4-B2', () => {
  it('investData présent + markets absent + fallback v3 → pas skeleton, bundles fallback', () => {
    assert.equal(shouldShowInvestFullSkeleton(false, { offers: [] }), false)
    const resolved = resolveInvestHubBundles({
      marketsData: null,
      readMarketsCache: () => MARKETS_FALLBACK,
    })
    assert.equal(resolved.usedMarketsFallback, true)
    assert.equal(resolved.bundles[0]?.id, 'fallback')
  })

  it('investData présent + markets absent + fallback absent → pas skeleton, bundles []', () => {
    assert.equal(shouldShowInvestFullSkeleton(false, { offers: [] }), false)
    const resolved = resolveInvestHubBundles({
      marketsData: null,
      readMarketsCache: () => null,
    })
    assert.equal(resolved.bundles.length, 0)
    assert.equal(resolved.effectiveMarketsData, null)
  })

  it('investData absent + investLoading → skeleton', () => {
    assert.equal(shouldShowInvestFullSkeleton(true, null), true)
    assert.equal(shouldShowInvestFullSkeleton(false, null), false)
  })

  it('marketsData direct prioritaire sur fallback', () => {
    const resolved = resolveInvestHubBundles({
      marketsData: MARKETS_DIRECT,
      readMarketsCache: () => MARKETS_FALLBACK,
    })
    assert.equal(resolved.usedMarketsFallback, false)
    assert.equal(resolved.bundles[0]?.id, 'direct')
  })

  it('tout présent → bundles depuis marketsData', () => {
    const resolved = resolveInvestHubBundles({
      marketsData: MARKETS_DIRECT,
      readMarketsCache: () => null,
    })
    assert.equal(resolved.bundles.length, 1)
    assert.equal(shouldShowInvestFullSkeleton(false, { offers: [] }), false)
  })
})
