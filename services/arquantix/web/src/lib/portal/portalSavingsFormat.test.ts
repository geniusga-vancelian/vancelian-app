import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  buildSavingsPositionStats,
  formatSavingsPositionReferenceMoney,
  isEurPeggedSavingsAsset,
  mapPortalSavingsVaultTransactions,
  resolveSavingsPositionValue,
  resolveStablecoinValuations,
} from './portalSavingsFormat'
import type { PortalSavingsPosition } from './portalSavingsTypes'

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

describe('resolveStablecoinValuations', () => {
  it('valorise EURC en euros natifs', () => {
    const v = resolveStablecoinValuations('EURC', 1)
    assert.equal(v.estimatedValueEur, 1)
    assert.ok(v.estimatedValueUsd > 1)
  })

  it('valorise USDC en dollars natifs', () => {
    const v = resolveStablecoinValuations('USDC', 10)
    assert.equal(v.estimatedValueUsd, 10)
    assert.ok(Math.abs(v.estimatedValueEur - 9.2) < 1e-9)
  })
})

describe('formatSavingsPositionReferenceMoney', () => {
  const eurcPosition: PortalSavingsPosition = {
    vaultAddress: '0xabc',
    vaultName: 'Flex',
    assetSymbol: 'EURC',
    assetsInVaultDisplay: '0.9999 EURC',
    assetsUsd: 1.09,
    estimatedValueUsd: 1.09,
    estimatedValueEur: 0.9999,
    earnedYieldDisplay: '0 EURC',
    userApyBps: 800,
    provider: 'ledgity',
    integrationMode: 'ledgity_vault',
  }

  it('affiche la position EURC en EUR', () => {
    assert.equal(isEurPeggedSavingsAsset('EURC'), true)
    assert.equal(resolveSavingsPositionValue(eurcPosition, 'EUR'), 0.9999)
    assert.match(formatSavingsPositionReferenceMoney(eurcPosition, 'EUR'), /€|EUR/)
    assert.doesNotMatch(formatSavingsPositionReferenceMoney(eurcPosition, 'EUR'), /\$|US\$/)
  })

  it('construit les stats avec valorisation croisée', () => {
    const stats = buildSavingsPositionStats({
      position: eurcPosition,
      referenceCurrency: 'EUR',
      apyDisplay: '8,00 %',
    })
    assert.equal(stats[0]?.label, 'Solde total')
    assert.match(stats[0]?.value ?? '', /€|EUR/)
    assert.equal(stats.find((row) => row.key === 'cross-usd')?.label, 'Valorisation USD')
  })
})
