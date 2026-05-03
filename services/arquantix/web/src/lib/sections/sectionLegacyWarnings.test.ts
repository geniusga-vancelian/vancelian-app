import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { getSectionLegacyWarnings } from './sectionLegacyWarnings'

describe('getSectionLegacyWarnings', () => {
  it('faq : subtitle sans title → info', () => {
    const w = getSectionLegacyWarnings('faq', { subtitle: 'Legacy', title: '' })
    assert.equal(w.length, 1)
    assert.equal(w[0]?.code, 'faq_subtitle_fallback')
    assert.equal(w[0]?.level, 'info')
  })

  it('faq : title renseigné → aucun avertissement', () => {
    assert.equal(
      getSectionLegacyWarnings('faq', { subtitle: 'Legacy', title: 'OK' }).length,
      0,
    )
  })

  it('cta : ctaText sans primaryButtonText → info', () => {
    const w = getSectionLegacyWarnings('cta', { ctaText: 'Go', primaryButtonText: '' })
    assert.equal(w.length, 1)
    assert.equal(w[0]?.code, 'cta_ctaText_alias')
  })

  it('feature_grid : imageUrl seule → warn', () => {
    const w = getSectionLegacyWarnings('feature_grid', {
      imageUrl: 'https://x',
    })
    assert.equal(w.length, 1)
    assert.equal(w[0]?.level, 'warn')
    assert.equal(w[0]?.code, 'feature_grid_imageUrl_only')
  })

  it('feature_grid : imageMediaId présent → pas d’avertissement imageUrl', () => {
    assert.equal(
      getSectionLegacyWarnings('feature_grid', {
        imageUrl: 'https://x',
        imageMediaId: 'm1',
      }).length,
      0,
    )
  })

  it('how_it_works : surface dark → info', () => {
    const w = getSectionLegacyWarnings('how_it_works', { surface: 'dark' })
    assert.equal(w.length, 1)
    assert.equal(w[0]?.code, 'how_it_works_surface_ignored')
  })
})
