import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildMenuSaveLocalePlan,
  selectActiveLocaleEditsForSave,
} from '@/lib/admin/menuSaveLocale'

/* -------------------------------------------------------------------------- */
/* buildMenuSaveLocalePlan                                                    */
/* -------------------------------------------------------------------------- */

describe('buildMenuSaveLocalePlan — locale par défaut', () => {
  it('met à jour Menu.name (base) quand activeLocale = defaultLocale', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'fr',
      defaultLocale: 'fr',
      menuNameInput: 'Menu principal',
      itemLabels: { 'item-1': 'Accueil', 'item-2': 'Contact' },
    })
    assert.equal(plan.menuNameToWrite, 'Menu principal')
    assert.equal(plan.diagnostics.didWriteMenuNameBase, true)
    assert.equal(plan.itemLabelsToWrite.size, 2)
    assert.equal(plan.itemLabelsToWrite.get('item-1'), 'Accueil')
    assert.equal(plan.itemLabelsToWrite.get('item-2'), 'Contact')
  })

  it('upsert MenuI18n même sur defaultLocale si la valeur est fournie', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'fr',
      defaultLocale: 'fr',
      menuI18nName: 'Override FR explicite',
    })
    assert.equal(plan.menuI18nNameToWrite, 'Override FR explicite')
    assert.equal(plan.diagnostics.didWriteMenuI18nName, true)
  })
})

describe('buildMenuSaveLocalePlan — locale traduite (verrouillage structure)', () => {
  it('IGNORE menuNameInput hors locale par défaut (structure verrouillée)', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
      menuNameInput: 'Doit être ignoré sur EN',
      menuI18nName: 'Main menu',
      itemLabels: { 'item-1': 'Home', 'item-2': 'Contact us' },
    })
    assert.equal(
      plan.menuNameToWrite,
      undefined,
      'Menu.name ne doit JAMAIS être touché hors defaultLocale (structure partagée)',
    )
    assert.equal(plan.diagnostics.didWriteMenuNameBase, false)
    assert.equal(plan.menuI18nNameToWrite, 'Main menu')
    assert.equal(plan.itemLabelsToWrite.size, 2)
  })

  it('IT : même comportement que EN', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'it',
      defaultLocale: 'fr',
      menuNameInput: 'Ignoré',
      menuI18nName: 'Menu principale',
      itemLabels: { 'item-1': 'Home' },
    })
    assert.equal(plan.menuNameToWrite, undefined)
    assert.equal(plan.menuI18nNameToWrite, 'Menu principale')
    assert.equal(plan.itemLabelsToWrite.get('item-1'), 'Home')
  })
})

describe('buildMenuSaveLocalePlan — gestion des valeurs vides', () => {
  it('ignore les labels vides ou whitespace-only (pas d\'écrasement par chaîne vide)', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
      menuI18nName: '',
      itemLabels: {
        'item-1': 'Home',
        'item-2': '',
        'item-3': '   ',
      },
    })
    assert.equal(plan.menuI18nNameToWrite, undefined, 'menuI18nName vide → ignoré')
    assert.equal(plan.itemLabelsToWrite.size, 1)
    assert.equal(plan.itemLabelsToWrite.has('item-1'), true)
    assert.equal(plan.itemLabelsToWrite.has('item-2'), false)
    assert.equal(plan.itemLabelsToWrite.has('item-3'), false)
    assert.deepEqual(plan.diagnostics.itemsSkippedEmpty.sort(), ['item-2', 'item-3'])
  })

  it('trim les valeurs avant écriture', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
      menuI18nName: '  Main menu  ',
      itemLabels: { 'item-1': '  Home  ' },
    })
    assert.equal(plan.menuI18nNameToWrite, 'Main menu')
    assert.equal(plan.itemLabelsToWrite.get('item-1'), 'Home')
  })

  it('rien à écrire → plan totalement vide, diagnostics cohérents', () => {
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
    })
    assert.equal(plan.menuNameToWrite, undefined)
    assert.equal(plan.menuI18nNameToWrite, undefined)
    assert.equal(plan.itemLabelsToWrite.size, 0)
    assert.equal(plan.diagnostics.didWriteMenuNameBase, false)
    assert.equal(plan.diagnostics.didWriteMenuI18nName, false)
    assert.equal(plan.diagnostics.itemsWritten.length, 0)
    assert.equal(plan.diagnostics.itemsSkippedEmpty.length, 0)
  })
})

