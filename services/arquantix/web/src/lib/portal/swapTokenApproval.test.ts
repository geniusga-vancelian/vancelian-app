import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertSwapTokenApprovalPayload,
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
      chainId: 8453,
      tokenAddress: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
      spenderAddress: '0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE',
    })
    assert.equal(tx.chainId, 8453)
    assert.equal(tx.to, '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
    assert.match(tx.data, /^0x095ea7b3/)
  })

  it('throws when approval payload is marked required but incomplete', () => {
    assert.throws(
      () =>
        assertSwapTokenApprovalPayload({
          required: true,
          token_address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        }),
      /Approbation ERC-20 requise mais incomplète/,
    )
  })
})
