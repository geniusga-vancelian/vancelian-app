import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'

const LONG_FR =
  'Ce paragraphe est rédigé entièrement en français pour permettre une détection fiable par trigrammes. ' +
  'Il décrit un contenu marketing sans mélange avec d’autres langues dans ce bloc précis.'

const LONG_EN =
  'This paragraph is written entirely in English to allow reliable trigram-based detection. ' +
  'It describes marketing content without mixing other languages in this specific block.'

describe('classifyTextForTargetLocale (Lot 1)', () => {
  it('texte vide → MISSING', () => {
    const r = classifyTextForTargetLocale('', 'fr')
    assert.equal(r.status, 'MISSING')
  })

  it('texte court → NEEDS_REVIEW', () => {
    const r = classifyTextForTargetLocale('Bonjour.', 'fr')
    assert.equal(r.status, 'NEEDS_REVIEW')
  })

  it('long FR vs cible en → WRONG_LANGUAGE', () => {
    const r = classifyTextForTargetLocale(LONG_FR, 'en')
    assert.equal(r.status, 'WRONG_LANGUAGE')
    assert.equal(r.detectedLocale, 'fr')
  })

  it('long EN vs cible fr → WRONG_LANGUAGE', () => {
    const r = classifyTextForTargetLocale(LONG_EN, 'fr')
    assert.equal(r.status, 'WRONG_LANGUAGE')
    assert.equal(r.detectedLocale, 'en')
  })

  it('long FR vs cible fr → OK', () => {
    const r = classifyTextForTargetLocale(LONG_FR, 'fr')
    assert.equal(r.status, 'OK')
    assert.equal(r.detectedLocale, 'fr')
  })
})
