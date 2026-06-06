import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { VANCELIAN_VFEUR_VAULT } from '@/lib/portal/ledgity/ledgityConstants'
import { resolveCatalogSlugVaultAddress, resolveCatalogVaultSlugByAddress } from './catalogVaultSlugMap'

describe('resolveCatalogSlugVaultAddress', () => {
  it('résout le Flex Vault catalogue vers vfEUR', () => {
    assert.equal(
      resolveCatalogSlugVaultAddress('vancelianflexvault'),
      VANCELIAN_VFEUR_VAULT.toLowerCase(),
    )
  })

  it('retourne null pour un slug inconnu', () => {
    assert.equal(resolveCatalogSlugVaultAddress('unknown-offer'), null)
  })

  it('retrouve le slug catalogue depuis l’adresse vfEUR', () => {
    assert.equal(
      resolveCatalogVaultSlugByAddress(VANCELIAN_VFEUR_VAULT),
      'vancelianflexvault',
    )
  })
})
