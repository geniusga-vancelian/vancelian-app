import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  VANCELIAN_AXBALI_VAULT,
  VANCELIAN_AXDUBAI_VAULT,
  VANCELIAN_VFEUR_VAULT,
} from '@/lib/portal/ledgity/ledgityConstants'
import {
  isExclusiveOfferLockedVault,
  isLedgityVaultLockActive,
  resolveLedgityVaultProfile,
  resolveLedgityVaultWithdrawMode,
} from '@/lib/portal/ledgity/ledgityVaultProfiles'

describe('resolveLedgityVaultProfile', () => {
  it('classifie axDUBAI et axBALI en offre exclusive lock-up', () => {
    assert.equal(resolveLedgityVaultProfile(VANCELIAN_AXDUBAI_VAULT), 'exclusive_offer_locked')
    assert.equal(resolveLedgityVaultProfile(VANCELIAN_AXBALI_VAULT), 'exclusive_offer_locked')
  })

  it('classifie vfEUR en coffre flexible', () => {
    assert.equal(resolveLedgityVaultProfile(VANCELIAN_VFEUR_VAULT), 'flexible')
  })
})

describe('exclusive offer lock-up policy', () => {
  const now = BigInt(1_700_000_000)
  const future = now + BigInt(365 * 24 * 3600)
  const past = now - BigInt(24 * 3600)

  it('bloque les retraits pendant le lock (club deal)', () => {
    assert.equal(
      resolveLedgityVaultWithdrawMode({
        profile: 'exclusive_offer_locked',
        operationEndDateUnix: future,
        nowUnix: now,
      }),
      'blocked',
    )
    assert.equal(
      isLedgityVaultLockActive({
        profile: 'exclusive_offer_locked',
        operationEndDateUnix: future,
        nowUnix: now,
      }),
      true,
    )
  })

  it('autorise la demande async après maturité', () => {
    assert.equal(
      resolveLedgityVaultWithdrawMode({
        profile: 'exclusive_offer_locked',
        operationEndDateUnix: past,
        nowUnix: now,
      }),
      'async_request',
    )
  })

  it('bloque aussi quand la maturité on-chain n’est pas encore publiée', () => {
    assert.equal(
      resolveLedgityVaultWithdrawMode({
        profile: 'exclusive_offer_locked',
        operationEndDateUnix: null,
        nowUnix: now,
      }),
      'blocked',
    )
    assert.equal(isExclusiveOfferLockedVault(VANCELIAN_AXDUBAI_VAULT), true)
  })
})
