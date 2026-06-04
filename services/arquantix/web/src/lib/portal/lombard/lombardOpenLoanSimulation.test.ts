import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { formatLombardSimulationUserMessage } from '@/lib/portal/lombard/lombardOpenLoanSimulation'

describe('formatLombardSimulationUserMessage', () => {
  it('mentionne la garantie pour un revert collateral', () => {
    const msg = formatLombardSimulationUserMessage('insufficient collateral')
    assert.match(msg, /garantie|marge/i)
  })

  it('propose un retry pour un revert générique', () => {
    const msg = formatLombardSimulationUserMessage('execution reverted')
    assert.match(msg, /réessayer|réseau/i)
  })
})
