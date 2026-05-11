import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isGoogleMapsIframeEmbedUrl,
  normalizeGoogleMapsEmbedInput,
} from './resolveMapsShareLink'

describe('normalizeGoogleMapsEmbedInput', () => {
  it('extrait le src depuis une iframe Google collée', () => {
    const html = `<iframe src="https://www.google.com/maps/embed?pb=test&#39;x" width="600"></iframe>`
    const n = normalizeGoogleMapsEmbedInput(html)
    assert.equal(n.includes('/maps/embed'), true)
    assert.equal(n.includes("'"), true)
    assert.equal(n.includes('&#39;'), false)
  })

  it('décode les entités dans une URL seule', () => {
    const u = 'https://www.google.com/maps/embed?pb=District%20d&#39;Abuta'
    assert.equal(
      normalizeGoogleMapsEmbedInput(u).includes("d'Abuta"),
      true,
    )
  })

  it('accepte l’iframe normalisée comme embed valide', () => {
    const iframe = `<iframe src="https://www.google.com/maps/embed?pb=foo" height="450"></iframe>`
    assert.equal(isGoogleMapsIframeEmbedUrl(iframe), true)
  })
})
