import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { parseLombardHumanAmountToRaw } from '@/lib/portal/lombard/lombardFormat'
import { aggregateMockOpenLoansByMarket } from '@/lib/portal/lombard/mocks/lombardMockPositionAggregate'

describe('aggregateMockOpenLoansByMarket', () => {
  it('sums multiple cbBTC draws on the same Morpho market', () => {
    const rows = aggregateMockOpenLoansByMarket([
      {
        lombardOperation: 'open_loan',
        collateral: 'cbBTC',
        borrowRaw: parseLombardHumanAmountToRaw('1000', 6),
        collateralRaw: parseLombardHumanAmountToRaw('0.017857', 8),
      },
      {
        lombardOperation: 'open_loan',
        collateral: 'cbBTC',
        borrowRaw: parseLombardHumanAmountToRaw('150', 6),
        collateralRaw: parseLombardHumanAmountToRaw('0.002678', 8),
      },
      {
        lombardOperation: 'open_loan',
        collateral: 'cbBTC',
        borrowRaw: parseLombardHumanAmountToRaw('135', 6),
        collateralRaw: parseLombardHumanAmountToRaw('0.002410', 8),
      },
    ])

    assert.equal(rows.length, 1)
    assert.equal(rows[0]?.market.collateral, 'cbBTC')
    assert.equal(rows[0]?.borrowRaw, parseLombardHumanAmountToRaw('1285', 6))
    assert.equal(
      rows[0]?.collateralRaw,
      parseLombardHumanAmountToRaw('0.017857', 8) +
        parseLombardHumanAmountToRaw('0.002678', 8) +
        parseLombardHumanAmountToRaw('0.002410', 8),
    )
  })
})
