import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildSwapAuthoritativeProcessingSteps,
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
    assert.match(SWAP_REVIEW_UI.confirmCta, /Confirmer l'échange/)
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

  it('authoritative (queue) steps have no forbidden jargon — both waiting variants', () => {
    for (const waitingForPrevious of [false, true]) {
      const steps = buildSwapAuthoritativeProcessingSteps(ctx, { waitingForPrevious })
      for (const step of steps) {
        assertNoSwapPrimaryJargon(step.label)
        assertNoSwapPrimaryJargon(step.subtext)
      }
    }
  })

  it('authoritative step #1 distinguishes preparation from queue wait', () => {
    const accepted = buildSwapAuthoritativeProcessingSteps(ctx, { waitingForPrevious: false })
    const waiting = buildSwapAuthoritativeProcessingSteps(ctx, { waitingForPrevious: true })
    // Cas nominal (aucune autre opération) : NE DOIT PAS mentionner une autre opération.
    assert.match(accepted[1]!.label, /Préparation/)
    assert.doesNotMatch(accepted[1]!.subtext, /autre opération/i)
    // Cas attente réelle : doit expliciter l'autre opération en cours.
    assert.match(waiting[1]!.label, /file de traitement/i)
    assert.match(waiting[1]!.subtext, /autre opération/i)
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
