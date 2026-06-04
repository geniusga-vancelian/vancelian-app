import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { LOMBARD_REVIEW_UI } from '@/components/portal/transaction/mappers/lombardReviewUiCopy'

describe('lombardReviewUiCopy — O4', () => {
  it('expose les libellés Review emprunt', () => {
    assert.match(LOMBARD_REVIEW_UI.title, /Récapitulatif/)
    assert.match(LOMBARD_REVIEW_UI.confirmCta, /Confirmer/)
    assert.equal(LOMBARD_REVIEW_UI.backButton, 'Retour')
  })
})
