import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { layoutMegaMenuColumns } from '@/lib/menu/buildMegaMenuColumns'

function item(
  id: string,
  title: string,
  category: string,
): Parameters<typeof layoutMegaMenuColumns>[0][number] {
  return {
    id,
    title,
    description: 'd',
    href: `/${id}`,
    category,
  }
}

describe('layoutMegaMenuColumns', () => {
  it('retourne [] si moins de 2 items', () => {
    assert.deepEqual(layoutMegaMenuColumns([item('a', 'A', '')]), [])
  })

  it('2 colonnes par défaut sans catégories distinctes', () => {
    const cols = layoutMegaMenuColumns([
      item('1', 'A', ''),
      item('2', 'B', ''),
      item('3', 'C', ''),
    ])
    assert.equal(cols.length, 2)
    assert.equal(cols[0].items.length, 2)
    assert.equal(cols[1].items.length, 1)
    assert.equal(cols[0].category, undefined)
  })

  it('1 colonne par catégorie si ≥ 2 catégories non vides', () => {
    const cols = layoutMegaMenuColumns([
      item('1', 'A', 'Alpha'),
      item('2', 'B', 'Beta'),
      item('3', 'C', 'Alpha'),
    ])
    const labeled = cols.filter((c) => c.category)
    assert.ok(labeled.length >= 2)
    assert.ok(cols.some((c) => c.category === 'Alpha'))
    assert.ok(cols.some((c) => c.category === 'Beta'))
  })

  it('items sans catégorie regroupés en tête si multi-catégories', () => {
    const cols = layoutMegaMenuColumns([
      item('1', 'U', ''),
      item('2', 'A', 'CatA'),
      item('3', 'B', 'CatB'),
    ])
    assert.equal(cols[0].category, undefined)
    assert.equal(cols[0].items.length, 1)
    assert.equal(cols[0].items[0].id, '1')
  })
})
