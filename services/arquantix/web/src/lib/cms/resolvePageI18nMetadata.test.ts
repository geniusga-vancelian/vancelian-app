import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { resolvePageTitleDescriptionWithFallback } from './resolvePageI18nMetadata'

describe('resolvePageTitleDescriptionWithFallback', () => {
  it('priorité PageI18n locale demandée', () => {
    const r = resolvePageTitleDescriptionWithFallback(
      { title: 'Root', description: 'D root' },
      { title: 'EN title', description: 'EN desc' },
      { title: 'FR title', description: 'FR desc' },
    )
    assert.equal(r.title, 'EN title')
    assert.equal(r.description, 'EN desc')
  })

  it('fallback vers locale par défaut si primary vide', () => {
    const r = resolvePageTitleDescriptionWithFallback(
      { title: 'Root', description: null },
      { title: '', description: null },
      { title: 'FR title', description: 'FR desc' },
    )
    assert.equal(r.title, 'FR title')
    assert.equal(r.description, 'FR desc')
  })

  it('fallback final Page.title / description', () => {
    const r = resolvePageTitleDescriptionWithFallback(
      { title: 'Root T', description: 'Root D' },
      null,
      null,
    )
    assert.equal(r.title, 'Root T')
    assert.equal(r.description, 'Root D')
  })
})
