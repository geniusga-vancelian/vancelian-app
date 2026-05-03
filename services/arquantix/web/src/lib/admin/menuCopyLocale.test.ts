import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { buildMenuCopyPlan } from '@/lib/admin/menuCopyLocale'
import type {
  MenuInputForScan,
  MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'

/* -------------------------------------------------------------------------- */
/* Fixtures                                                                    */
/* -------------------------------------------------------------------------- */

function baseMenu(): MenuInputForScan {
  return {
    id: 'menu-1',
    name: 'Menu principal',
    i18n: [{ locale: 'fr', name: 'Menu principal' }],
  }
}

function makeItem(overrides: Partial<MenuItemInputForScan> = {}): MenuItemInputForScan {
  return {
    id: 'item-base',
    index: 0,
    enabled: true,
    baseLabel: 'Accueil',
    i18n: [],
    ...overrides,
  }
}

/* -------------------------------------------------------------------------- */
/* Validation d'entrée                                                         */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — validation', () => {
  it('rejette sourceLocale === targetLocale', () => {
    assert.throws(
      () => buildMenuCopyPlan(baseMenu(), [makeItem()], 'fr', 'fr'),
      /doivent différer/,
    )
  })
})

/* -------------------------------------------------------------------------- */
/* Résolution de la valeur source (alignée avec extractMenuFields)             */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — résolution source', () => {
  it('utilise MenuI18n[sourceLocale].name s’il existe', () => {
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Base',
      i18n: [{ locale: 'fr', name: 'Menu FR explicite' }],
    }
    const plan = buildMenuCopyPlan(menu, [], 'fr', 'en')
    assert.equal(plan.menuI18nName, 'Menu FR explicite')
    assert.equal(plan.diagnostics.menuName, 'copied')
  })

  it('retombe sur Menu.name si MenuI18n[sourceLocale] absent', () => {
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Base FR',
      i18n: [],
    }
    const plan = buildMenuCopyPlan(menu, [], 'fr', 'en')
    assert.equal(plan.menuI18nName, 'Base FR')
  })

  it('utilise MenuItemI18n[sourceLocale].label s’il existe', () => {
    const item = makeItem({
      id: 'i1',
      baseLabel: 'Base',
      i18n: [{ locale: 'fr', label: 'Accueil FR explicite' }],
    })
    const plan = buildMenuCopyPlan(baseMenu(), [item], 'fr', 'en')
    assert.equal(plan.itemI18nLabelByItemId.get('i1'), 'Accueil FR explicite')
  })

  it('retombe sur baseLabel si MenuItemI18n[sourceLocale] absent', () => {
    const item = makeItem({ id: 'i1', baseLabel: 'Accueil base', i18n: [] })
    const plan = buildMenuCopyPlan(baseMenu(), [item], 'fr', 'en')
    assert.equal(plan.itemI18nLabelByItemId.get('i1'), 'Accueil base')
  })

  it('skip silencieux si la valeur source est vide après trim', () => {
    const item = makeItem({ id: 'i1', baseLabel: '   ', i18n: [] })
    const plan = buildMenuCopyPlan(baseMenu(), [item], 'fr', 'en')
    assert.equal(plan.itemI18nLabelByItemId.has('i1'), false)
    assert.deepEqual(plan.diagnostics.skippedEmptySource, ['i1'])
  })

  it('skip silencieux du nom si Menu.name vide après trim', () => {
    const menu: MenuInputForScan = { id: 'm', name: '   ', i18n: [] }
    const plan = buildMenuCopyPlan(menu, [], 'fr', 'en')
    assert.equal(plan.menuI18nName, undefined)
    assert.equal(plan.diagnostics.menuName, 'skippedEmptySource')
  })
})

/* -------------------------------------------------------------------------- */
/* Filtrage des items désactivés                                               */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — items désactivés', () => {
  it('ignore les items enabled: false', () => {
    const items = [
      makeItem({ id: 'on', baseLabel: 'Visible' }),
      makeItem({ id: 'off', enabled: false, baseLabel: 'Cachée' }),
    ]
    const plan = buildMenuCopyPlan(baseMenu(), items, 'fr', 'en')
    assert.equal(plan.itemI18nLabelByItemId.has('on'), true)
    assert.equal(plan.itemI18nLabelByItemId.has('off'), false)
    assert.deepEqual(plan.diagnostics.skippedDisabled, ['off'])
  })
})

