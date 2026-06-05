import { describe, expect, it } from 'vitest'

import { normalizePostTransactionWalletAsset } from '@/lib/portal/postTransactionWalletNav'

describe('postTransactionWalletNav', () => {
  it('normalizes wallet asset tickers', () => {
    expect(normalizePostTransactionWalletAsset('cbETH')).toBe('CBETH')
    expect(normalizePostTransactionWalletAsset(' usdc ')).toBe('USDC')
  })
})
