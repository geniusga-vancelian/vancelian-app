import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { resolveOwnedPrivyWallet } from './portalWalletOwnership'

describe('resolveOwnedPrivyWallet', () => {
  const wallets = [
    {
      id: 'wallet-db-1',
      address: '0xabc0000000000000000000000000000000000001',
      metadataJson: { privy_wallet_id: 'privy-wallet-1' },
    },
    {
      id: 'wallet-db-2',
      address: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
      metadataJson: null,
    },
  ]

  it('matches privy wallet id from metadata', () => {
    const matched = resolveOwnedPrivyWallet({
      wallets,
      privyWalletId: 'privy-wallet-1',
    })
    assert.ok(matched)
    assert.equal(matched.id, 'wallet-db-1')
  })

  it('falls back to EVM address when privy id missing in metadata', () => {
    const matched = resolveOwnedPrivyWallet({
      wallets,
      privyWalletId: 'svbeyhtpw8317205byhv04ns',
      walletAddress: '0x7ae683c429ec2bC66BF1eB93713B5644dd265A44',
    })
    assert.ok(matched)
    assert.equal(matched.id, 'wallet-db-2')
  })

  it('rejects unknown wallet without address fallback', () => {
    const matched = resolveOwnedPrivyWallet({
      wallets,
      privyWalletId: 'unknown-wallet',
    })
    assert.equal(matched, null)
  })
})
