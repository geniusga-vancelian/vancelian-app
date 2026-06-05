import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  LombardAsyncTimeoutError,
  withLombardAsyncTimeout,
} from '@/lib/portal/lombard/lombardAsyncTimeout'

describe('withLombardAsyncTimeout', () => {
  it('returns the resolved value when fn completes in time', async () => {
    const value = await withLombardAsyncTimeout('test_step', async () => 'ok', 500)
    assert.equal(value, 'ok')
  })

  it('rejects with LombardAsyncTimeoutError when fn exceeds timeout', async () => {
    await assert.rejects(
      withLombardAsyncTimeout(
        'build_open_loan_transactions',
        () => new Promise<string>(() => {}),
        50,
      ),
      (error: unknown) => {
        assert.ok(error instanceof LombardAsyncTimeoutError)
        assert.equal(error.code, 'lombard.prepare_timeout')
        assert.equal(error.step, 'build_open_loan_transactions')
        return true
      },
    )
  })
})
