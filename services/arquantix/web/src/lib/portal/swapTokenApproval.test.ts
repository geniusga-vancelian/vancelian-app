import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildSwapApproveTransaction,
  isSwapTokenApprovalRequired,
} from '@/lib/portal/swapTokenApproval'

describe('swapTokenApproval', () => {
  it('detects required approval payload', () => {
    assert.equal(
      isSwapTokenApprovalRequired({
        required: true,
        token_address: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        spender_address: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',
        amount_atomic: '10000000',
      }),
      true,
    )
  })

  it('skips native token approval', () => {
    assert.equal(
      isSwapTokenApprovalRequired({
        required: true,
        token_address: '0x0000000000000000000000000000000000000000',
        spender_address: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',
        amount_atomic: '1',
      }),
      false,
    )
  })

  it('builds approve calldata', () => {
    const tx = buildSwapApproveTransaction({
      chainId: 1,
      tokenAddress: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
      spenderAddress: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',
      amountAtomic: BigInt('10000000'),
    })
    assert.equal(tx.chainId, 1)
    assert.equal(tx.to, '0xdAC17F958D2ee523a2206206994597C13D831ec7')
    assert.match(tx.data, /^0x095ea7b3/)
  })
})
