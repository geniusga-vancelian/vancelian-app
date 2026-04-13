/**
 * @see verifyExclusiveOfferRegistry.ts
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { verifyPackagedProductPageAndSlug } from './verifyExclusiveOfferRegistry'

describe('verifyPackagedProductPageAndSlug', () => {
  it('flags empty slug', () => {
    const a = verifyPackagedProductPageAndSlug({
      id: 'p1',
      slug: '',
      productType: 'EXCLUSIVE_OFFER',
      page: { id: 'pg', slug: 'x', template: 'vault_builder' },
    })
    assert.ok(a.some((x) => x.code === 'EMPTY_SLUG'))
  })

  it('flags non-vault page template', () => {
    const a = verifyPackagedProductPageAndSlug({
      id: 'p1',
      slug: 'ok-slug',
      productType: 'EXCLUSIVE_OFFER',
      page: { id: 'pg', slug: 'x', template: 'homepage' },
    })
    assert.ok(a.some((x) => x.code === 'PAGE_NOT_VAULT_BUILDER'))
  })

  it('passes for vault_builder page', () => {
    const a = verifyPackagedProductPageAndSlug({
      id: 'p1',
      slug: 'ok-slug',
      productType: 'EXCLUSIVE_OFFER',
      page: { id: 'pg', slug: 'x', template: 'vault_builder' },
    })
    assert.equal(a.length, 0)
  })
})
