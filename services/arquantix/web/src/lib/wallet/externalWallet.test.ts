import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { privateKeyToAccount } from 'viem/accounts'
import { verifyMessage } from 'viem'

import {
  buildWalletSourceMetadata,
  readExecutionWalletSource,
} from '@/lib/wallet/executionWalletTypes'
import { buildExternalWalletVerificationMessage } from '@/lib/wallet/externalWalletVerification'

describe('external wallet verification message', () => {
  it('construit un message stable avec person_id et nonce', () => {
    const message = buildExternalWalletVerificationMessage({
      personId: '550e8400-e29b-41d4-a716-446655440000',
      nonce: 'abc123',
      timestamp: '2026-05-25T12:00:00.000Z',
    })
    assert.match(message, /Person ID: 550e8400-e29b-41d4-a716-446655440000/)
    assert.match(message, /Nonce: abc123/)
    assert.match(message, /Timestamp: 2026-05-25T12:00:00.000Z/)
  })
})

describe('execution wallet metadata', () => {
  it('marque un wallet externe dans le ledger', () => {
    const metadata = buildWalletSourceMetadata({
      type: 'external_evm',
      address: '0x0000000000000000000000000000000000000001',
      externalWalletId: 'wallet-1',
      connector: 'metamask',
    })
    assert.equal(metadata.wallet_source, 'external_evm')
    assert.equal(metadata.external_wallet_id, 'wallet-1')
    assert.equal(readExecutionWalletSource(metadata), 'external_evm')
  })

  it('marque un wallet privy embedded', () => {
    const metadata = buildWalletSourceMetadata({
      type: 'privy_embedded',
      address: '0x0000000000000000000000000000000000000002',
    })
    assert.equal(metadata.wallet_source, 'privy_embedded')
    assert.equal(readExecutionWalletSource(metadata), 'privy_embedded')
  })
})

describe('signature verify (unit)', () => {
  it('accepte une signature valide pour le message de vérification', async () => {
    const account = privateKeyToAccount(
      '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
    )
    const message = buildExternalWalletVerificationMessage({
      personId: '550e8400-e29b-41d4-a716-446655440000',
      nonce: 'deadbeef',
      timestamp: '2026-05-25T12:00:00.000Z',
    })
    const signature = await account.signMessage({ message })
    const valid = await verifyMessage({
      address: account.address,
      message,
      signature,
    })
    assert.equal(valid, true)
  })

  it('rejette une signature invalide', async () => {
    const account = privateKeyToAccount(
      '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80',
    )
    const message = buildExternalWalletVerificationMessage({
      personId: '550e8400-e29b-41d4-a716-446655440000',
      nonce: 'deadbeef',
      timestamp: '2026-05-25T12:00:00.000Z',
    })
    const signature = await account.signMessage({ message })
    const corrupted = `${signature.slice(0, -4)}0000` as `0x${string}`
    const valid = await verifyMessage({
      address: account.address,
      message,
      signature: corrupted,
    })
    assert.equal(valid, false)
  })
})
