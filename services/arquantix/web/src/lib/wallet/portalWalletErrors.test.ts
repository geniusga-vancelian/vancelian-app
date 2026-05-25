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
    assert.match(formatPortalWalletError(error), /MetaMask n’a pas reçu votre signature/)
  })

  it('detects user rejected errors', () => {
    const error = new Error('User rejected the request.')
    assert.equal(isPortalWalletUserRejectedError(error), true)
    assert.match(formatPortalWalletError(error), /refusée/)
  })
})
