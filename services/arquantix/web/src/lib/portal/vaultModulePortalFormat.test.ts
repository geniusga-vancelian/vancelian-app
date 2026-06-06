import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { shouldShowVaultMetricsFundingStrip } from './vaultModulePortalFormat'

describe('shouldShowVaultMetricsFundingStrip', () => {
  it('masque la bande funding sans FundingModule même si lending existe côté offre', () => {
    assert.equal(shouldShowVaultMetricsFundingStrip(null), false)
    assert.equal(shouldShowVaultMetricsFundingStrip(undefined), false)
  })

  it('affiche la bande funding uniquement avec un FundingModule explicite', () => {
    assert.equal(
      shouldShowVaultMetricsFundingStrip({ id: 'f1', type: 'FundingModule', enabled: true, content: {} }),
      true,
    )
  })
})
