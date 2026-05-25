import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { mapPortalSavingsVaultTransactions } from './portalSavingsFormat'

describe('mapPortalSavingsVaultTransactions', () => {
  it('builds cumulative history and display rows', () => {
    const createdAt = new Date('2026-01-01T12:00:00.000Z')
    const { transactions, historyPoints } = mapPortalSavingsVaultTransactions(
      [
        {
          id: '1',
          operation: 'deposit',
          amountRaw: '1000000',
          assetSymbol: 'USDC',
          assetDecimals: 6,
          status: 'success',
          txHash: '0xabc',
          walletAddress: '0x1234567890123456789012345678901234567890',
          createdAt,
        },
        {
          id: '2',
          operation: 'withdraw',
          amountRaw: '250000',
          assetSymbol: 'USDC',
          assetDecimals: 6,
          status: 'success',
          txHash: '0xdef',
          walletAddress: '0x1234567890123456789012345678901234567890',
          createdAt: new Date('2026-01-02T12:00:00.000Z'),
        },
      ],
      0.75,
    )

    assert.equal(transactions.length, 2)
    assert.equal(transactions[0]?.incoming, true)
    assert.equal(transactions[1]?.incoming, false)
    assert.match(transactions[0]?.amountDisplay ?? '', /1 USDC/)
    assert.match(transactions[1]?.amountDisplay ?? '', /0\.25 USDC/)
    assert.ok(historyPoints.length >= 2)
  })
})
