import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { resolvePrivyEmbeddedWalletId } from '@/lib/portal/resolvePrivyEmbeddedWalletId'

describe('resolvePrivyEmbeddedWalletId', () => {
  it('reads privy wallet id from linked accounts', () => {
    const id = resolvePrivyEmbeddedWalletId({
      user: {
        linkedAccounts: [
          {
            type: 'wallet',
            address: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
            walletClientType: 'privy',
            id: 'wallet-id-abc',
          },
        ],
      } as never,
      wallets: [],
      walletAddress: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
    })
    assert.equal(id, 'wallet-id-abc')
  })

  it('returns null when no embedded wallet matches', () => {
    const id = resolvePrivyEmbeddedWalletId({
      user: { linkedAccounts: [] } as never,
      wallets: [],
      walletAddress: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
    })
    assert.equal(id, null)
  })
})
