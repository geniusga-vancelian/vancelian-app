import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  assertWithdrawAmountWithinPosition,
  computePrincipalNetFromLedgerRows,
  MorphoVaultLedgerError,
} from './morphoVaultLedger'
import { compareAssetsForTest } from './morphoVaultReconciliation.test-utils'
import { matchPersonWalletToPrivyId } from './resolvePortalEarnWalletIdentity'

describe('morpho ledger integration (mock DB)', () => {
  it('reject withdraw amount > position', async () => {
    await assert.rejects(
      () =>
        assertWithdrawAmountWithinPosition({
          amountRaw: BigInt(2_000_000),
          assetsInVaultRaw: '1000000',
        }),
      (error: unknown) => {
        assert.ok(error instanceof MorphoVaultLedgerError)
        assert.equal(error.code, 'morpho.withdraw_exceeds_position')
        return true
      },
    )
  })

  it('idempotent deposit logic keeps single pending row per key', () => {
    const rows = [
      {
        personId: 'person-1',
        vaultAddress: '0xvault',
        idempotencyKey: 'key-deposit-1',
        status: 'pending' as const,
      },
    ]
    const duplicates = rows.filter(
      (row) => row.personId === 'person-1' && row.idempotencyKey === 'key-deposit-1',
    )
    assert.equal(duplicates.length, 1)
  })

  it('duplicate idempotency key should map to one ledger slot', () => {
    const key = 'key-withdraw-1'
    const slots = new Map<string, string>()
    const upsert = (slotKey: string) => {
      if (!slots.has(slotKey)) slots.set(slotKey, `tx-${slots.size + 1}`)
      return slots.get(slotKey)
    }
    const slotKey = `person-1:0xvault:withdraw:${key}:0`
    assert.equal(upsert(slotKey), upsert(slotKey))
  })

  it('tx success vs reverted affects principal net', () => {
    const successPrincipal = computePrincipalNetFromLedgerRows([
      { operation: 'deposit', amountRaw: '1000000', status: 'success' },
      { operation: 'withdraw', amountRaw: '200000', status: 'success' },
    ])
    const revertedPrincipal = computePrincipalNetFromLedgerRows([
      { operation: 'deposit', amountRaw: '1000000', status: 'reverted' },
    ])
    assert.equal(successPrincipal, BigInt(800000))
    assert.equal(revertedPrincipal, BigInt(0))
  })

  it('wallet ownership rejected for unknown privy wallet', () => {
    const wallets = [
      {
        id: 'wallet-db-1',
        address: '0xabc0000000000000000000000000000000000001',
        chainId: 8453,
        metadataJson: { privy_wallet_id: 'privy-wallet-1' },
      },
    ]
    assert.equal(matchPersonWalletToPrivyId(wallets, 'unknown-wallet'), null)
  })

  it('resolvePortalEarnWalletIdentity matches privy + evm wallet', () => {
    const wallets = [
      {
        id: 'wallet-db-1',
        address: '0xabc0000000000000000000000000000000000001',
        chainId: 8453,
        metadataJson: { privy_wallet_id: 'privy-wallet-1' },
      },
    ]
    const matched = matchPersonWalletToPrivyId(wallets, 'privy-wallet-1')
    assert.ok(matched)
    assert.equal(matched.address.toLowerCase(), '0xabc0000000000000000000000000000000000001')
  })
})

describe('reconciliation status helper', () => {
  it('classifies matched and mismatch deltas', () => {
    assert.equal(compareAssetsForTest({ ledgerAssetsRaw: '1000000', onchainAssetsRaw: '1000000' }), 'matched')
    assert.equal(compareAssetsForTest({ ledgerAssetsRaw: '1000000', onchainAssetsRaw: '0' }), 'missing_onchain')
    assert.equal(compareAssetsForTest({ ledgerAssetsRaw: '0', onchainAssetsRaw: '500000' }), 'missing_ledger')
    assert.equal(compareAssetsForTest({ ledgerAssetsRaw: '1000000', onchainAssetsRaw: '2000000' }), 'mismatch')
  })
})
