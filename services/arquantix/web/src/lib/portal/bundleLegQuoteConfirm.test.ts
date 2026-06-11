import { describe, expect, it } from 'vitest'

import {
  snapshotFromInvestLeg,
  snapshotFromRebalanceBuyLeg,
  snapshotFromRebalanceSellLeg,
  snapshotFromWithdrawLeg,
} from '@/lib/portal/bundleLegQuoteConfirm'

describe('bundleLegQuoteConfirm snapshots', () => {
  it('builds invest leg snapshot', () => {
    expect(
      snapshotFromInvestLeg({
        asset: 'ETH',
        status: 'pending',
        entry_asset_consumed: 100,
        crypto_received: 0.045,
      }),
    ).toEqual({
      review_amount_in: '100',
      review_estimated_receive: '0.045',
    })
  })

  it('builds withdraw leg snapshot', () => {
    expect(
      snapshotFromWithdrawLeg({
        asset: 'ETH',
        status: 'pending',
        quantity_sold: 0.5,
        entry_asset_received: 1200,
      }),
    ).toEqual({
      review_amount_in: '0.5',
      review_estimated_receive: '1200',
    })
  })

  it('builds rebalance buy snapshot', () => {
    expect(
      snapshotFromRebalanceBuyLeg({
        amount_in: '50',
        estimated_receive: '0.01',
        entry_asset_spent: 50,
        quantity_bought: 0.01,
      }),
    ).toEqual({
      review_amount_in: '50',
      review_estimated_receive: '0.01',
    })
  })

  it('prefers amount_in string over float quantity_sold on rebalance sell', () => {
    expect(
      snapshotFromRebalanceSellLeg({
        amount_in: '0.068624940000000000',
        estimated_receive: '4.3187654321',
        quantity_sold: 0.06862494,
        entry_asset_received: 4.3187654321,
      }),
    ).toEqual({
      review_amount_in: '0.068624940000000000',
      review_estimated_receive: '4.3187654321',
    })
  })
})
