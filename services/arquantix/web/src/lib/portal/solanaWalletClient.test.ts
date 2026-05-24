import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  parseSolanaWalletPayload,
  parseSolanaWalletStatus,
  resolveSolanaExplorerAddressUrl,
  resolveSolanaWalletUiState,
} from './solanaWalletClient'

describe('parseSolanaWalletPayload', () => {
  it('parses a valid Solana wallet response', () => {
    const wallet = parseSolanaWalletPayload({
      chain_type: 'solana',
      address: '9wtGmqMamnKfz49XBwnJASbjcVnnKnT78qKopCL54TAk',
      wallet_id: 'privy-wallet-sol-1',
      created: true,
      person_wallet_id: '881d952b-f7ae-4cc3-ac06-232fa02644b7',
    })
    assert.ok(wallet)
    assert.equal(wallet?.address, '9wtGmqMamnKfz49XBwnJASbjcVnnKnT78qKopCL54TAk')
    assert.equal(wallet?.created, true)
  })
})

describe('parseSolanaWalletStatus', () => {
  it('parses unlinked status from Privy', () => {
    const status = parseSolanaWalletStatus({
      status: 'unlinked',
      chain_type: 'solana',
      address: 'G3LsoYMqDp3NAEHG5DQT9SB3JfouXH9heUGLLmHLd6QR',
      wallet_id: 'dbopru0h1r0zuziges29io5k',
      created: false,
    })
    assert.equal(status?.status, 'unlinked')
    assert.equal(status?.address, 'G3LsoYMqDp3NAEHG5DQT9SB3JfouXH9heUGLLmHLd6QR')
  })
})

describe('resolveSolanaWalletUiState', () => {
  it('shows loading then ready address', () => {
    assert.equal(resolveSolanaWalletUiState({ loading: true, error: '', walletStatus: null }).status, 'loading')

    const ready = resolveSolanaWalletUiState({
      loading: false,
      error: '',
      walletStatus: {
        status: 'linked',
        chain_type: 'solana',
        address: '9wtGmqMamnKfz49XBwnJASbjcVnnKnT78qKopCL54TAk',
        wallet_id: 'w1',
        person_wallet_id: 'p1',
        created: false,
      },
    })
    assert.equal(ready.status, 'ready')
    if (ready.status === 'ready') {
      assert.match(ready.wallet.address, /^9wtG/)
    }
  })

  it('shows link CTA when wallet exists on Privy only', () => {
    const unlinked = resolveSolanaWalletUiState({
      loading: false,
      error: '',
      walletStatus: {
        status: 'unlinked',
        chain_type: 'solana',
        address: 'G3LsoYMqDp3NAEHG5DQT9SB3JfouXH9heUGLLmHLd6QR',
        wallet_id: 'dbopru0h1r0zuziges29io5k',
        created: false,
      },
    })
    assert.equal(unlinked.status, 'unlinked')
  })

  it('shows create CTA when wallet is missing', () => {
    const missing = resolveSolanaWalletUiState({
      loading: false,
      error: '',
      walletStatus: { status: 'missing', chain_type: 'solana', created: false },
    })
    assert.equal(missing.status, 'missing')
  })
})

describe('resolveSolanaExplorerAddressUrl', () => {
  it('builds a Solscan URL', () => {
    assert.match(
      resolveSolanaExplorerAddressUrl('G3LsoYMqDp3NAEHG5DQT9SB3JfouXH9heUGLLmHLd6QR'),
      /solscan\.io\/account\/G3Lso/,
    )
  })
})