/* -------------------------------------------------------------------------- */
/* Mode 'missing' (défaut, sûr)                                                */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — mode missing (défaut)', () => {
  it('préserve une traduction cible existante non vide', () => {
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Menu',
      i18n: [
        { locale: 'fr', name: 'Menu FR' },
        { locale: 'en', name: 'Existing EN translation' },
      ],
    }
    const item = makeItem({
      id: 'i1',
      baseLabel: 'Base',
      i18n: [
        { locale: 'fr', label: 'Accueil' },
        { locale: 'en', label: 'Home (already translated)' },
      ],
    })
    const plan = buildMenuCopyPlan(menu, [item], 'fr', 'en') // mode 'missing' par défaut
    assert.equal(plan.menuI18nName, undefined, 'menu i18n cible préservé')
    assert.equal(plan.diagnostics.menuName, 'skippedExisting')
    assert.equal(plan.itemI18nLabelByItemId.has('i1'), false, 'item i18n cible préservé')
    assert.deepEqual(plan.diagnostics.skippedExisting, ['i1'])
  })

  it('copie une traduction cible vide / blanc (considérée absente)', () => {
    const item = makeItem({
      id: 'i1',
      baseLabel: 'Accueil',
      i18n: [{ locale: 'en', label: '   ' }],
    })
    const plan = buildMenuCopyPlan(baseMenu(), [item], 'fr', 'en')
    assert.equal(plan.itemI18nLabelByItemId.get('i1'), 'Accueil')
    assert.deepEqual(plan.diagnostics.copied, ['i1'])
  })
})

/* -------------------------------------------------------------------------- */
/* Mode 'overwrite'                                                            */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — mode overwrite', () => {
  it('écrase les traductions cibles existantes', () => {
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Menu',
      i18n: [
        { locale: 'fr', name: 'Menu FR' },
        { locale: 'en', name: 'Old EN' },
      ],
    }
    const item = makeItem({
      id: 'i1',
      baseLabel: 'Base',
      i18n: [
        { locale: 'fr', label: 'Accueil' },
        { locale: 'en', label: 'Old translation' },
      ],
    })
    const plan = buildMenuCopyPlan(menu, [item], 'fr', 'en', 'overwrite')
    assert.equal(plan.menuI18nName, 'Menu FR', 'menu écrasé avec source FR')
    assert.equal(plan.itemI18nLabelByItemId.get('i1'), 'Accueil', 'item écrasé')
    assert.deepEqual(plan.diagnostics.copied, ['i1'])
    assert.equal(plan.diagnostics.menuName, 'copied')
  })
})

/* -------------------------------------------------------------------------- */
/* Cas réaliste : alignement avec workflow Pages/Footer                        */
/* -------------------------------------------------------------------------- */

describe('buildMenuCopyPlan — workflow réaliste', () => {
  it('copie FR → EN avec un menu vierge côté EN (cas typique « Étape 1 »)', () => {
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Menu principal',
      i18n: [{ locale: 'fr', name: 'Menu principal' }],
    }
    const items: MenuItemInputForScan[] = [
      makeItem({ id: 'i1', index: 0, baseLabel: 'Accueil' }),
      makeItem({ id: 'i2', index: 1, baseLabel: 'À propos' }),
      makeItem({ id: 'i3', index: 2, baseLabel: 'Solutions' }),
      makeItem({ id: 'i4', index: 3, enabled: false, baseLabel: 'Caché' }),
    ]
    const plan = buildMenuCopyPlan(menu, items, 'fr', 'en')

    assert.equal(plan.menuI18nName, 'Menu principal')
    assert.equal(plan.itemI18nLabelByItemId.size, 3)
    assert.equal(plan.itemI18nLabelByItemId.get('i1'), 'Accueil')
    assert.equal(plan.itemI18nLabelByItemId.get('i2'), 'À propos')
    assert.equal(plan.itemI18nLabelByItemId.get('i3'), 'Solutions')
    assert.equal(plan.itemI18nLabelByItemId.has('i4'), false)
    assert.deepEqual(plan.diagnostics.skippedDisabled, ['i4'])
  })

  it('cohérence avec extractMenuFields : les libellés copiés sont ceux qui seront scannés', async () => {
    const { extractMenuFields } = await import('@/lib/admin/menuCheckLanguage')
    const menu: MenuInputForScan = {
      id: 'm',
      name: 'Menu',
      i18n: [{ locale: 'fr', name: 'Menu FR' }],
    }
    const item = makeItem({
      id: 'i1',
      baseLabel: 'Accueil',
      i18n: [{ locale: 'fr', label: 'Accueil FR' }],
    })

    const plan = buildMenuCopyPlan(menu, [item], 'fr', 'en')
    const newMenu: MenuInputForScan = {
      ...menu,
      i18n: [...menu.i18n, { locale: 'en', name: plan.menuI18nName! }],
    }
    const newItem: MenuItemInputForScan = {
      ...item,
      i18n: [
        ...item.i18n,
        { locale: 'en', label: plan.itemI18nLabelByItemId.get('i1')! },
      ],
    }

    const fieldsAfterCopy = extractMenuFields(newMenu, [newItem], 'en')
    assert.equal(fieldsAfterCopy.length, 2)
    assert.equal(fieldsAfterCopy[0].value, 'Menu FR')
    assert.equal(fieldsAfterCopy[1].value, 'Accueil FR')
  })
})
