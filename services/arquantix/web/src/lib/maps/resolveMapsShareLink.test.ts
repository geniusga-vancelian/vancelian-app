import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  extractLatLngFromGoogleMapsUrl,
  isGoogleMapsIframeEmbedUrl,
  normalizeGoogleMapsEmbedInput,
  preferGoogleMapsPinnedEmbedIframeSrc,
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
})

describe('Google Maps embed coords & pin', () => {
  it('extrait lng,lat depuis un encodage pb !2d!3d dans l’URL', () => {
    const withPb =
      'https://www.google.com/maps/embed?pb=X!2d2.2945!3d48.8590!remaining'
    const coords = extractLatLngFromGoogleMapsUrl(withPb)
    assert.ok(coords)
    assert.equal(coords!.lat.toFixed(4), '48.8590')
    assert.equal(coords!.lng.toFixed(4), '2.2945')
  })

  it('preferGoogleMapsPinnedEmbedIframeSrc utilise q=&output=embed avec pin lorsque coords extrayables', () => {
    const embed =
      'https://www.google.com/maps/embed?pb=file!2d7.7436!3d48.5831!trail'
    const pinned = preferGoogleMapsPinnedEmbedIframeSrc(embed)
    assert.equal(isGoogleMapsIframeEmbedUrl(pinned), true)
    assert.match(pinned, /[?&]output=embed/)
    assert.match(pinned, /[?&]q=48\.5831%2C7\.7436/)
  })

  it('accepte l’iframe normalisée comme embed valide', () => {
    const iframe = `<iframe src="https://www.google.com/maps/embed?pb=foo" height="450"></iframe>`
    assert.equal(isGoogleMapsIframeEmbedUrl(iframe), true)
  })
})
