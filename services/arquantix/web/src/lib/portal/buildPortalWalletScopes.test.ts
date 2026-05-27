import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildEmbeddedVancelianWalletScope,
  buildPortalWalletScopes,
  buildSwitchablePortalWalletScopes,
} from '@/lib/portal/buildPortalWalletScopes'

const PRIVY_EVM = {
  id: 'privy-evm-id',
  address: '0x1111111111111111111111111111111111111111',
  provider: 'privy',
  chain_type: 'evm',
} as const

const EXTERNAL = {
  id: 'external-id',
  address: '0x2222222222222222222222222222222222222222',
  walletProvider: 'metamask' as const,
  verifiedAt: '2026-01-01T00:00:00.000Z',
}

describe('buildPortalWalletScopes', () => {
  it('embedded scope — Wallet crypto, pas de libellé Privy', () => {
    const embedded = buildEmbeddedVancelianWalletScope([PRIVY_EVM])
    assert.ok(embedded)
    assert.equal(embedded.id, 'privy:privy-evm-id')
    assert.equal(embedded.label, 'Wallet crypto')
    assert.equal(embedded.shortLabel, 'Crypto')
    assert.equal(embedded.kind, 'privy_embedded')
  })

  it('switchable scopes — externes uniquement', () => {
    const switchable = buildSwitchablePortalWalletScopes({ externalWallets: [EXTERNAL] })
    assert.equal(switchable.length, 1)
    assert.equal(switchable[0]?.id, 'external:external-id')
    assert.equal(switchable[0]?.kind, 'external_evm')
  })

  it('buildPortalWalletScopes — rétrocompat embedded + externes', () => {
    const scopes = buildPortalWalletScopes({
      personWallets: [PRIVY_EVM],
      externalWallets: [EXTERNAL],
    })
    assert.equal(scopes.length, 2)
    assert.ok(scopes.some((scope) => scope.id === 'privy:privy-evm-id'))
    assert.ok(scopes.some((scope) => scope.id === 'external:external-id'))
  })
})
