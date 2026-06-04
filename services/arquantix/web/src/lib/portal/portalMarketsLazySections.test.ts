import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isMarketsDeferredSection,
  MARKETS_DEFERRED_SECTION_IDS,
  shouldShowMarketsFullSkeleton,
} from '@/lib/portal/portalMarketsLazySections'

describe('portalMarketsLazySections — O3', () => {
  it('sections secondaires figées', () => {
    assert.deepEqual(MARKETS_DEFERRED_SECTION_IDS, ['news', 'research', 'sidebar'])
    assert.equal(isMarketsDeferredSection('news'), true)
    assert.equal(isMarketsDeferredSection('top-crypto'), false)
  })

  it('skeleton plein écran seulement sans data', () => {
    assert.equal(shouldShowMarketsFullSkeleton(true, null), true)
    assert.equal(shouldShowMarketsFullSkeleton(true, { popular: [] }), false)
    assert.equal(shouldShowMarketsFullSkeleton(false, null), false)
  })
})
