/**
 * @see projectExclusiveOfferGuards.ts
 */
import assert from 'node:assert/strict'
import { describe, it, afterEach } from 'node:test'

import { isProjectBasedExclusiveOfferCreationBlocked } from './projectExclusiveOfferGuards'

describe('isProjectBasedExclusiveOfferCreationBlocked', () => {
  const prevBlock = process.env.ADMIN_BLOCK_PROJECT_BASED_EO
  const prevAllow = process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO

  afterEach(() => {
    if (prevBlock === undefined) delete process.env.ADMIN_BLOCK_PROJECT_BASED_EO
    else process.env.ADMIN_BLOCK_PROJECT_BASED_EO = prevBlock
    if (prevAllow === undefined) delete process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO
    else process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO = prevAllow
  })

  it('blocked when BLOCK true and ALLOW unset', () => {
    delete process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO
    process.env.ADMIN_BLOCK_PROJECT_BASED_EO = 'true'
    assert.equal(isProjectBasedExclusiveOfferCreationBlocked(), true)
  })

  it('not blocked when ALLOW legacy true', () => {
    process.env.ADMIN_BLOCK_PROJECT_BASED_EO = 'true'
    process.env.ADMIN_ALLOW_LEGACY_PROJECT_BASED_EO = 'true'
    assert.equal(isProjectBasedExclusiveOfferCreationBlocked(), false)
  })
})
