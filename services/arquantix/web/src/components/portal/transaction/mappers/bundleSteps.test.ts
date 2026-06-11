import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  BUNDLE_INVEST_PROCESSING_STEP_DEFS,
  BUNDLE_INVEST_REVIEW_STEP_DEFS,
  BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS,
  buildBundleReviewPreviewSteps,
  buildBundleInvestProcessingStepsDynamic,
  buildBundleRebalancingProcessingStepsDynamic,
  buildBundleWithdrawProcessingStepsDynamic,
  bundleRebalancingDynamicProcessingProgressIndex,
  buildBundleProcessingSteps,
  bundleInvestDynamicProcessingProgressIndex,
  bundleWithdrawDynamicProcessingProgressIndex,
  bundleInvestProcessingStepperIndex,
  bundleWithdrawProcessingStepperIndex,
  formatBundleAllocationProgressLabel,
  resolveBundleFailureCopy,
  resolveBundleInvestResultVariant,
  shouldAutoResumeBundleInvest,
} from '@/components/portal/transaction/mappers/bundleSteps'
import {
  BUNDLE_FLOW_UI,
  BUNDLE_REVIEW_UI,
  BUNDLE_TERMINAL_IMPOSSIBLE,
  BUNDLE_TERMINAL_RECONCILIATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'

const ctx = {
  amountLabel: '5 000 USDC',
  bundleLabel: 'Two Crypto Kings',
  activeAllocationAsset: null as string | null,
}

describe('bundleSteps', () => {
  it('invest mapping exposes 4 product steps', () => {
    assert.equal(BUNDLE_INVEST_PROCESSING_STEP_DEFS.length, 4)
    const steps = buildBundleProcessingSteps('invest', ctx)
    assert.equal(steps.length, 4)
    assert.equal(steps[0]!.label, 'Préparation de l’investissement')
    assert.equal(steps[3]!.label, 'Mise à jour du portefeuille')
  })

  it('withdraw mapping exposes 4 product steps', () => {
    assert.equal(BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS.length, 4)
    const steps = buildBundleProcessingSteps('withdraw', ctx)
    assert.equal(steps[2]!.label, 'Transfert des fonds')
  })

  it('legacy swap phase index kept for withdraw stepper', () => {
    assert.equal(bundleInvestProcessingStepperIndex('signing'), 1)
    assert.equal(bundleWithdrawProcessingStepperIndex('submitting'), 2)
  })

  it('rebalancing dynamic stepper lists sells then buys', () => {
    const steps = buildBundleRebalancingProcessingStepsDynamic({
      bundleLabel: 'Crypto Majors',
      legs: [
        { asset: 'AAVE', action: 'sell', amount_entry: '4.42' },
        { asset: 'LINK', action: 'sell', amount_entry: '3.54' },
        { asset: 'ETH', action: 'buy', amount_entry: '12.48' },
      ],
    })
    assert.equal(steps.length, 5)
    assert.equal(steps[0]!.label, 'Calcul du plan')
    assert.match(steps[1]!.label, /Vente · AAVE/)
    assert.match(steps[3]!.label, /Achat · ETH/)

    const stepCount = steps.length
    const idxLeg2 = bundleRebalancingDynamicProcessingProgressIndex(
      { stage: 'executing', legCurrent: 2, legTotal: 3 },
      stepCount,
    )
    assert.ok(idxLeg2 > bundleRebalancingDynamicProcessingProgressIndex(
      { stage: 'executing', legCurrent: 1, legTotal: 3 },
      stepCount,
    ))
  })

  it('invest dynamic stepper progresses monotonically per leg', () => {
    const assets = ['cbBTC', 'cbETH', 'LINK']
    const steps = buildBundleInvestProcessingStepsDynamic({
      bundleLabel: 'Crypto Majors',
      entryAsset: 'USDC',
      allocationAssets: assets,
    })
    assert.equal(steps.length, 2 + assets.length + 1)
    assert.match(steps[1]!.subtext, /Transfert USDC/)
    assert.match(steps[2]!.label, /CBBTC/i)

    const stepCount = steps.length
    const idxPrep = bundleInvestDynamicProcessingProgressIndex({ stage: 'preparing' }, stepCount)
    const idxTransfer = bundleInvestDynamicProcessingProgressIndex(
      { stage: 'entry_transfer', allocationLegTotal: 3 },
      stepCount,
    )
    const idxLeg1 = bundleInvestDynamicProcessingProgressIndex(
      {
        stage: 'allocating',
        allocationLegCurrent: 1,
        allocationLegTotal: 3,
        activeAsset: 'cbBTC',
      },
      stepCount,
    )
    const idxLeg2 = bundleInvestDynamicProcessingProgressIndex(
      {
        stage: 'allocating',
        allocationLegCurrent: 2,
        allocationLegTotal: 3,
        activeAsset: 'cbETH',
      },
      stepCount,
    )
    const idxFinalize = bundleInvestDynamicProcessingProgressIndex(
      { stage: 'finalizing', allocationLegTotal: 3 },
      stepCount,
    )

    assert.equal(idxPrep, 0)
    assert.equal(idxTransfer, 1)
    assert.equal(idxLeg1, 2)
    assert.equal(idxLeg2, 3)
    assert.ok(idxLeg2 > idxLeg1)
    assert.ok(idxFinalize > idxLeg2)
    assert.equal(
      bundleInvestProcessingStepperIndex('signing'),
      bundleInvestProcessingStepperIndex('submitting') - 1,
      'legacy phase mapper still oscillates (not used for invest UI)',
    )
  })

  it('review invest shows Confirmation screen and preview steps', () => {
    assert.equal(BUNDLE_REVIEW_UI.title, 'Confirmation')
    assert.match(BUNDLE_REVIEW_UI.targetAllocation, /Allocation cible/)
    assert.match(BUNDLE_REVIEW_UI.confirmCta, /Confirmer l’investissement/)
    assert.equal(BUNDLE_INVEST_REVIEW_STEP_DEFS.length, 4)
    const previewSteps = buildBundleReviewPreviewSteps(ctx)
    assert.equal(previewSteps.length, 4)
    assert.match(previewSteps[0]!.subtext, /5 000 USDC/)
  })

  it('withdraw dynamic stepper progresses per unwind leg then USDC transfer', () => {
    const assets = ['cbBTC', 'cbETH']
    const steps = buildBundleWithdrawProcessingStepsDynamic({
      entryAsset: 'USDC',
      unwindAssets: assets,
    })
    assert.equal(steps.length, 5)
    assert.match(steps[1]!.label, /Désallocation · CBBTC/i)
    assert.match(steps[3]!.label, /Transfert des fonds/)
    const stepCount = steps.length
    const idxLeg2 = bundleWithdrawDynamicProcessingProgressIndex(
      { stage: 'deallocating', unwindLegCurrent: 2, unwindLegTotal: 2 },
      stepCount,
    )
    const idxTransfer = bundleWithdrawDynamicProcessingProgressIndex(
      { stage: 'transferring', unwindLegTotal: 2 },
      stepCount,
    )
    assert.ok(idxLeg2 > 1)
    assert.ok(idxTransfer > idxLeg2)
  })

  it('allocation step shows asset in progress without Leg', () => {
    const steps = buildBundleProcessingSteps('invest', {
      ...ctx,
      activeAllocationAsset: 'cbBTC',
    })
    assert.match(steps[2]!.subtext, /Allocation en cours : cbBTC/)
    assert.doesNotMatch(steps[2]!.subtext, /Leg/i)
    const label = formatBundleAllocationProgressLabel('cbETH')
    assert.equal(label, 'Allocation en cours : CBETH')
    assert.doesNotMatch(label, /Leg/i)
  })

  it('success invest resolves to success variant', () => {
    assert.equal(
      resolveBundleInvestResultVariant({
        status: 'ok',
        batch_id: 'b',
        portfolio_id: 'p',
        entry_asset: 'USDC',
        total_entry_asset_received: 1,
        total_entry_asset_consumed: 1,
        allocation_details: [],
      }),
      'success',
    )
  })

  it('orchestration terminalStatus maps partial allocation to completed_partial_allocation variant', () => {
    assert.equal(
      resolveBundleInvestResultVariant(undefined, undefined, 'completed_partial_allocation'),
      'completed_partial_allocation',
    )
    assert.equal(
      resolveBundleInvestResultVariant(undefined, undefined, 'completed_full_allocation'),
      'success',
    )
    assert.equal(
      resolveBundleInvestResultVariant(undefined, undefined, 'failed_no_allocation'),
      'impossible',
    )
  })

  it('detects partial invest from existing payload fields (legacy read path)', () => {
    assert.equal(
      resolveBundleInvestResultVariant({
        status: 'partial_pending',
        batch_id: 'b',
        portfolio_id: 'p',
        entry_asset: 'USDC',
        total_entry_asset_received: 100,
        total_entry_asset_consumed: 50,
        allocation_details: [],
        legs_failed: 1,
        legs_succeeded: 1,
      }),
      'reconciliation_required',
    )
    assert.equal(
      resolveBundleInvestResultVariant(
        {
          status: 'ok',
          batch_id: 'b',
          portfolio_id: 'p',
          entry_asset: 'USDC',
          total_entry_asset_received: 100,
          total_entry_asset_consumed: 50,
          allocation_details: [],
          legs_failed: 0,
          legs_succeeded: 1,
          legs_pending: 1,
        },
        { batch_id: 'b', cash_leg_credited: 0, recoverable_cash_in_bundle: 10 },
      ),
      'reconciliation_required',
    )
  })

  it('success invest uses TransactionResultPage copy constants', () => {
    assert.equal(BUNDLE_FLOW_UI.successTitle, 'Portefeuille créé')
    assert.match(BUNDLE_FLOW_UI.successSubtitle, /allocation/)
  })

  it('failure invest uses TransactionResultPage impossible copy', () => {
    assert.match(BUNDLE_TERMINAL_IMPOSSIBLE.title, /Impossible de finaliser/)
    assert.match(BUNDLE_TERMINAL_IMPOSSIBLE.lines[0]!, /Aucun portefeuille/)
    assert.match(BUNDLE_TERMINAL_RECONCILIATION.title, /Vérification/)
  })

  it('failed invest uses impossible terminal copy', () => {
    const copy = resolveBundleFailureCopy(new Error('tx reverted on chain'))
    assert.equal(copy.title, BUNDLE_TERMINAL_IMPOSSIBLE.title)
  })

  it('maps v3 resume disabled code to product copy', () => {
    const copy = resolveBundleFailureCopy(new Error('v3_deposit_flow_resume_disabled'))
    assert.match(copy.lines[0]!, /rééquilibrage automatique V3/)
  })

  it('maps insufficient self-trading API code to product copy', () => {
    const copy = resolveBundleFailureCopy(
      new Error('bundle.funding.insufficient_self_trading'),
    )
    assert.match(copy.lines[0]!, /Mon Trading insuffisant/)
    assert.doesNotMatch(copy.lines[0]!, /bundle\.funding/)
  })

  it('resume session opens processing when lock matches and legs are actionable', () => {
    const session = {
      portfolioId: 'p1',
      batchId: 'batch-1',
      fundingAsset: 'USDC',
      fundingAmount: 100,
      invest: {
        status: 'pending',
        batch_id: 'batch-1',
        portfolio_id: 'p1',
        entry_asset: 'USDC',
        total_entry_asset_received: 100,
        total_entry_asset_consumed: 0,
        allocation_details: [
          { asset: 'cbETH', status: 'pending', swap_id: 'swap-1' },
        ],
      },
      savedAt: new Date().toISOString(),
    }
    assert.equal(shouldAutoResumeBundleInvest('active', 'batch-1', session, { batch_id: 'batch-1', status: 'active' }), true)
    assert.equal(shouldAutoResumeBundleInvest('active', 'other', session), false)
    assert.equal(shouldAutoResumeBundleInvest('none', 'batch-1', session), false)
  })

  it('reconciliation copy matches product spec', () => {
    assert.match(BUNDLE_TERMINAL_RECONCILIATION.lines[0]!, /Une partie de votre allocation/)
    assert.match(BUNDLE_TERMINAL_RECONCILIATION.lines[0]!, /réconciliation de votre portefeuille/)
  })
})
