import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildPackagedPutBodyFromDraft,
  packagedProductByPagePutSchema,
  parseTagsInput,
} from './packagedProductSchemas'

describe('packagedProductSchemas', () => {
  it('parseTagsInput splits commas and newlines and dedupes', () => {
    assert.deepEqual(parseTagsInput('a, b \n a'), ['a', 'b'])
    assert.deepEqual(parseTagsInput(''), [])
  })

  it('PUT schema: disabled sends only enabled flag', () => {
    const r = packagedProductByPagePutSchema.parse({ enabled: false })
    assert.equal(r.enabled, false)
  })

  it('PUT schema: enabled requires slug and productType', () => {
    assert.throws(() =>
      packagedProductByPagePutSchema.parse({
        enabled: true,
        productType: 'VAULT_SIMPLE',
      })
    )
    assert.throws(() =>
      packagedProductByPagePutSchema.parse({
        enabled: true,
        slug: 'ok-slug',
      })
    )
  })

  it('PUT schema: enabled accepts minimal valid payload', () => {
    const r = packagedProductByPagePutSchema.parse({
      enabled: true,
      slug: 'my-offer',
      productType: 'EXCLUSIVE_OFFER',
      commercialStatus: 'DRAFT',
      visibility: 'PUBLIC',
      tags: ['x'],
    })
    assert.equal(r.slug, 'my-offer')
    assert.equal(r.productType, 'EXCLUSIVE_OFFER')
  })

  it('buildPackagedPutBodyFromDraft: toggle off yields parseable minimal body', () => {
    const body = buildPackagedPutBodyFromDraft({
      enabled: false,
      slug: '',
      productType: 'VAULT_SIMPLE',
      commercialStatus: 'DRAFT',
      visibility: 'PUBLIC',
      featuredRank: '',
      categorySlug: '',
      tagsText: '',
    })
    packagedProductByPagePutSchema.parse(body)
    assert.equal(body.enabled, false)
  })

  it('buildPackagedPutBodyFromDraft: toggle on builds full payload', () => {
    const body = buildPackagedPutBodyFromDraft({
      enabled: true,
      slug: 'test-slug',
      productType: 'VAULT_SIMPLE',
      commercialStatus: 'PUBLISHED',
      visibility: 'HIDDEN',
      featuredRank: '42',
      categorySlug: 'crypto',
      tagsText: 'a, b',
    })
    assert.equal(body.enabled, true)
    assert.equal(body.slug, 'test-slug')
    assert.equal(body.featuredRank, 42)
    assert.deepEqual(body.tags, ['a', 'b'])
  })
})
