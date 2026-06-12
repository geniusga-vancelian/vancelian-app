import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readTitlePagePromoVideoUrl, shouldShowVaultMetricsFundingStrip } from './vaultModulePortalFormat'

describe('readTitlePagePromoVideoUrl', () => {
  it('lit promoVideoUrl depuis le module TitlePage', () => {
    const url = readTitlePagePromoVideoUrl([
      {
        id: 'tp1',
        type: 'TitlePage',
        enabled: true,
        content: { promoVideoUrl: 'https://www.youtube.com/watch?v=JpT4qLGlqzE' },
      },
    ])
    assert.equal(url, 'https://www.youtube.com/watch?v=JpT4qLGlqzE')
  })

  it('préfère promoVideoUrls[0] quand présent', () => {
    const url = readTitlePagePromoVideoUrl([
      {
        id: 'tp1',
        type: 'TitlePage',
        enabled: true,
        content: {
          promoVideoUrls: ['https://youtu.be/first'],
          promoVideoUrl: 'https://youtu.be/second',
        },
      },
    ])
    assert.equal(url, 'https://youtu.be/first')
  })
})

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
