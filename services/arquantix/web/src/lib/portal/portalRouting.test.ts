import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  isFullSitePreviewPathname,
  isPortalPublicStaticPathname,
  isPublicPreviewPathname,
} from './portalRouting'

describe('isPortalPublicStaticPathname', () => {
  it('identifie les assets publics du portail', () => {
    assert.equal(isPortalPublicStaticPathname('/crypto_svgs/btc.svg'), true)
    assert.equal(isPortalPublicStaticPathname('/brand/vancelian/sso-apple.svg'), true)
    assert.equal(isPortalPublicStaticPathname('/icons/kalai/wallet.svg'), true)
  })

  it('rejette les routes applicatives', () => {
    assert.equal(isPortalPublicStaticPathname('/markets'), false)
    assert.equal(isPortalPublicStaticPathname('/app/markets'), false)
    assert.equal(isPortalPublicStaticPathname('/login'), false)
  })
})

describe('isPublicPreviewPathname', () => {
  it('accepte /preview et sous-chemins', () => {
    assert.equal(isPublicPreviewPathname('/preview'), true)
    assert.equal(isPublicPreviewPathname('/preview/home'), true)
    assert.equal(isPublicPreviewPathname('/preview/section/abc'), true)
  })

  it('rejette les autres chemins', () => {
    assert.equal(isPublicPreviewPathname('/admin/pages'), false)
    assert.equal(isPublicPreviewPathname('/app/dashboard'), false)
  })
})

describe('isFullSitePreviewPathname', () => {
  it('cible les pages CMS complètes', () => {
    assert.equal(isFullSitePreviewPathname('/preview/home'), true)
    assert.equal(isFullSitePreviewPathname('/preview/about'), true)
  })

  it('exclut les previews isolées', () => {
    assert.equal(isFullSitePreviewPathname('/preview/section/abc'), false)
    assert.equal(isFullSitePreviewPathname('/preview/email/newsletter'), false)
    assert.equal(isFullSitePreviewPathname('/preview'), false)
  })
})
