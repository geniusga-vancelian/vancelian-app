import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import { buildPortalWalletScopes } from '@/lib/portal/buildPortalWalletScopes'

describe('buildPortalWalletScopes', () => {
  it('lists connected wallets only — one Privy entry, no Solana duplicate', () => {
    const scopes = buildPortalWalletScopes({
      personWallets: [
        {
          id: 'privy-evm-id',
          address: '0x1111111111111111111111111111111111111111',
          provider: 'privy',
          chain_type: 'evm',
        },
      ],
      externalWallets: [
        {
          id: 'external-id',
          address: '0x2222222222222222222222222222222222222222',
          walletProvider: 'metamask',
          verifiedAt: '2026-01-01T00:00:00.000Z',
        },
      ],
    })

    assert.equal(scopes.length, 2)
    assert.ok(scopes.some((scope) => scope.id === 'privy:privy-evm-id'))
    assert.ok(scopes.some((scope) => scope.id === 'external:external-id'))
    assert.equal(
      scopes.filter((scope) => scope.kind === 'privy_embedded').length,
      1,
    )
  })
})
