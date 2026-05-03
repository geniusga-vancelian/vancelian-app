import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { mergeArticleBlockLocalizedData } from '@/lib/blog/normalizeArticleBlocks'

describe('normalizeArticleBlocks — mergeArticleBlockLocalizedData', () => {
  it('priorise i18n[0].data sur data canonique', () => {
    const out = mergeArticleBlockLocalizedData({
      data: { text: 'base' },
      i18n: [{ data: { text: 'fr' } }],
    })
    assert.deepEqual(out, { text: 'fr' })
  })

  it('repli sur data si pas de ligne i18n', () => {
    const out = mergeArticleBlockLocalizedData({
      data: { text: 'only' },
      i18n: [],
    })
    assert.deepEqual(out, { text: 'only' })
  })

  it('repli sur data si i18n absent', () => {
    const out = mergeArticleBlockLocalizedData({
      data: { items: ['a'] },
    })
    assert.deepEqual(out, { items: ['a'] })
  })

  it('IMAGE legacy : structure minimale', () => {
    const out = mergeArticleBlockLocalizedData({
      data: { mediaId: 'm1', caption: 'L' },
      i18n: undefined,
    })
    assert.deepEqual(out, { mediaId: 'm1', caption: 'L' })
  })

  it('DOCUMENTS_LIST legacy documentMediaIds : pass-through (enrich séparé)', () => {
    const out = mergeArticleBlockLocalizedData({
      data: { documentMediaIds: ['a', 'b'], moduleTitle: 'Docs' },
    })
    assert.deepEqual(out, {
      documentMediaIds: ['a', 'b'],
      moduleTitle: 'Docs',
    })
  })

  it('bloc vide / data non objet : retourne tel quel', () => {
    assert.equal(mergeArticleBlockLocalizedData({ data: null }), null)
    assert.equal(mergeArticleBlockLocalizedData({ data: 'raw' }), 'raw')
  })

  it('HEADING : merge typique titre FR', () => {
    const merged = mergeArticleBlockLocalizedData({
      data: { text: '' },
      i18n: [{ data: { text: 'Titre' } }],
    })
    assert.equal((merged as { text?: string }).text, 'Titre')
  })
})
