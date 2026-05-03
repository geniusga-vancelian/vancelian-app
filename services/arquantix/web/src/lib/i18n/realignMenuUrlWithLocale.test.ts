import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { realignPrimaryMenuUrlForActiveLocale } from './realignMenuUrlWithLocale'

describe('realignPrimaryMenuUrlForActiveLocale', () => {
  it('remplace le préfixe de locale', () => {
    assert.equal(
      realignPrimaryMenuUrlForActiveLocale('/fr/projects', 'en'),
      '/en/projects',
    )
    assert.equal(
      realignPrimaryMenuUrlForActiveLocale('/fr/about', 'it'),
      '/it/about',
    )
  })

  it('laisse les URLs externes inchangées', () => {
    assert.equal(
      realignPrimaryMenuUrlForActiveLocale('https://example.com/fr/foo', 'en'),
      'https://example.com/fr/foo',
    )
    assert.equal(realignPrimaryMenuUrlForActiveLocale('mailto:a@b.co', 'en'), 'mailto:a@b.co')
  })

  it('localise /projects et /projects/{slug} sans préfixe locale', () => {
    assert.equal(realignPrimaryMenuUrlForActiveLocale('/projects', 'en'), '/en/projects')
    assert.equal(
      realignPrimaryMenuUrlForActiveLocale('/projects/mon-slug', 'it'),
      '/it/projects/mon-slug',
    )
  })
})
