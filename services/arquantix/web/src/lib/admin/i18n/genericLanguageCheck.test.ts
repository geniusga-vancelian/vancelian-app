import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildLanguageHintsFromGenericScan,
  scanFieldsLanguageDeep,
  scanFieldsLocally,
  type GenericFieldInput,
} from '@/lib/admin/i18n/genericLanguageCheck'
import type {
  BatchClassifyOutcome,
  BatchLanguageRefiner,
} from '@/lib/i18n/llm/batchClassifyLanguages'

const LONG_EN =
  'This paragraph is written entirely in English to allow reliable trigram-based detection. ' +
  'It describes marketing content without mixing other languages in this specific block.'

const LONG_FR =
  'Ce paragraphe est rédigé entièrement en français pour permettre une détection fiable par trigrammes. ' +
  'Il décrit un contenu marketing sans mélange avec d’autres langues dans ce bloc précis.'

function makeStaticRefiner(
  mapping: Record<string, { locale: 'fr' | 'en' | 'it' | 'und'; confidence: number }>,
  options?: { tokensPerCall?: number; throwOnce?: boolean },
): BatchLanguageRefiner {
  let alreadyThrown = false
  return async (items): Promise<BatchClassifyOutcome> => {
    if (options?.throwOnce && !alreadyThrown) {
      alreadyThrown = true
      throw new Error('mock refiner forced failure')
    }
    return {
      results: items.map((it) => {
        const m = mapping[it.text]
        return m
          ? { id: it.id, locale: m.locale, confidence: m.confidence }
          : { id: it.id, locale: 'und' as const, confidence: 0 }
      }),
      tokensUsedApprox: options?.tokensPerCall ?? 100,
      hadError: false,
      callCount: 1,
    }
  }
}

describe('genericLanguageCheck — scanFieldsLocally', () => {
  it('classe un texte EN propre comme OK quand target=en', () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: LONG_EN, kind: 'plain', domain: 'test' },
    ]
    const r = scanFieldsLocally(fields, 'en')
    assert.equal(r.entries.length, 1)
    assert.equal(r.entries[0].status, 'OK')
  })

  it('détecte WRONG_LANGUAGE pour un texte FR sur cible EN', () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: LONG_FR, kind: 'plain', domain: 'test' },
    ]
    const r = scanFieldsLocally(fields, 'en')
    assert.equal(r.entries[0].status, 'WRONG_LANGUAGE')
    assert.equal(r.entries[0].detectedLocale, 'fr')
    assert.equal(r.entries[0].autoFixEligible, true)
  })

  it('ignore les valeurs vides ou whitespace-only', () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: '', kind: 'plain', domain: 'test' },
      { hintKey: 'b', path: 'b', value: '   ', kind: 'plain', domain: 'test' },
      { hintKey: 'c', path: 'c', value: LONG_EN, kind: 'plain', domain: 'test' },
    ]
    const r = scanFieldsLocally(fields, 'en')
    assert.equal(r.entries.length, 1)
    assert.equal(r.entries[0].hintKey, 'c')
  })

  it('porte le groupId/groupLabel dans la sortie', () => {
    const fields: GenericFieldInput[] = [
      {
        hintKey: 'a',
        path: 'a',
        value: LONG_EN,
        kind: 'plain',
        domain: 'menu',
        groupId: 'item:42',
        groupLabel: 'Item #1',
      },
    ]
    const r = scanFieldsLocally(fields, 'en')
    assert.equal(r.entries[0].groupId, 'item:42')
    assert.equal(r.entries[0].groupLabel, 'Item #1')
    assert.equal(r.entries[0].domain, 'menu')
  })
})

