import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  isLombardRetryableFailedIntent,
  isLombardTerminalIntentStatus,
  readLombardIntentDisplayStatus,
} from './lombardIntentTerminalStatus'

describe('lombardIntentTerminalStatus', () => {
  it('detects retryable_failed', () => {
    assert.equal(isLombardRetryableFailedIntent('retryable_failed'), true)
    assert.equal(isLombardRetryableFailedIntent('partial'), false)
  })

  it('treats new terminal statuses as terminal', () => {
    assert.equal(isLombardTerminalIntentStatus('failed_final'), true)
    assert.equal(isLombardTerminalIntentStatus('superseded'), true)
    assert.equal(isLombardTerminalIntentStatus('retryable_failed'), false)
  })

  it('reads display status from metadata detail fallback', () => {
    assert.equal(
      readLombardIntentDisplayStatus({
        status: 'partial',
        metadata: { lombard_status_detail: 'retryable_failed' },
      }),
      'retryable_failed',
    )
    assert.equal(
      readLombardIntentDisplayStatus({
        status: 'retryable_failed',
        metadata: { terminal_outcome: 'borrow_not_opened' },
      }),
      'retryable_failed',
    )
  })
})
