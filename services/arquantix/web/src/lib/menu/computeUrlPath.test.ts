import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { computeMenuItemUrlPath } from './computeUrlPath'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'

describe('computeMenuItemUrlPath', () => {
  it('racine → /{locale}', () => {
    assert.equal(computeMenuItemUrlPath(true, 'anything', 'fr'), '/fr')
  })

  it('slug home → /{locale}', () => {
    assert.equal(computeMenuItemUrlPath(false, 'home', 'en'), '/en')
  })

  it('page CMS classique → /{locale}/{slug}', () => {
    assert.equal(
      computeMenuItemUrlPath(false, 'about', 'fr', 'homepage'),
      '/fr/about',
    )
  })

  it('vault_builder → /{locale}/projects/{slug}', () => {
    assert.equal(
      computeMenuItemUrlPath(false, 'mon-vault', 'fr', VAULT_BUILDER_TEMPLATE),
      '/fr/projects/mon-vault',
    )
    assert.equal(
      computeMenuItemUrlPath(false, 'mon-vault', 'en', VAULT_BUILDER_TEMPLATE),
      '/en/projects/mon-vault',
    )
  })
})
