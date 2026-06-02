import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildSwapProcessingSteps,
  SWAP_TERMINAL_FAILURE_COPY,
} from '@/components/portal/transaction/mappers/swapSteps'
import {
  assertNoSwapPrimaryJargon,
  collectSwapProcessingPrimaryStrings,
  collectSwapReviewPrimaryStrings,
  SWAP_FLOW_UI,
  SWAP_REVIEW_UI,
} from '@/components/portal/transaction/mappers/swapUiCopy'

describe('swapFlowAntiJargon', () => {
  const ctx = {
    fromAsset: 'USDC',
    toAsset: 'ETH',
    payLabel: '1,000',
    receiveLabel: '0.42 ETH',
  }

  it('review primary copy has no forbidden jargon', () => {
    for (const line of collectSwapReviewPrimaryStrings()) {
      assertNoSwapPrimaryJargon(line)
    }
    assert.doesNotMatch(SWAP_REVIEW_UI.confirmCta, /confirm swap/i)
  })

  it('processing primary copy has no forbidden jargon', () => {
    const steps = buildSwapProcessingSteps(ctx)
    const lines = collectSwapProcessingPrimaryStrings(ctx, steps)
    for (const line of lines) {
      assertNoSwapPrimaryJargon(line)
    }
    for (const step of steps) {
      assertNoSwapPrimaryJargon(step.label)
      assertNoSwapPrimaryJargon(step.subtext)
    }
  })

  it('terminal failure copy has no forbidden jargon', () => {
    assertNoSwapPrimaryJargon(SWAP_TERMINAL_FAILURE_COPY.title)
    for (const line of SWAP_TERMINAL_FAILURE_COPY.lines) {
      assertNoSwapPrimaryJargon(line)
    }
  })

  it('flow chrome strings have no forbidden jargon', () => {
    assertNoSwapPrimaryJargon(SWAP_FLOW_UI.processingTitle)
    assertNoSwapPrimaryJargon(SWAP_FLOW_UI.processingLead(ctx.payLabel, ctx.fromAsset, ctx.toAsset))
    assertNoSwapPrimaryJargon(SWAP_FLOW_UI.successTitle)
    assertNoSwapPrimaryJargon(SWAP_FLOW_UI.quoteExpiredLine)
  })
})
