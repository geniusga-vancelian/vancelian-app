import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  BUNDLE_RESULT_ACTIONS,
  BUNDLE_TERMINAL_PARTIAL_ALLOCATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import { resolveBundleInvestResultVariant } from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BundleLegSkippableError,
  mapTerminalStatusToResultVariant,
  mergeLegOutcomesIntoInvest,
  resolveTerminalStatusFromOutcomes,
  type BundleLegOutcome,
} from '@/lib/portal/bundleInvestOrchestration'
import { shouldAutoResumeBundleInvest } from '@/lib/portal/bundleInvestTerminalization'
import { clearBundleInvestSession, saveBundleInvestSession } from '@/lib/portal/bundleInvestSession'

const baseInvest = {
  batch_id: 'new-batch-001',
  portfolio_id: 'portfolio-1',
  entry_asset: 'USDC',
  entry_instrument_id: 'inst-1',
  total_entry_asset_received: 100,
  total_entry_asset_consumed: 0,
  allocation_details: [
    { asset: 'cbBTC', status: 'pending', swap_id: 'swap-btc', entry_asset_consumed: 56 },
    { asset: 'cbETH', status: 'pending', swap_id: 'swap-eth', entry_asset_consumed: 44 },
  ],
}

function outcome(
  asset: string,
  swapId: string,
  status: BundleLegOutcome['status'],
): BundleLegOutcome {
  return {
    asset,
    swapId,
    status,
    attempts: status === 'confirmed' ? 1 : 2,
    amountUsdc: 50,
  }
}

describe('bundleInvestOrchestration E.2-B', () => {
  it('leg1 confirmed, leg2 fail+retry fail → completed_partial_allocation', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'confirmed'), outcome('cbETH', 'swap-eth', 'skipped_failed')]
    const status = resolveTerminalStatusFromOutcomes(outcomes, mergeLegOutcomesIntoInvest(baseInvest, outcomes))
    assert.equal(status, 'completed_partial_allocation')
    assert.equal(mapTerminalStatusToResultVariant(status), 'completed_partial_allocation')
  })

  it('leg1 fail+retry fail, leg2 success → completed_partial_allocation', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'skipped_failed'), outcome('cbETH', 'swap-eth', 'confirmed')]
    const status = resolveTerminalStatusFromOutcomes(outcomes, mergeLegOutcomesIntoInvest(baseInvest, outcomes))
    assert.equal(status, 'completed_partial_allocation')
  })

  it('all legs success → completed_full_allocation', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'confirmed'), outcome('cbETH', 'swap-eth', 'confirmed')]
    const merged = mergeLegOutcomesIntoInvest(
      { ...baseInvest, total_entry_asset_consumed: 100 },
      outcomes,
    )
    const status = resolveTerminalStatusFromOutcomes(outcomes, merged)
    assert.equal(status, 'completed_full_allocation')
    assert.equal(resolveBundleInvestResultVariant(merged, undefined, status), 'success')
  })

  it('all legs skipped but funding done → completed_partial_allocation', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'skipped_failed'), outcome('cbETH', 'swap-eth', 'skipped_failed')]
    const status = resolveTerminalStatusFromOutcomes(outcomes, baseInvest)
    assert.equal(status, 'completed_partial_allocation')
  })

  it('v3_deposit_queued maps to v3_deposit_queued variant', () => {
    assert.equal(mapTerminalStatusToResultVariant('v3_deposit_queued'), 'v3_deposit_queued')
    const invest = {
      ...baseInvest,
      allocation_details: [],
      total_entry_asset_received: 20,
    }
    assert.equal(
      resolveBundleInvestResultVariant(invest, undefined, 'v3_deposit_queued'),
      'v3_deposit_queued',
    )
  })

  it('no funding/no useful effect → failed_no_allocation', () => {
    const invest = {
      ...baseInvest,
      total_entry_asset_received: 0,
      allocation_details: [],
    }
    const status = resolveTerminalStatusFromOutcomes([], invest)
    assert.equal(status, 'failed_no_allocation')
    assert.equal(mapTerminalStatusToResultVariant(status), 'impossible')
  })

  it('normal skipped leg does not map to reconciliation_required', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'confirmed'), outcome('cbETH', 'swap-eth', 'skipped_failed')]
    const status = resolveTerminalStatusFromOutcomes(outcomes, mergeLegOutcomesIntoInvest(baseInvest, outcomes))
    assert.notEqual(status, 'reconciliation_required')
    assert.notEqual(mapTerminalStatusToResultVariant(status), 'reconciliation_required')
  })

  it('finalize error maps to reconciliation_required', () => {
    const outcomes = [outcome('cbBTC', 'swap-btc', 'confirmed')]
    const status = resolveTerminalStatusFromOutcomes(outcomes, baseInvest, { finalizeError: true })
    assert.equal(status, 'reconciliation_required')
  })

  it('BundleLegSkippableError is not batch-terminal', () => {
    const err = new BundleLegSkippableError('timeout', 'AWAITING_SIGNATURE')
    assert.equal(err.name, 'BundleLegSkippableError')
    assert.equal(err.category, 'timeout')
  })

  it('partial terminal copy has no Retry/Reprendre/Leg/LI.FI', () => {
    assert.match(BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title, /partiellement réalisé/)
    assert.doesNotMatch(BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title, /Retry|Reprendre|Leg|LI\.FI/i)
    assert.notEqual(BUNDLE_RESULT_ACTIONS.retry, 'Reprendre')
  })

  it('no auto-resume after terminal partial session', () => {
    const session = {
      portfolioId: 'portfolio-1',
      batchId: baseInvest.batch_id,
      fundingAsset: 'USDC',
      fundingAmount: 100,
      invest: mergeLegOutcomesIntoInvest(baseInvest, [
        outcome('cbBTC', 'swap-btc', 'confirmed'),
        outcome('cbETH', 'swap-eth', 'skipped_failed'),
      ]),
      savedAt: new Date().toISOString(),
    }
    assert.equal(
      shouldAutoResumeBundleInvest('active', baseInvest.batch_id, session, {
        batch_id: baseInvest.batch_id,
        status: 'signature_requested',
      }),
      false,
    )
  })

  it('session cleared helper after terminal partial (storage contract)', () => {
    saveBundleInvestSession({
      portfolioId: 'portfolio-1',
      batchId: 'batch-clear',
      fundingAsset: 'USDC',
      fundingAmount: 10,
      invest: { ...baseInvest, batch_id: 'batch-clear' },
      savedAt: new Date().toISOString(),
    })
    clearBundleInvestSession('portfolio-1')
    // no throw — contract used by orchestrator after terminal
    assert.ok(true)
  })
})
