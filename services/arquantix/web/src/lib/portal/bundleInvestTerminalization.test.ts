import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  BUNDLE_FLOW_UI,
  BUNDLE_RESULT_ACTIONS,
  BUNDLE_TERMINAL_RECONCILIATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import { resolveBundleInvestResultVariant, shouldAutoResumeBundleInvest } from '@/components/portal/transaction/mappers/bundleSteps'
import {
  detectPartialBundleSuccess,
  hasNoBundleInvestProgress,
  resolveBundleInvestTerminalVariant,
  shouldShowReconciliationForActiveLock,
  shouldTerminalizeStalePartial,
} from '@/lib/portal/bundleInvestTerminalization'

const baseInvest = {
  batch_id: '8486fb48-09e6-421c-8654-8a0e5ad1b9be',
  portfolio_id: 'p',
  entry_asset: 'USDC',
}

describe('bundleInvestTerminalization', () => {
  it('pending CBETH after CBBTC confirmed → reconciliation_required', () => {
    const invest = {
      ...baseInvest,
      status: 'partial_pending',
      total_entry_asset_received: 100,
      total_entry_asset_consumed: 50,
      legs_succeeded: 1,
      legs_pending: 1,
      allocation_details: [
        { asset: 'cbBTC', status: 'completed', entry_asset_consumed: 50 },
        { asset: 'cbETH', status: 'pending', swap_id: 'swap-eth' },
      ],
    }
    assert.equal(resolveBundleInvestResultVariant(invest), 'reconciliation_required')
    assert.equal(resolveBundleInvestTerminalVariant(invest), 'reconciliation_required')
  })

  it('funding done + no allocation confirmed + cash leg remains → reconciliation_required', () => {
    const invest = {
      ...baseInvest,
      status: 'partial',
      total_entry_asset_received: 100,
      total_entry_asset_consumed: 0,
      cash_leg_remaining: 4.2,
      legs_succeeded: 0,
      legs_pending: 0,
      allocation_details: [],
    }
    assert.equal(resolveBundleInvestResultVariant(invest), 'reconciliation_required')
    assert.ok(detectPartialBundleSuccess(invest))
  })

  it('no funding/no leg → impossible', () => {
    const invest = {
      ...baseInvest,
      status: 'failed',
      total_entry_asset_received: 0,
      total_entry_asset_consumed: 0,
      allocation_details: [],
    }
    assert.ok(hasNoBundleInvestProgress(invest))
    assert.equal(resolveBundleInvestResultVariant(invest), 'impossible')
    assert.equal(resolveBundleInvestTerminalVariant(invest), 'impossible')
  })

  it('poll timeout partial context resolves reconciliation', () => {
    const invest = {
      ...baseInvest,
      status: 'partial',
      total_entry_asset_received: 100,
      total_entry_asset_consumed: 60,
      legs_succeeded: 1,
      legs_pending: 1,
      allocation_details: [
        { asset: 'cbBTC', status: 'completed' },
        { asset: 'cbETH', status: 'awaiting_signature', swap_id: 's2' },
      ],
    }
    assert.equal(
      resolveBundleInvestTerminalVariant(invest, undefined, { lockStatus: 'signature_requested' }),
      'reconciliation_required',
    )
  })

  it('shouldAutoResumeBundleInvest returns false for stale partial terminal', () => {
    const session = {
      portfolioId: 'p1',
      batchId: baseInvest.batch_id,
      fundingAsset: 'USDC',
      fundingAmount: 100,
      invest: {
        ...baseInvest,
        status: 'partial',
        total_entry_asset_received: 100,
        total_entry_asset_consumed: 50,
        legs_succeeded: 1,
        legs_pending: 0,
        allocation_details: [
          { asset: 'cbBTC', status: 'completed', swap_id: 's1' },
          { asset: 'cbETH', status: 'awaiting_signature', swap_id: 's2' },
        ],
      },
      savedAt: new Date().toISOString(),
    }
    const lock = { batch_id: baseInvest.batch_id, status: 'signature_requested' }
    assert.equal(shouldTerminalizeStalePartial(lock, session), true)
    assert.equal(shouldAutoResumeBundleInvest('active', baseInvest.batch_id, session, lock), false)
  })

  it('blocked active lock partial stale → reconciliation via shouldShowReconciliation', () => {
    const session = {
      portfolioId: 'p1',
      batchId: baseInvest.batch_id,
      fundingAsset: 'USDC',
      fundingAmount: 100,
      invest: {
        ...baseInvest,
        status: 'partial',
        total_entry_asset_received: 100,
        total_entry_asset_consumed: 50,
        allocation_details: [{ asset: 'cbBTC', status: 'completed' }],
      },
      savedAt: new Date().toISOString(),
    }
    assert.equal(
      shouldShowReconciliationForActiveLock(
        { batch_id: baseInvest.batch_id, status: 'signature_requested' },
        session,
      ),
      true,
    )
  })

  it('reconciliation result actions exclude manual retry', () => {
    assert.notEqual(BUNDLE_FLOW_UI.viewBasketCta, BUNDLE_RESULT_ACTIONS.retry)
    assert.match(BUNDLE_TERMINAL_RECONCILIATION.lines[0]!, /Une partie de votre allocation/)
  })

  it('success full allocation unchanged', () => {
    assert.equal(
      resolveBundleInvestResultVariant({
        ...baseInvest,
        status: 'ok',
        total_entry_asset_received: 100,
        total_entry_asset_consumed: 100,
        legs_pending: 0,
        legs_succeeded: 2,
        allocation_details: [
          { asset: 'cbBTC', status: 'completed' },
          { asset: 'cbETH', status: 'completed' },
        ],
      }),
      'success',
    )
  })
})
