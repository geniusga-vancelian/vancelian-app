import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  applyMenuLanguageFixes,
  buildMenuUpsertPlanFromFixed,
  extractMenuFields,
  scanMenuLanguageDeep,
  type MenuInputForScan,
  type MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'
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

const MENU_BASE: MenuInputForScan = {
  id: 'menu-1',
  name: 'Primary',
  i18n: [{ locale: 'fr', name: 'Principal' }],
}

describe('menuCheckLanguage — extractMenuFields', () => {
  it('extrait Menu.name + tous les MenuItem.label activés (fallback baseLabel)', () => {
    const items: MenuItemInputForScan[] = [
      {
        id: 'item-1',
        index: 0,
        enabled: true,
        baseLabel: 'About',
        i18n: [],
      },
      {
        id: 'item-2',
        index: 1,
        enabled: true,
        baseLabel: 'Contact',
        i18n: [{ locale: 'fr', label: 'Contactez-nous' }],
      },
    ]
    const fields = extractMenuFields(MENU_BASE, items, 'fr')
    const byHint = new Map(fields.map((f) => [f.hintKey, f]))
    assert.equal(byHint.get('menu.name')?.value, 'Principal')
    assert.equal(byHint.get('item:item-1.label')?.value, 'About')
    assert.equal(byHint.get('item:item-2.label')?.value, 'Contactez-nous')
    assert.equal(fields.length, 3)
  })

  it('skip les items disabled (pas d’appel OpenAI inutile)', () => {
    const items: MenuItemInputForScan[] = [
      { id: 'item-1', index: 0, enabled: true, baseLabel: 'About', i18n: [] },
      { id: 'item-2', index: 1, enabled: false, baseLabel: 'Hidden', i18n: [] },
    ]
    const fields = extractMenuFields(MENU_BASE, items, 'fr')
    const hintKeys = fields.map((f) => f.hintKey)
    assert.ok(hintKeys.includes('item:item-1.label'))
    assert.ok(!hintKeys.includes('item:item-2.label'))
  })

  it('priorise i18n[locale] sur baseLabel pour la valeur scannée', () => {
    const items: MenuItemInputForScan[] = [
      {
        id: 'item-1',
        index: 0,
        enabled: true,
        baseLabel: 'Home',
        i18n: [
          { locale: 'fr', label: 'Accueil' },
          { locale: 'en', label: 'Home (en)' },
        ],
      },
    ]
    const fr = extractMenuFields(MENU_BASE, items, 'fr')
    const en = extractMenuFields(MENU_BASE, items, 'en')
    assert.equal(fr.find((f) => f.hintKey === 'item:item-1.label')?.value, 'Accueil')
    assert.equal(en.find((f) => f.hintKey === 'item:item-1.label')?.value, 'Home (en)')
  })

  it('attache groupId/groupLabel par item (ergonomie modale)', () => {
    const items: MenuItemInputForScan[] = [
      { id: 'item-1', index: 0, enabled: true, baseLabel: 'About', i18n: [] },
      { id: 'item-2', index: 1, enabled: true, baseLabel: 'Contact', i18n: [] },
    ]
    const fields = extractMenuFields(MENU_BASE, items, 'fr')
    const it1 = fields.find((f) => f.hintKey === 'item:item-1.label')
    const it2 = fields.find((f) => f.hintKey === 'item:item-2.label')
    assert.equal(it1?.groupId, 'item:item-1')
    assert.equal(it1?.groupLabel, 'Item #1')
    assert.equal(it2?.groupLabel, 'Item #2')
  })
})

describe('menuCheckLanguage — buildMenuUpsertPlanFromFixed', () => {
  it('reprojette correctement menu.name + items.label par itemId', () => {
    const fixed = new Map<string, string>([
      ['menu.name', 'Menu principal'],
      ['item:abc.label', 'À propos'],
      ['item:def.label', 'Contact'],
    ])
    const plan = buildMenuUpsertPlanFromFixed(fixed)
    assert.equal(plan.menuI18nName, 'Menu principal')
    assert.equal(plan.itemI18nLabelByItemId.get('abc'), 'À propos')
    assert.equal(plan.itemI18nLabelByItemId.get('def'), 'Contact')
    assert.equal(plan.itemI18nLabelByItemId.size, 2)
  })

  it('ignore les hintKeys non reconnus (forward compat)', () => {
    const fixed = new Map<string, string>([
      ['menu.name', 'X'],
      ['unknown.path', 'Y'],
    ])
    const plan = buildMenuUpsertPlanFromFixed(fixed)
    assert.equal(plan.menuI18nName, 'X')
    assert.equal(plan.itemI18nLabelByItemId.size, 0)
  })

  it('retourne un plan vide si aucun fix', () => {
    const plan = buildMenuUpsertPlanFromFixed(new Map())
    assert.equal(plan.menuI18nName, undefined)
    assert.equal(plan.itemI18nLabelByItemId.size, 0)
  })
})

