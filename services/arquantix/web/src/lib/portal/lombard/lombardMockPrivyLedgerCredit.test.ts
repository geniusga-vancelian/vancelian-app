import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  creditLombardMockBorrowToPrivyLedger,
  isLombardMockPrivyLedgerCreditAllowed,
} from '@/lib/portal/lombard/lombardMockPrivyLedgerCredit'

describe('lombardMockPrivyLedgerCredit', () => {
  it('interdit le crédit ledger Privy en production', () => {
    const prevNode = process.env.NODE_ENV
    const prevMock = process.env.LOMBARD_V1_MOCK_ENABLED
    process.env.NODE_ENV = 'production'
    process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
    try {
      assert.equal(isLombardMockPrivyLedgerCreditAllowed(), false)
    } finally {
      process.env.NODE_ENV = prevNode
      if (prevMock === undefined) delete process.env.LOMBARD_V1_MOCK_ENABLED
      else process.env.LOMBARD_V1_MOCK_ENABLED = prevMock
    }
  })

  it('creditLombardMockBorrowToPrivyLedger retourne false en production sans appeler le backend', async () => {
    const prevNode = process.env.NODE_ENV
    const prevMock = process.env.LOMBARD_V1_MOCK_ENABLED
    process.env.NODE_ENV = 'production'
    process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
    try {
      const result = await creditLombardMockBorrowToPrivyLedger({
        personId: '00000000-0000-4000-8000-000000000001',
        groupKey: 'test-group',
      })
      assert.equal(result, false)
    } finally {
      process.env.NODE_ENV = prevNode
      if (prevMock === undefined) delete process.env.LOMBARD_V1_MOCK_ENABLED
      else process.env.LOMBARD_V1_MOCK_ENABLED = prevMock
    }
  })

  it('autorise le crédit mock hors production quand le mock Lombard est actif', () => {
    const prevNode = process.env.NODE_ENV
    const prevMock = process.env.LOMBARD_V1_MOCK_ENABLED
    process.env.NODE_ENV = 'development'
    process.env.LOMBARD_V1_MOCK_ENABLED = 'true'
    try {
      assert.equal(isLombardMockPrivyLedgerCreditAllowed(), true)
    } finally {
      process.env.NODE_ENV = prevNode
      if (prevMock === undefined) delete process.env.LOMBARD_V1_MOCK_ENABLED
      else process.env.LOMBARD_V1_MOCK_ENABLED = prevMock
    }
  })
})
