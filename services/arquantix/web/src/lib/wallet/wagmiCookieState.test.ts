import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { decodeWagmiCookieHeader } from '@/lib/wallet/wagmiCookieHeader'

describe('wagmiCookieState', () => {
  it('decodeWagmiCookieHeader decodes URL-encoded wagmi.store value', () => {
    const encoded = 'wagmi.store=%7B%22state%22%3A%7B%7D%7D'
    const decoded = decodeWagmiCookieHeader(encoded)
    assert.equal(decoded, 'wagmi.store={"state":{}}')
  })
})
