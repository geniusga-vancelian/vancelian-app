import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  applyConfirmedSellToBundleHoldings,
  applyWithdrawReleaseToDirectSnapshot,
  isSelfTradingCreditPending,
  mapWithdrawStatusToDisplayPhase,
  splitBundleHoldings,
} from '@/lib/portal/bundleWithdrawFormat'
import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'

const samplePositions: PortalBundlePosition[] = [
  {
    asset: 'USDC',
    quantity: 40,
    costBasis: 40,
    positionType: 'cash',
  },
  {
    asset: 'CBBTC',
    quantity: 0.001,
    costBasis: 80,
    marketValue: 90,
    positionType: 'spot',
  },
  {
    asset: 'CBETH',
    quantity: 0.02,
    costBasis: 50,
    marketValue: 55,
    positionType: 'spot',
  },
]

test('splitBundleHoldings separates cash leg and spot assets', () => {
  const split = splitBundleHoldings(samplePositions)
  assert.equal(split.cashLegQuantity, 40)
  assert.equal(split.spotAssets.length, 2)
  assert.equal(split.spotNotional, 145)
  assert.equal(split.totalWithdrawableEstimate, 185)
})

test('self-trading is not credited before RELEASED', () => {
  const directBefore = { usdcBalance: 100 }
  const pendingRelease = { released: false, amount: 30 }

  assert.equal(isSelfTradingCreditPending('UNWINDING', pendingRelease), true)
  assert.equal(isSelfTradingCreditPending('READY_TO_RELEASE', pendingRelease), true)
  assert.equal(isSelfTradingCreditPending('WITHDRAW_REQUESTED', pendingRelease), true)

  const afterRelease = applyWithdrawReleaseToDirectSnapshot(directBefore, {
    released: true,
    amount: 30,
  })
  assert.equal(afterRelease.usdcBalance, 130)

  const noCredit = applyWithdrawReleaseToDirectSnapshot(directBefore, pendingRelease)
  assert.equal(noCredit.usdcBalance, 100)
})

test('confirmed sell increases cash leg without touching self-trading', () => {
  const split = splitBundleHoldings(samplePositions)
  const afterSell = applyConfirmedSellToBundleHoldings(split, {
    asset: 'CBBTC',
    quantitySold: 0.001,
    entryReceived: 88,
    entryAsset: 'USDC',
  })

  assert.equal(afterSell.cashLegQuantity, 128)
  assert.equal(afterSell.spotAssets.length, 1)
  assert.equal(afterSell.spotAssets[0]?.asset, 'CBETH')
  assert.equal(afterSell.totalWithdrawableEstimate, 128 + 55)

  const direct = { usdcBalance: 100 }
  const unchanged = applyWithdrawReleaseToDirectSnapshot(direct, { released: false })
  assert.equal(unchanged.usdcBalance, 100)
})

test('mapWithdrawStatusToDisplayPhase covers backend phases', () => {
  assert.equal(mapWithdrawStatusToDisplayPhase('pending_signature', 'UNWINDING'), 'UNWINDING')
  assert.equal(mapWithdrawStatusToDisplayPhase('ready_to_release', null), 'READY_TO_RELEASE')
  assert.equal(
    mapWithdrawStatusToDisplayPhase('released', null, { released: true, amount: 10 }),
    'RELEASED',
  )
  assert.equal(mapWithdrawStatusToDisplayPhase('failed_partial', 'FAILED_PARTIAL'), 'FAILED_PARTIAL')
})

test('final release updates self-trading accounting without prior credit', () => {
  let direct = { usdcBalance: 200 }

  const phases: Array<ReturnType<typeof mapWithdrawStatusToDisplayPhase>> = [
    'WITHDRAW_REQUESTED',
    'UNWINDING',
    'READY_TO_RELEASE',
  ]
  for (const phase of phases) {
    assert.equal(isSelfTradingCreditPending(phase, { released: false }), true)
    direct = applyWithdrawReleaseToDirectSnapshot(direct, { released: false, amount: 50 })
    assert.equal(direct.usdcBalance, 200)
  }

  direct = applyWithdrawReleaseToDirectSnapshot(direct, { released: true, amount: 50 })
  assert.equal(direct.usdcBalance, 250)
})