describe('genericLanguageCheck — scanFieldsLanguageDeep (mock LLM)', () => {
  it('reclassifie un libellé court ambigu via le LLM (en sur cible fr → WRONG_LANGUAGE)', async () => {
    const fields: GenericFieldInput[] = [
      // « AAA » : ni accent FR ni stop-word reconnu → NEEDS_REVIEW localement.
      { hintKey: 'eyebrow', path: 'eyebrow', value: 'AAA', kind: 'plain', domain: 'footer' },
    ]
    const refiner = makeStaticRefiner({ AAA: { locale: 'en', confidence: 0.9 } })

    const r = await scanFieldsLanguageDeep(fields, 'fr', { refiner })

    assert.equal(r.entries.length, 1)
    assert.equal(r.entries[0].status, 'WRONG_LANGUAGE')
    assert.equal(r.entries[0].detectedLocale, 'en')
    assert.equal(r.entries[0].autoFixEligible, true)
    assert.equal(r.llmRefinement.attempted, 1)
    assert.equal(r.llmRefinement.refined, 1)
    assert.equal(r.llmRefinement.callCount, 1)
    assert.equal(r.llmRefinement.hadError, false)
  })

  it('quand le refiner throw, retombe sur le scan local sans crash (hadError=true)', async () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'eyebrow', path: 'eyebrow', value: 'AAA', kind: 'plain', domain: 'footer' },
    ]
    const refiner = makeStaticRefiner(
      { AAA: { locale: 'en', confidence: 0.9 } },
      { throwOnce: true },
    )
    const r = await scanFieldsLanguageDeep(fields, 'fr', { refiner })
    assert.equal(r.entries[0].status, 'NEEDS_REVIEW')
    assert.equal(r.llmRefinement.hadError, true)
    assert.equal(r.llmRefinement.refined, 0)
  })

  it("quand aucun champ n'est ambigu, n'appelle PAS le LLM", async () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: LONG_EN, kind: 'plain', domain: 'footer' },
    ]
    let called = 0
    const refiner: BatchLanguageRefiner = async () => {
      called += 1
      return { results: [], tokensUsedApprox: 0, callCount: 1, hadError: false }
    }
    const r = await scanFieldsLanguageDeep(fields, 'en', { refiner })
    assert.equal(called, 0)
    assert.equal(r.llmRefinement.attempted, 0)
    assert.equal(r.llmRefinement.callCount, 0)
  })

  it('propage la décision LLM aux duplicats (1 seul appel pour le même texte)', async () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: 'AAA', kind: 'plain', domain: 'footer' },
      { hintKey: 'b', path: 'b', value: 'AAA', kind: 'plain', domain: 'footer' },
      { hintKey: 'c', path: 'c', value: 'AAA', kind: 'plain', domain: 'footer' },
    ]
    let itemsSeen = 0
    const refiner: BatchLanguageRefiner = async (items) => {
      itemsSeen += items.length
      return {
        results: items.map((it) => ({ id: it.id, locale: 'en' as const, confidence: 0.9 })),
        tokensUsedApprox: 50,
        callCount: 1,
        hadError: false,
      }
    }
    const r = await scanFieldsLanguageDeep(fields, 'fr', { refiner })
    assert.equal(itemsSeen, 1, 'le texte dupliqué ne doit être envoyé qu’une seule fois')
    // Mais les 3 entries doivent être reclassifiées.
    assert.equal(r.entries.filter((e) => e.status === 'WRONG_LANGUAGE').length, 3)
  })
})

describe('genericLanguageCheck — buildLanguageHintsFromGenericScan', () => {
  it('construit une carte hintKey → Locale exploitable', async () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: LONG_EN, kind: 'plain', domain: 'footer' },
      { hintKey: 'b', path: 'b', value: LONG_FR, kind: 'plain', domain: 'footer' },
    ]
    const r = await scanFieldsLanguageDeep(fields, 'en', {
      refiner: async () => ({
        results: [],
        tokensUsedApprox: 0,
        callCount: 0,
        hadError: false,
      }),
    })
    const hints = buildLanguageHintsFromGenericScan(r)
    assert.equal(hints.get('a'), 'en')
    assert.equal(hints.get('b'), 'fr')
  })

  it('ignore les entrées sans detectedLocale (und LLM = pas de hint)', async () => {
    const fields: GenericFieldInput[] = [
      { hintKey: 'a', path: 'a', value: 'AAA', kind: 'plain', domain: 'footer' },
    ]
    const refiner = makeStaticRefiner({ AAA: { locale: 'und', confidence: 0 } })
    const r = await scanFieldsLanguageDeep(fields, 'en', { refiner })
    const hints = buildLanguageHintsFromGenericScan(r)
    assert.equal(hints.get('a'), undefined)
  })
})
