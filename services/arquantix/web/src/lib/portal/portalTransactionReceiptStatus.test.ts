import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  PORTAL_ENTRYPOINT_V07_ADDRESS,
  readEntryPointUserOperationSuccess,
  resolvePortalTransactionReceiptStatus,
} from '@/lib/portal/portalTransactionReceiptStatus'

const USER_OP_TOPIC =
  '0x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f' as const

function userOpLog(success: boolean) {
  const nonce =
    '0x0000000000000000000000000000000000000000000000000000000000000001' as const
  const successWord = success
    ? ('0x0000000000000000000000000000000000000000000000000000000000000001' as const)
    : ('0x0000000000000000000000000000000000000000000000000000000000000000' as const)
  const gasCost =
    '0x0000000000000000000000000000000000000000000000000000000000000002' as const
  const gasUsed =
    '0x0000000000000000000000000000000000000000000000000000000000000003' as const

  return {
    address: PORTAL_ENTRYPOINT_V07_ADDRESS,
    topics: [
      USER_OP_TOPIC,
      '0x0000000000000000000000000000000000000000000000000000000000000001',
      '0x0000000000000000000000000000000000000000000000000000000000000002',
      '0x0000000000000000000000000000000000000000000000000000000000000003',
    ],
    data: `${nonce}${successWord.slice(2)}${gasCost.slice(2)}${gasUsed.slice(2)}`,
    blockHash: '0x0',
    blockNumber: 1n,
    logIndex: 0,
    transactionHash: '0x0',
    transactionIndex: 0,
    removed: false,
  }
}

describe('portalTransactionReceiptStatus', () => {
  it('marks EntryPoint bundles with failed UserOp as reverted', () => {
    const receipt = {
      to: PORTAL_ENTRYPOINT_V07_ADDRESS,
      status: 'success' as const,
      logs: [userOpLog(false)],
    }

    assert.equal(readEntryPointUserOperationSuccess(receipt), false)
    assert.equal(resolvePortalTransactionReceiptStatus(receipt), 'reverted')
  })

  it('accepts successful EntryPoint UserOp bundles', () => {
    const receipt = {
      to: PORTAL_ENTRYPOINT_V07_ADDRESS,
      status: 'success' as const,
      logs: [userOpLog(true)],
    }

    assert.equal(readEntryPointUserOperationSuccess(receipt), true)
    assert.equal(resolvePortalTransactionReceiptStatus(receipt), 'success')
  })

  it('keeps classic EOA receipts unchanged', () => {
    const receipt = {
      to: '0x833589fcd6edb6e08f4c7c32d4a62f0908c3c88' as const,
      status: 'success' as const,
      logs: [],
    }

    assert.equal(readEntryPointUserOperationSuccess(receipt), null)
    assert.equal(resolvePortalTransactionReceiptStatus(receipt), 'success')
  })
})
