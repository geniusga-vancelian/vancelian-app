import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, it } from 'node:test'

import { PORTAL_CACHE_KEYS } from '@/lib/portal/portalCacheKeys'
import {
  hasPortalRouteCachedPreview,
  readPortalRouteCachedPayload,
} from '@/lib/portal/portalRouteCachePreview'
import { writePortalCache, invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import type { PortalInvestPayload } from '@/lib/portal/investTypes'
import type { PortalMarketsPayload } from '@/lib/portal/marketsTypes'

const PREVIEW_SOURCE = path.join(
  process.cwd(),
  'src/lib/portal/portalRouteCachePreview.ts',
)

describe('portalRouteCachePreview — clés alignées écrans', () => {
  it('preview markets utilise la même clé que PortalMarketsScreen', () => {
    const screenSource = readFileSync(
      path.join(process.cwd(), 'src/components/portal/markets/PortalMarketsScreen.tsx'),
      'utf8',
    )
    assert.match(screenSource, /PORTAL_CACHE_KEYS\.markets/)
    assert.doesNotMatch(screenSource, /portal:markets:v2/)
  })

  it('preview invest utilise la même clé que PortalInvestScreen', () => {
    const screenSource = readFileSync(
      path.join(process.cwd(), 'src/components/portal/invest/PortalInvestScreen.tsx'),
      'utf8',
    )
    assert.match(screenSource, /PORTAL_CACHE_KEYS\.invest/)
    assert.doesNotMatch(screenSource, /portal:invest:v2/)
  })

  it('portalRouteCachePreview ne référence plus v2', () => {
    const previewSource = readFileSync(PREVIEW_SOURCE, 'utf8')
    assert.doesNotMatch(previewSource, /portal:markets:v2/)
    assert.doesNotMatch(previewSource, /portal:invest:v2/)
    assert.match(previewSource, /PORTAL_CACHE_KEYS\.markets/)
    assert.match(previewSource, /PORTAL_CACHE_KEYS\.invest/)
  })

  it('lit le cache markets v3 écrit par l’écran', () => {
    invalidatePortalCache(PORTAL_CACHE_KEYS.markets)
    const payload = { popular: [], topGainers: [], topLosers: [], favorites: [], bundles: [], news: [] } as PortalMarketsPayload
    writePortalCache(PORTAL_CACHE_KEYS.markets, payload, 60_000)

    const preview = readPortalRouteCachedPayload(PORTAL_ROUTES.markets)
    assert.equal(preview?.kind, 'markets')
    assert.equal(hasPortalRouteCachedPreview(PORTAL_ROUTES.markets), true)

    invalidatePortalCache(PORTAL_CACHE_KEYS.markets)
    assert.equal(hasPortalRouteCachedPreview(PORTAL_ROUTES.markets), false)
  })

  it('lit le cache invest v3 écrit par l’écran', () => {
    invalidatePortalCache(PORTAL_CACHE_KEYS.invest)
    const payload = { sections: [] } as PortalInvestPayload
    writePortalCache(PORTAL_CACHE_KEYS.invest, payload, 60_000)

    const preview = readPortalRouteCachedPayload(PORTAL_ROUTES.invest)
    assert.equal(preview?.kind, 'invest')
    assert.equal(hasPortalRouteCachedPreview(PORTAL_ROUTES.invest), true)

    invalidatePortalCache(PORTAL_CACHE_KEYS.invest)
    assert.equal(hasPortalRouteCachedPreview(PORTAL_ROUTES.invest), false)
  })
})
