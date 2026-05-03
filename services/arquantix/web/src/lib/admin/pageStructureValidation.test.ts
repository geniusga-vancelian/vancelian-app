import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  mustStayStructuralRoot,
  newParentWouldCreateCycle,
  parentCannotBeVaultTemplate,
} from './pageStructureValidation'

describe('pageStructureValidation', () => {
  it('newParentWouldCreateCycle — détecte un ancêtre qui est la page déplacée', () => {
    const m = new Map<string, string | null>([
      ['a', null],
      ['b', 'a'],
      ['c', 'b'],
    ])
    assert.equal(newParentWouldCreateCycle('a', 'c', m), true)
    assert.equal(newParentWouldCreateCycle('b', 'c', m), true)
    assert.equal(newParentWouldCreateCycle('c', 'a', m), false)
  })

  it('mustStayStructuralRoot — home et projects', () => {
    assert.equal(mustStayStructuralRoot({ slug: 'home', pageRole: 'STANDARD' }), true)
    assert.equal(mustStayStructuralRoot({ slug: 'projects', pageRole: 'STANDARD' }), true)
    assert.equal(mustStayStructuralRoot({ slug: 'x', pageRole: 'HOME' }), true)
    assert.equal(mustStayStructuralRoot({ slug: 'x', pageRole: 'PROJECTS_HUB' }), true)
    assert.equal(mustStayStructuralRoot({ slug: 'about', pageRole: 'STANDARD' }), false)
  })

  it('parentCannotBeVaultTemplate', () => {
    assert.equal(parentCannotBeVaultTemplate('vault_builder'), true)
    assert.equal(parentCannotBeVaultTemplate('homepage'), false)
  })
})
