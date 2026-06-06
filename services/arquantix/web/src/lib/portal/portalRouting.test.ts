import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  isFullSitePreviewPathname,
  isPortalPublicStaticPathname,
  isPublicPreviewPathname,
  portalLedgityVaultInvestRoute,
  portalMorphoVaultInvestRoute,
  portalVaultInvestRoute,
  resolvePortalVaultEngineInvestRoute,
  resolvePortalVaultProductInvestRoute,
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

describe('resolvePortalVaultProductInvestRoute', () => {
  it('route un vault_simple Ledgity par adresse on-chain', () => {
    const address = '0x46db81f232df1884081368cd2aacc9e6ec6489a2'
    const href = resolvePortalVaultProductInvestRoute({
      slug: 'vancelianflexvault',
      vaultEngineConfigId: 'cfg-uuid',
      vaultAddress: address,
      integrationMode: 'ledgity_vault',
    })
    assert.equal(href, portalLedgityVaultInvestRoute(address))
  })

  it('route un vault_simple Morpho par adresse', () => {
    const address = '0x916f179d5d9b7d8ad815ac2f8570aabf0c6a6e38'
    const href = resolvePortalVaultProductInvestRoute({
      slug: 'morpho-usdc',
      vaultEngineConfigId: 'cfg-morpho',
      vaultAddress: address,
      integrationMode: 'direct_morpho',
    })
    assert.equal(href, portalMorphoVaultInvestRoute(address))
  })

  it('retombe sur la page lending mock sans moteur', () => {
    const href = resolvePortalVaultProductInvestRoute({
      slug: 'niseko',
      vaultEngineConfigId: null,
      vaultAddress: null,
      integrationMode: null,
    })
    assert.equal(href, portalVaultInvestRoute('niseko'))
  })
})

describe('resolvePortalVaultEngineInvestRoute', () => {
  it('route depuis un snapshot moteur Ledgity par adresse', () => {
    const address = '0x46db81f232df1884081368cd2aacc9e6ec6489a2'
    const href = resolvePortalVaultEngineInvestRoute(
      {
        portal_config_id: 'cfg-uuid',
        integration_mode: 'ledgity_vault',
        vault_address: address,
      },
      'vancelianflexvault',
      'withdraw',
    )
    assert.equal(href, portalLedgityVaultInvestRoute(address, 'withdraw'))
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
