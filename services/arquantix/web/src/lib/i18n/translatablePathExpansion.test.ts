import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { expandTranslatablePaths } from './translatablePathExpansion'

describe('expandTranslatablePaths — chemins simples', () => {
  it('renvoie le chemin tel quel si pas de wildcard', () => {
    assert.deepEqual(
      expandTranslatablePaths({ title: 'Hello' }, 'title'),
      ['title'],
    )
  })

  it('renvoie quand même le chemin si la clé est absente (responsabilité au consommateur)', () => {
    // Conséquence : `getStringAtLot1Path` renverra `undefined`, le scan
    // ignorera silencieusement ; le ground-truth test garantit la couverture.
    assert.deepEqual(
      expandTranslatablePaths({}, 'title'),
      ['title'],
    )
  })

  it('gère un chemin imbriqué sans `[]`', () => {
    assert.deepEqual(
      expandTranslatablePaths({ ui: { title: 'X' } }, 'ui.title'),
      ['ui.title'],
    )
  })
})

describe('expandTranslatablePaths — un seul `[]`', () => {
  it('expanse `items[].title` selon la longueur du tableau', () => {
    const data = { items: [{ title: 'A' }, { title: 'B' }, { title: 'C' }] }
    assert.deepEqual(
      expandTranslatablePaths(data, 'items[].title'),
      ['items[0].title', 'items[1].title', 'items[2].title'],
    )
  })

  it('renvoie `[]` si le tableau est vide', () => {
    assert.deepEqual(
      expandTranslatablePaths({ items: [] }, 'items[].title'),
      [],
    )
  })

  it('renvoie `[]` si la clé n\'est pas un tableau', () => {
    assert.deepEqual(
      expandTranslatablePaths({ items: 'oups' }, 'items[].title'),
      [],
    )
  })

  it('renvoie `[]` si la clé est absente', () => {
    assert.deepEqual(
      expandTranslatablePaths({}, 'items[].title'),
      [],
    )
  })
})

describe('expandTranslatablePaths — array de strings (`tags[]`)', () => {
  it('expanse `tags[]` en index scalaire — fix régression `translateSectionData`', () => {
    // C'est exactement le cas que l'ancien `translateSectionData` ratait :
    // `typeof item === 'object'` était false pour des strings.
    const data = { tags: ['premium', 'exclusive', 'reserved'] }
    assert.deepEqual(
      expandTranslatablePaths(data, 'tags[]'),
      ['tags[0]', 'tags[1]', 'tags[2]'],
    )
  })

  it('renvoie `[]` si le tableau de strings est vide', () => {
    assert.deepEqual(
      expandTranslatablePaths({ tags: [] }, 'tags[]'),
      [],
    )
  })
})

describe('expandTranslatablePaths — multi-`[]` (imbrication)', () => {
  it('expanse `items[].tags[]` (objet > array de strings)', () => {
    const data = {
      items: [
        { title: 'A', tags: ['x', 'y'] },
        { title: 'B', tags: [] },
        { title: 'C', tags: ['z'] },
      ],
    }
    assert.deepEqual(
      expandTranslatablePaths(data, 'items[].tags[]'),
      ['items[0].tags[0]', 'items[0].tags[1]', 'items[2].tags[0]'],
    )
  })

  it('expanse `cards[].buttons[].label` (deux niveaux d\'objets)', () => {
    const data = {
      cards: [
        { buttons: [{ label: 'X' }, { label: 'Y' }] },
        { buttons: [{ label: 'Z' }] },
      ],
    }
    assert.deepEqual(
      expandTranslatablePaths(data, 'cards[].buttons[].label'),
      [
        'cards[0].buttons[0].label',
        'cards[0].buttons[1].label',
        'cards[1].buttons[0].label',
      ],
    )
  })

  it('renvoie `[]` si un sous-tableau est manquant', () => {
    const data = { cards: [{ buttons: 'oups' }] }
    assert.deepEqual(
      expandTranslatablePaths(data, 'cards[].buttons[].label'),
      [],
    )
  })
})

describe('expandTranslatablePaths — robustesse', () => {
  it('ne mute pas la donnée d\'entrée', () => {
    const data = { items: [{ title: 'A' }] }
    const snapshot = JSON.parse(JSON.stringify(data))
    expandTranslatablePaths(data, 'items[].title')
    assert.deepEqual(data, snapshot)
  })

  it('gère `data` non-objet sans planter', () => {
    assert.deepEqual(expandTranslatablePaths(null, 'items[].title'), [])
    assert.deepEqual(expandTranslatablePaths(undefined, 'items[].title'), [])
    assert.deepEqual(expandTranslatablePaths(42, 'items[].title'), [])
  })
})
