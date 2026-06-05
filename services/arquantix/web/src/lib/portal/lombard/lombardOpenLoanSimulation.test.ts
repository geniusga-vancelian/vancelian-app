import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assertLombardOpenLoanSimulates,
  formatLombardSimulationUserMessage,
} from '@/lib/portal/lombard/lombardOpenLoanSimulation'

describe('formatLombardSimulationUserMessage', () => {
  it('mentionne la garantie pour un revert collateral', () => {
    const msg = formatLombardSimulationUserMessage('insufficient collateral')
    assert.match(msg, /garantie|marge/i)
  })

  it('propose un retry pour un revert générique', () => {
    const msg = formatLombardSimulationUserMessage('execution reverted')
    assert.match(msg, /réessayer|réseau/i)
  })

  it('skip simulation when approve/authorize prerequisites are pending', async () => {
    await assert.doesNotReject(async () =>
      assertLombardOpenLoanSimulates({
        walletAddress: '0x0000000000000000000000000000000000000001',
        transactions: [
          {
            to: '0x0000000000000000000000000000000000000002',
            data: '0x',
            value: '0x0',
            chainId: 8453,
            operation: 'approve',
          },
          {
            to: '0x0000000000000000000000000000000000000003',
            data: '0x',
            value: '0x0',
            chainId: 8453,
            operation: 'open_loan',
          },
        ],
      }),
    )
  })
})
