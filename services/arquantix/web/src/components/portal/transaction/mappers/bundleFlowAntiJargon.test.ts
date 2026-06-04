import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildBundleProcessingSteps,
  formatBundleAllocationProgressLabel,
} from '@/components/portal/transaction/mappers/bundleSteps'
import {
  assertNoBundlePrimaryJargon,
  BUNDLE_FLOW_UI,
  BUNDLE_REVIEW_UI,
  BUNDLE_TERMINAL_IMPOSSIBLE,
  BUNDLE_TERMINAL_PARTIAL_ALLOCATION,
  BUNDLE_TERMINAL_RECONCILIATION,
  collectBundleProcessingPrimaryStrings,
  collectBundleResultPrimaryStrings,
  collectBundleReviewPrimaryStrings,
} from '@/components/portal/transaction/mappers/bundleUiCopy'

describe('bundleFlowAntiJargon', () => {
  const ctx = {
    amountLabel: '1 000 USDC',
    bundleLabel: 'Panier Growth',
    activeAllocationAsset: 'cbBTC',
  }

  it('review primary copy has no forbidden jargon', () => {
    for (const line of collectBundleReviewPrimaryStrings()) {
      assertNoBundlePrimaryJargon(line)
    }
    assert.doesNotMatch(BUNDLE_REVIEW_UI.confirmCta, /Preview/i)
  })

  it('processing invest shows 4 steps without jargon', () => {
    const steps = buildBundleProcessingSteps('invest', ctx)
    assert.equal(steps.length, 4)
    const lines = collectBundleProcessingPrimaryStrings(
      steps,
      BUNDLE_FLOW_UI.processingLead(ctx.amountLabel, ctx.bundleLabel),
    )
    for (const line of lines) {
      assertNoBundlePrimaryJargon(line)
    }
  })

  it('allocation progress label has no Leg or LI.FI', () => {
    const label = formatBundleAllocationProgressLabel('cbETH')
    assertNoBundlePrimaryJargon(label)
    assert.doesNotMatch(label, /Leg/i)
  })

  it('terminal copies have no forbidden jargon', () => {
    assertNoBundlePrimaryJargon(BUNDLE_TERMINAL_IMPOSSIBLE.title)
    assertNoBundlePrimaryJargon(BUNDLE_TERMINAL_RECONCILIATION.title)
    assertNoBundlePrimaryJargon(BUNDLE_TERMINAL_PARTIAL_ALLOCATION.title)
    assertNoBundlePrimaryJargon(BUNDLE_TERMINAL_PARTIAL_ALLOCATION.lines[0]!)
    for (const line of collectBundleResultPrimaryStrings()) {
      assertNoBundlePrimaryJargon(line)
    }
  })
})
