import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { LombardExecutionError } from '@/lib/portal/lombard/lombardExecutionError'
import type { LombardPreparedTx } from '@/lib/portal/lombard/lombardTypes'

import { executeLombardOpenLoanSteps } from './lombardIncrementalStepConfirm'

const APPROVE_TX: LombardPreparedTx = {
  to: '0x0000000000000000000000000000000000000001',
  data: '0x',
  value: '0x0',
  chainId: 8453,
  operation: 'approve',
}

const OPEN_LOAN_TX: LombardPreparedTx = {
  to: '0x0000000000000000000000000000000000000002',
  data: '0x',
  value: '0x0',
  chainId: 8453,
  operation: 'open_loan',
}

const APPROVE_HASH = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
const OPEN_LOAN_HASH = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
const GROUP_KEY = 'test-group-key-001'

function receipt(status: 'success' | 'reverted') {
  return { status, to: null, logs: [] as const }
}

function buildRunner(overrides: {
  transactions: LombardPreparedTx[]
  ledgerEntries: Array<{ id: string }>
  receiptByHash?: Record<string, ReturnType<typeof receipt>>
  confirmStep?: (result: { ledgerEntryId: string; txHash: string }) => Promise<void>
}) {
  const confirms: Array<{ ledgerEntryId: string; txHash: string }> = []
  const sendOrder: string[] = []

  const receiptByHash =
    overrides.receiptByHash ??
    ({
      [APPROVE_HASH]: receipt('success'),
      [OPEN_LOAN_HASH]: receipt('success'),
    } as Record<string, ReturnType<typeof receipt>>)

  const hashByOperation: Record<string, string> = {
    approve: APPROVE_HASH,
    authorize: APPROVE_HASH,
    open_loan: OPEN_LOAN_HASH,
  }

  const run = () =>
    executeLombardOpenLoanSteps({
      groupKey: GROUP_KEY,
      transactions: overrides.transactions,
      ledgerEntries: overrides.ledgerEntries,
      sendTransaction: async (tx) => {
        sendOrder.push(tx.operation)
        return { hash: hashByOperation[tx.operation] ?? APPROVE_HASH }
      },
      waitForReceipt: async (hash) => receiptByHash[hash] ?? null,
      resolveReceiptStatus: (r) => (r.status === 'success' ? 'success' : 'reverted'),
      confirmStep:
        overrides.confirmStep ??
        (async (result) => {
          confirms.push(result)
        }),
    })

  return { run, confirms, sendOrder }
}

describe('executeLombardOpenLoanSteps', () => {
  it('confirms approve then open_loan immediately after each success receipt', async () => {
    const { run, confirms, sendOrder } = buildRunner({
      transactions: [APPROVE_TX, OPEN_LOAN_TX],
      ledgerEntries: [{ id: 'ovt-approve' }, { id: 'ovt-open-loan' }],
    })

    const lastHash = await run()

    assert.equal(lastHash, OPEN_LOAN_HASH)
    assert.deepEqual(sendOrder, ['approve', 'open_loan'])
    assert.deepEqual(confirms, [
      { ledgerEntryId: 'ovt-approve', txHash: APPROVE_HASH },
      { ledgerEntryId: 'ovt-open-loan', txHash: OPEN_LOAN_HASH },
    ])
  })

  it('confirms approve success then open_loan reverted when open_loan fails', async () => {
    const { run, confirms } = buildRunner({
      transactions: [APPROVE_TX, OPEN_LOAN_TX],
      ledgerEntries: [{ id: 'ovt-approve' }, { id: 'ovt-open-loan' }],
      receiptByHash: {
        [APPROVE_HASH]: receipt('success'),
        [OPEN_LOAN_HASH]: receipt('reverted'),
      },
    })

    await assert.rejects(run, (error: unknown) => {
      assert.ok(error instanceof LombardExecutionError)
      assert.equal(error.code, 'reverted')
      assert.equal(error.operation, 'open_loan')
      return true
    })

    assert.deepEqual(confirms, [
      { ledgerEntryId: 'ovt-approve', txHash: APPROVE_HASH },
      { ledgerEntryId: 'ovt-open-loan', txHash: OPEN_LOAN_HASH },
    ])
  })

  it('confirms a single open_loan step (retry path without approve)', async () => {
    const { run, confirms } = buildRunner({
      transactions: [OPEN_LOAN_TX],
      ledgerEntries: [{ id: 'ovt-open-loan-only' }],
    })

    const lastHash = await run()

    assert.equal(lastHash, OPEN_LOAN_HASH)
    assert.deepEqual(confirms, [{ ledgerEntryId: 'ovt-open-loan-only', txHash: OPEN_LOAN_HASH }])
  })

  it('does not duplicate confirm calls for the same ledger entry', async () => {
    let confirmCount = 0
    const { run } = buildRunner({
      transactions: [OPEN_LOAN_TX],
      ledgerEntries: [{ id: 'ovt-open-loan-only' }],
      confirmStep: async () => {
        confirmCount += 1
      },
    })

    await run()
    assert.equal(confirmCount, 1)
  })

  it('throws receipt_timeout without confirming when receipt is missing', async () => {
    const { run, confirms } = buildRunner({
      transactions: [APPROVE_TX],
      ledgerEntries: [{ id: 'ovt-approve' }],
      receiptByHash: {},
    })

    await assert.rejects(run, (error: unknown) => {
      assert.ok(error instanceof LombardExecutionError)
      assert.equal(error.code, 'receipt_timeout')
      return true
    })
    assert.deepEqual(confirms, [])
  })
})
