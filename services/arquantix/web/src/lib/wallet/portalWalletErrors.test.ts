import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  formatPortalWalletError,
  isPortalWalletRequestExpiredError,
  isPortalWalletUserRejectedError,
} from '@/lib/wallet/portalWalletErrors'

describe('portalWalletErrors', () => {
  it('detects MetaMask request expired errors', () => {
    const error = new Error('An unknown RPC error occurred. Details: Request expired. Please try again.')
    assert.equal(isPortalWalletRequestExpiredError(error), true)
    assert.match(
      formatPortalWalletError(error, { walletMode: 'external_evm', chainId: 8453, assetSymbol: 'USDC' }),
      /MetaMask n’a pas reçu votre signature/,
    )
  })

  it('detects user rejected errors', () => {
    const error = new Error('User rejected the request.')
    assert.equal(isPortalWalletUserRejectedError(error), true)
    assert.match(formatPortalWalletError(error, { walletMode: 'privy_embedded' }), /wallet Vancelian/)
  })

  it('maps execution reverted to contextual approve guidance for Privy', () => {
    const error = new Error('Execution reverted for an unknown reason. Details: execution reverted')
    assert.match(
      formatPortalWalletError(error, {
        walletMode: 'privy_embedded',
        chainId: 8453,
        phase: 'approve',
        assetSymbol: 'USDC',
      }),
      /Approbation USDC impossible sur Base/,
    )
  })
})
