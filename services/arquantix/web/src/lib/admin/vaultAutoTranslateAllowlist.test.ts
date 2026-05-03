import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { shouldSkipPlainString } from '@/lib/admin/vaultAutoTranslateAllowlist'

describe('shouldSkipPlainString', () => {
  it('vide', () => {
    assert.equal(shouldSkipPlainString(''), true)
  })
  it('URL http', () => {
    assert.equal(shouldSkipPlainString('https://example.com/x'), true)
  })
  it('UUID', () => {
    assert.equal(shouldSkipPlainString('550e8400-e29b-41d4-a716-446655440000'), true)
  })
  it('texte éditorial', () => {
    assert.equal(shouldSkipPlainString('Rendement annuel fixe pour les investisseurs.'), false)
  })
})