describe('menuCheckLanguage — scanMenuLanguageDeep (mock LLM)', () => {
  it('détecte un Menu.name FR sur cible EN comme WRONG_LANGUAGE', async () => {
    const refiner = makeRefiner({})
    const menu: MenuInputForScan = {
      id: 'menu-1',
      name: LONG_FR,
      i18n: [],
    }
    const items: MenuItemInputForScan[] = [
      { id: 'item-1', index: 0, enabled: true, baseLabel: LONG_EN, i18n: [] },
    ]
    const r = await scanMenuLanguageDeep(menu, items, 'en', { refiner })
    const menuNameEntry = r.entries.find((e) => e.hintKey === 'menu.name')
    assert.equal(menuNameEntry?.status, 'WRONG_LANGUAGE')
    assert.equal(menuNameEntry?.detectedLocale, 'fr')
    assert.equal(menuNameEntry?.autoFixEligible, true)
  })

  it('reclassifie un MenuItem.label court ambigu via LLM', async () => {
    const refiner = makeRefiner({ Home: { locale: 'en', confidence: 0.9 } })
    const menu: MenuInputForScan = { id: 'm-1', name: '', i18n: [] }
    const items: MenuItemInputForScan[] = [
      { id: 'item-1', index: 0, enabled: true, baseLabel: 'Home', i18n: [] },
    ]
    const r = await scanMenuLanguageDeep(menu, items, 'fr', { refiner })
    const itemEntry = r.entries.find((e) => e.hintKey === 'item:item-1.label')
    assert.equal(itemEntry?.status, 'WRONG_LANGUAGE')
    assert.equal(itemEntry?.detectedLocale, 'en')
    assert.ok(r.llmRefinement.refined >= 1)
  })

  it('Menu.name court FR sur cible EN est auto-fix éligible MÊME sans LLM (regression #menu-name-not-corrected)', async () => {
    // Reproduit le bug: le path `menu.name` n'est pas matché par
    // `isShortHeaderPath` (qui ne reconnaît que eyebrow|label|kicker|title|subtitle).
    // Avant le fix `isShortHeader: true` dans extractMenuFields, l'apply
    // skippait silencieusement le nom du menu quand le LLM échouait/n'était
    // pas concluant, laissant `Menu.name` en français sur la locale EN/IT.
    const refiner: BatchLanguageRefiner = async () => ({
      results: [],
      tokensUsedApprox: 0,
      callCount: 0,
      hadError: true,
    })
    // Texte clairement FR (présence d'accents → bestEffortDetectShortLocale
    // détecte 'fr' avec certitude). Avant le fix, même un menu.name aussi
    // évident que « Très bien » n'était pas auto-fix éligible parce que
    // `isShortHeaderPath('menu.name')` retournait false → la branche
    // short-header n'était jamais exécutée pour le nom de menu.
    const menu: MenuInputForScan = {
      id: 'm-1',
      name: 'Découvrir',
      i18n: [],
    }
    const items: MenuItemInputForScan[] = []
    const r = await scanMenuLanguageDeep(menu, items, 'en', { refiner })
    const menuNameEntry = r.entries.find((e) => e.hintKey === 'menu.name')
    assert.ok(menuNameEntry, 'menu.name doit être scanné')
    // Court (< 24 chars) → NEEDS_REVIEW local. Sans LLM, doit néanmoins
    // être marqué auto-fix éligible grâce à `isShortHeader: true` côté
    // adaptateur menu (force le traitement short-header dans l'apply).
    assert.equal(menuNameEntry?.status, 'NEEDS_REVIEW')
    assert.equal(
      menuNameEntry?.autoFixEligible,
      true,
      'menu.name court FR doit être éligible à l\'auto-fix même sans LLM',
    )
  })

  it('extractMenuFields marque tous les champs avec isShortHeader=true', () => {
    const menu: MenuInputForScan = { id: 'm', name: 'Primary', i18n: [] }
    const items: MenuItemInputForScan[] = [
      { id: 'i1', index: 0, enabled: true, baseLabel: 'Home', i18n: [] },
    ]
    const fields = extractMenuFields(menu, items, 'fr')
    assert.ok(fields.every((f) => f.isShortHeader === true), 'tous les champs menu sont des short-headers')
  })

  it('items disabled ne sont jamais scannés (économie OpenAI)', async () => {
    let calledItems = 0
    const refiner: BatchLanguageRefiner = async (items) => {
      calledItems += items.length
      return { results: [], tokensUsedApprox: 0, callCount: 1, hadError: false }
    }
    const menu: MenuInputForScan = { id: 'm-1', name: '', i18n: [] }
    const items: MenuItemInputForScan[] = [
      { id: 'd-1', index: 0, enabled: false, baseLabel: 'AAA', i18n: [] },
      { id: 'd-2', index: 1, enabled: false, baseLabel: 'BBB', i18n: [] },
    ]
    const r = await scanMenuLanguageDeep(menu, items, 'fr', { refiner })
    assert.equal(r.entries.length, 0)
    assert.equal(calledItems, 0)
  })
})
