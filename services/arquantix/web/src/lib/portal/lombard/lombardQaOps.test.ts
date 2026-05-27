import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  canShowLombardDebugPanel,
  isLombardDebugPanelClientHintVisible,
  isLombardNonProductionRuntime,
} from '@/lib/portal/lombard/lombardDebugAccess'
import { logLombardOpsEvent } from '@/lib/portal/lombard/lombardOpsLog'

describe('lombardDebugAccess', () => {
  it('treats non-production as debug-eligible runtime', () => {
    if (process.env.NODE_ENV === 'production') {
      assert.equal(isLombardNonProductionRuntime(), false)
      assert.equal(isLombardDebugPanelClientHintVisible(), false)
    } else {
      assert.equal(isLombardNonProductionRuntime(), true)
      assert.equal(isLombardDebugPanelClientHintVisible(), true)
    }
  })

  it('canShowLombardDebugPanel resolves for unknown person in non-prod', async () => {
    if (process.env.NODE_ENV !== 'production') {
      assert.equal(await canShowLombardDebugPanel('person-test'), true)
    }
  })
})

describe('lombardOpsLog', () => {
  it('exports structured event helper', () => {
    assert.doesNotThrow(() => {
      logLombardOpsEvent({
        code: 'lombard.quote_requested',
        level: 'info',
        message: 'test',
      })
    })
  })
})
