import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  formatLombardExecutionErrorMessage,
  LombardExecutionError,
  lombardExecutionStepLabel,
  resolveLombardExecutionFailure,
} from '@/lib/portal/lombard/lombardExecutionError'

describe('lombardExecutionError', () => {
  it('labels each prepared transaction step', () => {
    assert.equal(lombardExecutionStepLabel('approve'), 'Authorising guarantee (token approval)')
    assert.equal(lombardExecutionStepLabel('authorize'), 'Authorising Morpho protocol access')
    assert.equal(
      lombardExecutionStepLabel('open_loan'),
      'Opening loan (lock guarantee and receive USDC)',
    )
  })

  it('formats revert failures with step and tx hash', () => {
    const error = new LombardExecutionError({
      code: 'reverted',
      operation: 'open_loan',
      txHash: '0x94eef5815d2cb0949432130a72c5c3ef94229c60601aadce999bf1e34b49bb4d',
    })

    assert.deepEqual(resolveLombardExecutionFailure(error), {
      code: 'reverted',
      headline: 'On-chain transaction reverted.',
      stepLabel: 'Opening loan (lock guarantee and receive USDC)',
      operation: 'open_loan',
      txHash: '0x94eef5815d2cb0949432130a72c5c3ef94229c60601aadce999bf1e34b49bb4d',
    })

    assert.equal(
      formatLombardExecutionErrorMessage(error),
      [
        'On-chain transaction reverted.',
        'Step: Opening loan (lock guarantee and receive USDC)',
        'Transaction: 0x94eef5815d2cb0949432130a72c5c3ef94229c60601aadce999bf1e34b49bb4d',
      ].join('\n'),
    )
  })

  it('falls back for non-Lombard errors', () => {
    assert.deepEqual(resolveLombardExecutionFailure(new Error('Wallet mismatch.')), {
      code: 'failed',
      headline: 'Wallet mismatch.',
      stepLabel: null,
      operation: null,
      txHash: null,
    })
    assert.equal(formatLombardExecutionErrorMessage(new Error('Wallet mismatch.')), 'Wallet mismatch.')
    assert.equal(formatLombardExecutionErrorMessage('boom'), 'Transaction failed.')
  })
})
