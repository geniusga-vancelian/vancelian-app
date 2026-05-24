import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  computeEarnedYieldDisplay,
  parseHumanAmountToRaw,
} from './morphoVaultFormat'
import {
  computePrincipalNetFromLedgerRows,
  mapPrivyActionStatusToLedgerStatus,
} from './morphoVaultLedger'
import { idempotencyKeySchema } from './morphoVaultValidation'

describe('computeEarnedYieldDisplay', () => {
  const asset = { symbol: 'USDC', decimals: 6 }

  it('n’affiche jamais 0 USDC hardcodé sans historique', () => {
    assert.equal(
      computeEarnedYieldDisplay({ currentAssetsRaw: '1000000', principalNetRaw: null, asset }),
      'Rendement en cours de synchronisation',
    )
  })

  it('calcule earned = max(0, current - principal)', () => {
    assert.equal(
      computeEarnedYieldDisplay({ currentAssetsRaw: '1500000', principalNetRaw: '1000000', asset }),
      '0.5 USDC',
    )
    assert.equal(
      computeEarnedYieldDisplay({ currentAssetsRaw: '900000', principalNetRaw: '1000000', asset }),
      '0 USDC',
    )
  })
})

describe('computePrincipalNetFromLedgerRows', () => {
  it('agrège dépôts et retraits réussis', () => {
    const principal = computePrincipalNetFromLedgerRows([
      { operation: 'deposit', amountRaw: '1000000', status: 'success' },
      { operation: 'withdraw', amountRaw: '200000', status: 'success' },
      { operation: 'deposit', amountRaw: '500000', status: 'pending' },
    ])
    assert.equal(principal, BigInt(800000))
  })
})

describe('mapPrivyActionStatusToLedgerStatus', () => {
  it('mappe les statuts Privy vers le ledger', () => {
    assert.equal(mapPrivyActionStatusToLedgerStatus('succeeded'), 'success')
    assert.equal(mapPrivyActionStatusToLedgerStatus('failed'), 'failed')
    assert.equal(mapPrivyActionStatusToLedgerStatus('processing'), 'pending')
  })
})

describe('idempotencyKeySchema', () => {
  it('accepte une clé valide', () => {
    const key = '550e8400-e29b-41d4-a716-446655440000'
    assert.equal(idempotencyKeySchema.parse(key), key)
  })

  it('rejette une clé trop courte', () => {
    assert.throws(() => idempotencyKeySchema.parse('abc'))
  })
})

describe('parseHumanAmountToRaw withdraw cap helper', () => {
  it('parse USDC 6 decimals pour validation retrait', () => {
    assert.equal(parseHumanAmountToRaw('1.25', 6), BigInt(1250000))
  })
})
