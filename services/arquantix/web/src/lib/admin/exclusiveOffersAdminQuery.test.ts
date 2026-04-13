import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'

import { buildExclusiveOffersWhere, exclusiveOffersOrderBy } from './exclusiveOffersAdminQuery'

describe('exclusiveOffersAdminQuery', () => {
  it('buildExclusiveOffersWhere — base filtre type EO + template vault', () => {
    const w = buildExclusiveOffersWhere({})
    assert.equal((w.AND as unknown[]).length, 2)
    assert.deepEqual((w.AND as Record<string, unknown>[])[0], {
      productType: PackagedProductType.EXCLUSIVE_OFFER,
    })
    assert.deepEqual((w.AND as Record<string, unknown>[])[1], {
      page: { template: 'vault_builder' },
    })
  })

  it('buildExclusiveOffersWhere — recherche + commercial + visibility + engine', () => {
    const w = buildExclusiveOffersWhere({
      q: 'niseko',
      commercialStatus: PackagedCommercialStatus.PUBLISHED,
      visibility: PackagedVisibility.PUBLIC,
      engineLinked: 'linked',
    })
    const and = w.AND as Record<string, unknown>[]
    assert.ok(and.some((x) => 'OR' in x))
    assert.ok(and.some((x) => (x as { commercialStatus?: string }).commercialStatus === 'PUBLISHED'))
    assert.ok(and.some((x) => (x as { visibility?: string }).visibility === 'PUBLIC'))
    assert.ok(
      and.some(
        (x) =>
          (x as { lendingPoolProduct?: { isNot: null } }).lendingPoolProduct?.isNot === null
      )
    )
  })

  it('buildExclusiveOffersWhere — engine unlinked', () => {
    const w = buildExclusiveOffersWhere({ engineLinked: 'unlinked' })
    const and = w.AND as Record<string, unknown>[]
    assert.ok(
      and.some(
        (x) => (x as { lendingPoolProduct?: null }).lendingPoolProduct === null
      )
    )
  })

  it('exclusiveOffersOrderBy', () => {
    assert.deepEqual(exclusiveOffersOrderBy('updated_desc'), [{ updatedAt: 'desc' }])
    assert.deepEqual(exclusiveOffersOrderBy('featured_asc'), [
      { featuredRank: 'asc' },
      { updatedAt: 'desc' },
    ])
  })
})
