import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  BUNDLE_INVEST_PROCESSING_STEP_DEFS,
  BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS,
  BUNDLE_PROCESSING_COMPLETED_INDEX,
  buildBundleProcessingSteps,
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

  it('maps swap phases to invest stepper index', () => {
    assert.equal(bundleInvestProcessingStepperIndex('preparing'), 0)
    assert.equal(bundleInvestProcessingStepperIndex('signing'), 1)
    assert.equal(bundleInvestProcessingStepperIndex('submitting'), 2)
    assert.equal(bundleInvestProcessingStepperIndex('bridging'), 3)
    assert.equal(bundleInvestProcessingStepperIndex('completed'), BUNDLE_PROCESSING_COMPLETED_INDEX)
    assert.equal(bundleWithdrawProcessingStepperIndex('submitting'), 2)
  })

  it('review invest shows target allocation label', () => {
    assert.match(BUNDLE_REVIEW_UI.targetAllocation, /Allocation cible/)
    assert.match(BUNDLE_REVIEW_UI.confirmCta, /Confirmer l’investissement/)
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

  it('detects partial invest from existing payload fields', () => {
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
