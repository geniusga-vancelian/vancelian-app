import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

process.env.NODE_ENV = 'test'
process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'
process.env.EXTERNAL_WALLET_LOCAL_MOCK_ENABLED = 'true'

import { buildWalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'
import {
  generateMockExternalWalletTxHash,
  isLocalMockExternalWallet,
  isLocalMockExternalWalletAddress,
  LOCAL_MOCK_EXTERNAL_WALLET,
} from '@/lib/wallet/externalWalletMock'
import {
  isExternalWalletLocalMockEnabled,
  isExternalWalletMockDevRouteAvailable,
} from '@/lib/wallet/externalWalletMockConfig'
import { isLifiLocalSandboxEnabled } from '@/lib/wallet/lifiLocalSandboxConfig'

describe('external wallet local mock config', () => {
  it('mock enabled in test env with morpho sandbox', () => {
    assert.equal(isExternalWalletLocalMockEnabled(), true)
    assert.equal(isExternalWalletMockDevRouteAvailable(), true)
  })

  it('mock disabled in production', () => {
    const prevNode = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    try {
      assert.equal(isExternalWalletMockDevRouteAvailable(), false)
    } finally {
      process.env.NODE_ENV = prevNode
    }
  })

  it('mock disabled without sandbox parent flag', () => {
    const prevMorpho = process.env.MORPHO_LOCAL_SANDBOX_ENABLED
    const prevLifi = process.env.LIFI_LOCAL_SANDBOX_ENABLED
    process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'false'
    process.env.LIFI_LOCAL_SANDBOX_ENABLED = 'false'
    try {
      assert.equal(isExternalWalletLocalMockEnabled(), false)
    } finally {
      process.env.MORPHO_LOCAL_SANDBOX_ENABLED = prevMorpho
      process.env.LIFI_LOCAL_SANDBOX_ENABLED = prevLifi
    }
  })

  it('mock enabled with lifi sandbox only', () => {
    const prevMorpho = process.env.MORPHO_LOCAL_SANDBOX_ENABLED
    const prevLifi = process.env.LIFI_LOCAL_SANDBOX_ENABLED
    process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'false'
    process.env.LIFI_LOCAL_SANDBOX_ENABLED = 'true'
    try {
      assert.equal(isLifiLocalSandboxEnabled(), true)
      assert.equal(isExternalWalletLocalMockEnabled(), true)
    } finally {
      process.env.MORPHO_LOCAL_SANDBOX_ENABLED = prevMorpho
      process.env.LIFI_LOCAL_SANDBOX_ENABLED = prevLifi
    }
  })
})

describe('external wallet mock helpers', () => {
  it('expose stable mock wallet constants', () => {
    assert.equal(LOCAL_MOCK_EXTERNAL_WALLET.address, '0x1111111111111111111111111111111111111111')
    assert.equal(LOCAL_MOCK_EXTERNAL_WALLET.connector, 'local_mock')
    assert.equal(LOCAL_MOCK_EXTERNAL_WALLET.isVerified, true)
  })

  it('detects local mock wallet address', () => {
    assert.equal(isLocalMockExternalWalletAddress(LOCAL_MOCK_EXTERNAL_WALLET.address), true)
    assert.equal(isLocalMockExternalWalletAddress('0xabc'), false)
  })

  it('generates fake tx hash prefixed with 0xmocked', () => {
    const hash = generateMockExternalWalletTxHash()
    assert.match(hash, /^0xmocked[0-9a-f]+$/)
  })

  it('marks execution wallet metadata for local mock external wallet', () => {
    const wallet = {
      type: 'external_evm' as const,
      address: LOCAL_MOCK_EXTERNAL_WALLET.address,
      externalWalletId: 'mock-wallet-id',
      connector: 'local_mock' as const,
    }
    assert.equal(isLocalMockExternalWallet(wallet), true)
    const metadata = buildWalletSourceMetadata(wallet)
    assert.equal(metadata.wallet_source, 'external_evm')
    assert.equal(metadata.wallet_provider, 'local_mock')
    assert.equal(metadata.external_wallet_id, 'mock-wallet-id')
  })

  it('does not treat real metamask wallet as local mock', () => {
    assert.equal(
      isLocalMockExternalWallet({
        type: 'external_evm',
        address: '0x0000000000000000000000000000000000000001',
        externalWalletId: 'w1',
        connector: 'metamask',
      }),
      false,
    )
  })
})

describe('external wallet mock tx signer contract', () => {
  it('local mock wallet bypasses wagmi/reown requirement by design', () => {
    const wallet = {
      type: 'external_evm' as const,
      address: LOCAL_MOCK_EXTERNAL_WALLET.address,
      externalWalletId: 'mock-wallet-id',
      connector: 'local_mock' as const,
    }
    assert.equal(isLocalMockExternalWallet(wallet), true)
    const hash = generateMockExternalWalletTxHash()
    assert.match(hash, /^0xmocked/)
  })
})
