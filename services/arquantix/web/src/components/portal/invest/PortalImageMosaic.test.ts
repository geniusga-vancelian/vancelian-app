import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { portalImageMosaicCols } from './PortalImageMosaic'

describe('portalImageMosaicCols', () => {
  it('choisit 1, 2 ou 3 colonnes selon le nombre de photos', () => {
    assert.equal(portalImageMosaicCols(1), 1)
    assert.equal(portalImageMosaicCols(2), 2)
    assert.equal(portalImageMosaicCols(3), 3)
    assert.equal(portalImageMosaicCols(6), 3)
  })
})
