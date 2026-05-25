import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildSwapSigningWalletQuoteParams,
  formatSwapSigningWalletShort,
} from '@/lib/portal/swapSigningWallet'

describe('swapSigningWallet', () => {
  it('builds privy params without address', () => {
    const params = buildSwapSigningWalletQuoteParams({
      mode: 'privy_embedded',
      privyEmbeddedAddress: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
      externalWalletAddress: null,
    })
    assert.equal(params.signing_wallet_mode, 'privy_embedded')
    assert.equal(params.signing_wallet_address, undefined)
  })

  it('builds external params with verified address', () => {
    const addr = '0x1234567890123456789012345678901234567890'
    const params = buildSwapSigningWalletQuoteParams({
      mode: 'external_evm',
      privyEmbeddedAddress: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
      externalWalletAddress: addr,
    })
    assert.equal(params.signing_wallet_mode, 'external_evm')
    assert.equal(params.signing_wallet_address, addr)
  })

  it('formats short address', () => {
    assert.equal(
      formatSwapSigningWalletShort('0x1234567890123456789012345678901234567890'),
      '0x1234…7890',
    )
  })
})