describe('buildMenuSaveLocalePlan — invariants Footer-like', () => {
  it('idempotent : exécuter le plan 2x donne le même résultat (rien à modifier)', () => {
    const input = {
      activeLocale: 'en' as const,
      defaultLocale: 'fr' as const,
      menuI18nName: 'Main menu',
      itemLabels: { 'a': 'A', 'b': 'B' },
    }
    const p1 = buildMenuSaveLocalePlan(input)
    const p2 = buildMenuSaveLocalePlan(input)
    assert.deepEqual(
      Array.from(p1.itemLabelsToWrite.entries()).sort(),
      Array.from(p2.itemLabelsToWrite.entries()).sort(),
    )
    assert.equal(p1.menuI18nNameToWrite, p2.menuI18nNameToWrite)
  })

  it('menuNameInput + activeLocale=fr → écrit Menu.name ; menuNameInput + activeLocale=en → ignoré', () => {
    const onFr = buildMenuSaveLocalePlan({
      activeLocale: 'fr',
      defaultLocale: 'fr',
      menuNameInput: 'X',
    })
    const onEn = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
      menuNameInput: 'X',
    })
    assert.equal(onFr.menuNameToWrite, 'X')
    assert.equal(onEn.menuNameToWrite, undefined)
  })
})

/* -------------------------------------------------------------------------- */
/* selectActiveLocaleEditsForSave                                             */
/* -------------------------------------------------------------------------- */

describe('selectActiveLocaleEditsForSave — extraction des edits par locale', () => {
  it('ne garde que les valeurs de la locale active', () => {
    const r = selectActiveLocaleEditsForSave({
      activeLocale: 'en',
      i18nLabels: {
        'item-1': { fr: 'Accueil', en: 'Home', it: 'Casa' },
        'item-2': { fr: 'Contact', en: 'Contact us', it: 'Contatti' },
      },
      menuI18nNames: { fr: 'Menu principal', en: 'Main menu', it: 'Menu principale' },
    })
    assert.deepEqual(r.itemLabels, { 'item-1': 'Home', 'item-2': 'Contact us' })
    assert.equal(r.menuI18nName, 'Main menu')
  })

  it('items sans entrée pour la locale active sont absents (pas de chaîne vide)', () => {
    const r = selectActiveLocaleEditsForSave({
      activeLocale: 'it',
      i18nLabels: {
        'item-1': { fr: 'Accueil', en: 'Home' },
        'item-2': { fr: 'Contact', it: 'Contatti' },
      },
      menuI18nNames: { fr: 'Menu principal' },
    })
    assert.equal(r.itemLabels['item-1'], undefined)
    assert.equal(r.itemLabels['item-2'], 'Contatti')
    assert.equal(r.menuI18nName, undefined)
  })

  it('boucle complète : extract + buildPlan → cohérent avec ce qu\'on attend de l\'admin', () => {
    const extracted = selectActiveLocaleEditsForSave({
      activeLocale: 'en',
      i18nLabels: {
        'item-1': { fr: 'Accueil', en: 'Home' },
        'item-2': { fr: 'Contact', en: '' },
      },
      menuI18nNames: { fr: 'Menu principal', en: 'Main menu' },
    })
    const plan = buildMenuSaveLocalePlan({
      activeLocale: 'en',
      defaultLocale: 'fr',
      menuI18nName: extracted.menuI18nName,
      itemLabels: extracted.itemLabels,
    })
    assert.equal(plan.menuI18nNameToWrite, 'Main menu')
    assert.equal(plan.itemLabelsToWrite.get('item-1'), 'Home')
    assert.equal(plan.itemLabelsToWrite.has('item-2'), false, 'EN vide ignoré')
  })
})
