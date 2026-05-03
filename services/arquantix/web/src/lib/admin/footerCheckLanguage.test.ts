import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  applyFooterFixesToBlock,
  extractFooterFields,
  scanFooterLanguageDeep,
} from '@/lib/admin/footerCheckLanguage'
import type {
  BatchClassifyOutcome,
  BatchLanguageRefiner,
} from '@/lib/i18n/llm/batchClassifyLanguages'

const LONG_FR =
  'Ce paragraphe est rédigé entièrement en français pour permettre une détection fiable par trigrammes. ' +
  'Il décrit un contenu marketing sans mélange avec d’autres langues dans ce bloc précis.'

const LONG_EN =
  'This paragraph is written entirely in English to allow reliable trigram-based detection. ' +
  'It describes marketing content without mixing other languages in this specific block.'

function makeRefiner(
  mapping: Record<string, { locale: 'fr' | 'en' | 'it' | 'und'; confidence: number }>,
): BatchLanguageRefiner {
  return async (items): Promise<BatchClassifyOutcome> => ({
    results: items.map((it) => {
      const m = mapping[it.text]
      return m
        ? { id: it.id, locale: m.locale, confidence: m.confidence }
        : { id: it.id, locale: 'und' as const, confidence: 0 }
    }),
    tokensUsedApprox: 50,
    callCount: 1,
    hadError: false,
  })
}

describe('footerCheckLanguage — extractFooterFields', () => {
  it('extrait copyright, description, newsletter, links[].label, legalTexts[]', () => {
    const fields = extractFooterFields({
      copyright: '© 2026',
      description: 'Tagline',
      newsletterTitle: 'Subscribe',
      newsletterPlaceholder: 'Email',
      newsletterButtonLabel: 'Go',
      links: [
        { label: 'Privacy', href: '/privacy', category: 'Legal' },
        { label: 'Terms', href: '/terms', category: 'Legal' },
      ],
      legalTexts: ['Mention 1', 'Mention 2'],
    })

    const paths = new Set(fields.map((f) => f.path))
    assert.ok(paths.has('copyright'))
    assert.ok(paths.has('description'))
    assert.ok(paths.has('newsletterTitle'))
    assert.ok(paths.has('newsletterPlaceholder'))
    assert.ok(paths.has('newsletterButtonLabel'))
    assert.ok(paths.has('links[0].label'))
    assert.ok(paths.has('links[1].label'))
    assert.ok(paths.has('legalTexts[0]'))
    assert.ok(paths.has('legalTexts[1]'))
  })

  it('exclut explicitement href, category, socialLinks[].href, backgroundColor', () => {
    const fields = extractFooterFields({
      copyright: '© 2026',
      links: [{ label: 'X', href: '/x', category: 'Cat' }],
      socialLinks: [{ platform: 'youtube', href: 'https://youtube.com/x' }],
      backgroundColor: '#000',
      logoMediaId: 'media-1',
    })
    const paths = fields.map((f) => f.path)
    assert.ok(!paths.includes('links[0].href'))
    assert.ok(!paths.includes('links[0].category'))
    assert.ok(!paths.some((p) => p.includes('socialLinks')))
    assert.ok(!paths.includes('backgroundColor'))
    assert.ok(!paths.includes('logoMediaId'))
  })

  it('ignore les champs vides ou whitespace-only', () => {
    const fields = extractFooterFields({
      copyright: '',
      description: '   ',
      newsletterTitle: 'Subscribe',
      links: [
        { label: '', href: '/x', category: '' },
        { label: 'Real', href: '/r', category: '' },
      ],
      legalTexts: ['', 'Real text'],
    })
    const paths = new Set(fields.map((f) => f.path))
    assert.ok(!paths.has('copyright'))
    assert.ok(!paths.has('description'))
    assert.ok(paths.has('newsletterTitle'))
    assert.ok(!paths.has('links[0].label'))
    assert.ok(paths.has('links[1].label'))
    assert.ok(!paths.has('legalTexts[0]'))
    assert.ok(paths.has('legalTexts[1]'))
  })
})

describe('footerCheckLanguage — applyFooterFixesToBlock', () => {
  it('remplace les valeurs ciblées sans toucher aux autres', () => {
    const original = {
      copyright: '© Old',
      description: 'Old desc',
      links: [
        { label: 'Old A', href: '/a', category: 'C' },
        { label: 'Old B', href: '/b', category: 'C' },
      ],
      legalTexts: ['Old legal 1', 'Old legal 2'],
      backgroundColor: '#000',
    }
    const fixed = new Map<string, string>([
      ['copyright', '© New'],
      ['links[0].label', 'New A'],
      ['legalTexts[1]', 'New legal 2'],
    ])
    const out = applyFooterFixesToBlock(original, fixed)
    assert.equal(out.copyright, '© New')
    assert.equal(out.description, 'Old desc')
    assert.equal(out.links?.[0]?.label, 'New A')
    assert.equal(out.links?.[0]?.href, '/a', 'href intact (clé technique)')
    assert.equal(out.links?.[1]?.label, 'Old B')
    assert.equal(out.legalTexts?.[0], 'Old legal 1')
    assert.equal(out.legalTexts?.[1], 'New legal 2')
    assert.equal(out.backgroundColor, '#000')
  })

  it('retourne un nouvel objet (pas de mutation in-place)', () => {
    const original = { copyright: 'old', links: [{ label: 'a', href: '/a' }] }
    const out = applyFooterFixesToBlock(
      original,
      new Map([['copyright', 'new']]),
    )
    assert.notEqual(out, original)
    assert.equal(original.copyright, 'old', "l'entrée n'est pas mutée")
    assert.equal(out.copyright, 'new')
  })

  it('si fixedByHintKey est vide, retourne une copie superficielle inchangée', () => {
    const original = { copyright: 'old' }
    const out = applyFooterFixesToBlock(original, new Map())
    assert.deepEqual(out, original)
  })
})

describe('footerCheckLanguage — scanFooterLanguageDeep (mock LLM)', () => {
  it('détecte un copyright FR sur cible EN comme WRONG_LANGUAGE', async () => {
    const refiner = makeRefiner({})
    const r = await scanFooterLanguageDeep(
      {
        copyright: LONG_FR,
        description: LONG_EN,
        newsletterTitle: 'Subscribe',
      },
      'en',
      { refiner },
    )
    const copy = r.entries.find((e) => e.path === 'copyright')
    assert.equal(copy?.status, 'WRONG_LANGUAGE')
    assert.equal(copy?.detectedLocale, 'fr')
    assert.equal(copy?.autoFixEligible, true)
  })

  it('reclassifie un newsletterButtonLabel court via LLM (en sur cible fr)', async () => {
    const refiner = makeRefiner({ subscribe: { locale: 'en', confidence: 0.95 } })
    const r = await scanFooterLanguageDeep(
      {
        copyright: LONG_FR,
        newsletterButtonLabel: 'subscribe',
      },
      'fr',
      { refiner },
    )
    const btn = r.entries.find((e) => e.path === 'newsletterButtonLabel')
    assert.equal(btn?.status, 'WRONG_LANGUAGE')
    assert.equal(btn?.detectedLocale, 'en')
    assert.ok(r.llmRefinement.refined >= 1)
  })
})
