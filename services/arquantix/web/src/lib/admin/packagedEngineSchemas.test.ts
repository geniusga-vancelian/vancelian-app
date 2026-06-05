import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  createLendingFromPackagedBodySchema,
  linkLendingBodySchema,
  linkVaultBodySchema,
} from './packagedEngineSchemas'

describe('packagedEngineSchemas', () => {
  it('create body accepts minimal valid payload', () => {
    const r = createLendingFromPackagedBodySchema.parse({
      borrower_client_id: '550e8400-e29b-41d4-a716-446655440000',
      asset: 'USDC',
      target_size: 1000,
    })
    assert.equal(r.target_size, 1000)
    assert.equal(r.supply_apr_bps, 300)
  })

  it('link body requires uuid', () => {
    assert.throws(() =>
      linkLendingBodySchema.parse({ lending_product_id: 'not-a-uuid' })
    )
    const r = linkLendingBodySchema.parse({
      lending_product_id: '550e8400-e29b-41d4-a716-446655440000',
    })
    assert.ok(r.lending_product_id)
  })

  it('link vault body requires portal_config_id', () => {
    assert.throws(() => linkVaultBodySchema.parse({ portal_config_id: '' }))
    const r = linkVaultBodySchema.parse({ portal_config_id: 'clxyz123vaultconfig' })
    assert.equal(r.portal_config_id, 'clxyz123vaultconfig')
  })
})
