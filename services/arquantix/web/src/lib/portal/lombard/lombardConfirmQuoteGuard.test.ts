import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  assessLombardConfirmQuote,
  LOMBARD_CONFIRM_GUARANTEE_DRIFT_BPS,
  LOMBARD_CONFIRM_LTV_DRIFT_PP,
} from '@/lib/portal/lombard/lombardConfirmQuoteGuard'
import type { LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'

function baseQuote(overrides: Partial<LombardQuoteResult> = {}): LombardQuoteResult {
  return {
    marketId: '0x9103c3b4e834476c9a62ea009ba2c884ee42e94e6e314a26f04d312434191836',
    collateral: 'cbBTC',
    collateralName: 'Bitcoin',
    targetLtvPercent: 28,
    borrowAmount: '1',
    borrowAmountRaw: '1000000',
    guaranteeAmount: '0.00002897',
    guaranteeAmountRaw: '2897',
    projectedLtvPercent: 27.5,
    safetyLevel: 'comfortable',
    safetyLabel: 'Confortable',
    safetyMessage: 'OK',
    maxBorrowAmount: '100',
    recommendedBorrowAmount: '50',
    borrowApyPercent: 5,
    liquidationLltvPercent: 86,
    walletGuaranteeBalance: '0.001',
    poweredBy: 'Morpho',
    ...overrides,
  }
}

describe('assessLombardConfirmQuote', () => {
  it('accepte un devis identique', () => {
    const q = baseQuote()
    const result = assessLombardConfirmQuote({ snapshot: q, fresh: q })
    assert.equal(result.ok, true)
    if (result.ok) assert.equal(result.materialChange, false)
  })

  it('bloque si safety blocked', () => {
    const snapshot = baseQuote()
    const fresh = baseQuote({ safetyLevel: 'blocked', safetyLabel: 'Bloqué' })
    const result = assessLombardConfirmQuote({ snapshot, fresh })
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.code, 'safety_blocked')
  })

  it('bloque si garantie augmente au-delà du seuil', () => {
    const snapshot = baseQuote({ guaranteeAmountRaw: '2897', guaranteeAmount: '0.00002897' })
    const driftBps = LOMBARD_CONFIRM_GUARANTEE_DRIFT_BPS + 50
    const increased = (BigInt(2897) * BigInt(10_000 + driftBps)) / BigInt(10_000)
    const fresh = baseQuote({
      guaranteeAmountRaw: increased.toString(),
      guaranteeAmount: '0.00003000',
    })
    const result = assessLombardConfirmQuote({ snapshot, fresh })
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.code, 'guarantee_increased')
  })

  it('accepte une légère baisse de garantie avec materialChange', () => {
    const snapshot = baseQuote({ guaranteeAmountRaw: '3000' })
    const fresh = baseQuote({ guaranteeAmountRaw: '2950', guaranteeAmount: '0.00002950' })
    const result = assessLombardConfirmQuote({ snapshot, fresh })
    assert.equal(result.ok, true)
    if (result.ok) assert.equal(result.materialChange, true)
  })

  it('bloque si LTV projetée augmente trop', () => {
    const snapshot = baseQuote({ projectedLtvPercent: 27 })
    const fresh = baseQuote({
      projectedLtvPercent: 27 + LOMBARD_CONFIRM_LTV_DRIFT_PP + 0.1,
    })
    const result = assessLombardConfirmQuote({ snapshot, fresh })
    assert.equal(result.ok, false)
    if (!result.ok) assert.equal(result.code, 'ltv_increased')
  })

  it('processing_retry — accepte une hausse de garantie', () => {
    const snapshot = baseQuote({ guaranteeAmountRaw: '2897' })
    const fresh = baseQuote({ guaranteeAmountRaw: '3200', guaranteeAmount: '0.000032' })
    const result = assessLombardConfirmQuote({
      snapshot,
      fresh,
      mode: 'processing_retry',
    })
    assert.equal(result.ok, true)
  })

  it('processing_retry — bloque toujours safety blocked', () => {
    const fresh = baseQuote({ safetyLevel: 'blocked' })
    const result = assessLombardConfirmQuote({
      snapshot: null,
      fresh,
      mode: 'processing_retry',
    })
    assert.equal(result.ok, false)
  })
})
