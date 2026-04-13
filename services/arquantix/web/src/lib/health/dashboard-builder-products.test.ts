import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { offersLayoutIncludesExclusiveOffers } from './dashboard-builder-products'

describe('offersLayoutIncludesExclusiveOffers', () => {
  it('returns true when body.widgets contains exclusive_offers', () => {
    const ok = offersLayoutIncludesExclusiveOffers({
      structure: {
        body: {
          widgets: [{ key: 'saving_vaults_widget' }, { key: 'exclusive_offers' }],
        },
      },
    })
    assert.equal(ok, true)
  })

  it('returns false when missing', () => {
    assert.equal(
      offersLayoutIncludesExclusiveOffers({
        structure: { body: { widgets: [{ key: 'saving_vaults_widget' }] } },
      }),
      false
    )
    assert.equal(offersLayoutIncludesExclusiveOffers(null), false)
    assert.equal(offersLayoutIncludesExclusiveOffers({}), false)
  })
})
