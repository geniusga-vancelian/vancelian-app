import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { sourceLocaleOrder } from '@/lib/i18n/integrity/prepareFixesStrategies'

describe('sourceLocaleOrder', () => {
  it('cible en → fr puis it', () => {
    assert.deepEqual(sourceLocaleOrder('en'), ['fr', 'it'])
  })

  it('cible fr → en puis it', () => {
    assert.deepEqual(sourceLocaleOrder('fr'), ['en', 'it'])
  })
})
