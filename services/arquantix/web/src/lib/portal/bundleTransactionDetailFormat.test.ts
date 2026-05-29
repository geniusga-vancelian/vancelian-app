import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildBundleTransactionDetail,
  findBundleTransactionById,
} from './bundleTransactionDetailFormat'
import type { PortalCryptoWalletTransaction } from './cryptoWalletTypes'

const baseTx: PortalCryptoWalletTransaction = {
  id: 'tx-1',
  side: 'allocation',
  asset: 'USDC',
  amountCrypto: '80',
  amountFiat: '0',
  price: '0',
  currency: 'EUR',
  status: 'completed',
  createdAt: '2026-05-29T05:48:32.000Z',
  title: 'Allocation · Crypto Majors',
  subtitle: '5/5 legs · completed',
  direction: 'info',
  transactionKind: 'bundle_allocation_aggregate',
  bundleBatchId: 'ad281952-5cc3-446d-bab8-24c3fd31f385',
  legsCount: 5,
  successfulLegsCount: 5,
  expandableLegs: [
    {
      fromAsset: 'USDC',
      toAsset: 'CBBTC',
      amountIn: '40',
      amountOut: '0.00054332',
      status: 'confirmed',
      txHash: '0xabc',
    },
    {
      fromAsset: 'USDC',
      toAsset: 'CBETH',
      amountIn: '24',
      amountOut: '0.01192318',
      status: 'confirmed',
      txHash: '0xdef',
    },
  ],
}

describe('buildBundleTransactionDetail', () => {
  it('builds allocation aggregate detail with Li.FI leg steps', () => {
    const detail = buildBundleTransactionDetail(baseTx, 'EUR')
    assert.equal(detail.variant, 'allocation')
    assert.equal(detail.kindLabel, 'Allocation')
    assert.match(detail.amountLabel, /80/)
    assert.match(detail.amountLabel, /USDC/)
    assert.equal(detail.steps.length, 2)
    assert.match(detail.steps[0]?.name ?? '', /CBBTC/)
    assert.match(detail.stepperTitle, /Li\.FI/)
    assert.equal(detail.summary.some((row) => row.key === 'Jambes exécutées'), true)
  })

  it('falls back to standard detail for bundle deposit', () => {
    const deposit: PortalCryptoWalletTransaction = {
      ...baseTx,
      id: 'deposit-1',
      side: 'deposit',
      direction: 'credit',
      transactionKind: 'bundle_deposit',
      title: 'Dépôt · Crypto Majors',
      subtitle: '+80 USDC',
      expandableLegs: undefined,
      legsCount: undefined,
    }
    const detail = buildBundleTransactionDetail(deposit, 'EUR')
    assert.equal(detail.variant, 'flow')
    assert.match(detail.amountLabel, /\+/)
  })
})

describe('findBundleTransactionById', () => {
  it('finds transaction by id or batch id', () => {
    assert.equal(findBundleTransactionById([baseTx], 'tx-1')?.id, 'tx-1')
    assert.equal(
      findBundleTransactionById([baseTx], 'ad281952-5cc3-446d-bab8-24c3fd31f385')?.id,
      'tx-1',
    )
  })
})
