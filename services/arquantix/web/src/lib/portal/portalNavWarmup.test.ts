import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { PORTAL_MAIN_NAV_PREFETCH_ROUTES } from '@/lib/portal/portalNavWarmup'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

describe('portalNavWarmup — G4-B1.5', () => {
  it('prefetch routes — onglets shell + profil + wallet', () => {
    const hrefs = [...PORTAL_MAIN_NAV_PREFETCH_ROUTES]
    assert.ok(hrefs.includes(PORTAL_ROUTES.dashboard))
    assert.ok(hrefs.includes(PORTAL_ROUTES.markets))
    assert.ok(hrefs.includes(PORTAL_ROUTES.invest))
    assert.ok(hrefs.includes(PORTAL_ROUTES.profile))
    assert.ok(hrefs.includes(PORTAL_ROUTES.cryptoWallet))
    assert.equal(hrefs.length, 6)
  })
})
