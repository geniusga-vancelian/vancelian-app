import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  resolveEffectiveNavPath,
  resolveNavIsNavigating,
  resolveNavPendingBarVisible,
  shouldBeginPortalNavigation,
} from '@/lib/portal/portalNavInstantFeedback'

describe('portalNavInstantFeedback — G4-B1.5', () => {
  it('shouldBeginPortalNavigation — false si même route', () => {
    assert.equal(shouldBeginPortalNavigation('/app/dashboard', '/app/dashboard'), false)
    assert.equal(shouldBeginPortalNavigation('/app/dashboard/', '/app/dashboard'), false)
  })

  it('shouldBeginPortalNavigation — true si destination différente', () => {
    assert.equal(shouldBeginPortalNavigation('/app/dashboard', '/app/markets'), true)
  })

  it('effectivePath — pending prioritaire', () => {
    assert.equal(resolveEffectiveNavPath('/app/markets', '/app/dashboard'), '/app/markets')
    assert.equal(resolveEffectiveNavPath(null, '/app/dashboard'), '/app/dashboard')
  })

  it('pending bar et isNavigating dès clic optimiste', () => {
    assert.equal(resolveNavPendingBarVisible('/app/markets', '/app/dashboard'), true)
    assert.equal(resolveNavIsNavigating('/app/markets', '/app/dashboard'), true)
    assert.equal(resolveNavPendingBarVisible(null, '/app/dashboard'), false)
    assert.equal(resolveNavPendingBarVisible('/app/dashboard', '/app/dashboard'), false)
  })
})
