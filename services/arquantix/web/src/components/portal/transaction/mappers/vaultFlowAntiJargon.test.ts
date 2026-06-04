import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildVaultProcessingSteps,
  VAULT_TERMINAL_FAILURE_COPY,
} from '@/components/portal/transaction/mappers/vaultSteps'
import {
  assertNoVaultPrimaryJargon,
  collectVaultProcessingPrimaryStrings,
  collectVaultResultPrimaryStrings,
  collectVaultReviewPrimaryStrings,
  VAULT_FLOW_UI,
  VAULT_REVIEW_UI,
} from '@/components/portal/transaction/mappers/vaultUiCopy'

describe('vaultFlowAntiJargon', () => {
  const ctx = {
    amountLabel: '500 USDC',
    vaultLabel: 'lyUSDC',
    assetSymbol: 'USDC',
  }

  it('review primary copy has no forbidden jargon', () => {
    for (const line of collectVaultReviewPrimaryStrings()) {
      assertNoVaultPrimaryJargon(line)
    }
    assert.doesNotMatch(VAULT_REVIEW_UI.confirmDeposit, /approval pending/i)
    assert.equal(VAULT_REVIEW_UI.title, 'Confirmation')
  })

  it('processing deposit shows 4 product steps without jargon', () => {
    const steps = buildVaultProcessingSteps('deposit', ctx)
    assert.equal(steps.length, 4)
    const lines = collectVaultProcessingPrimaryStrings('deposit', steps, ctx.amountLabel, ctx.vaultLabel)
    for (const line of lines) {
      assertNoVaultPrimaryJargon(line)
    }
  })

  it('processing withdraw shows 4 product steps without jargon', () => {
    const steps = buildVaultProcessingSteps('withdraw', ctx)
    assert.equal(steps.length, 4)
    const lines = collectVaultProcessingPrimaryStrings('withdraw', steps, ctx.amountLabel, ctx.vaultLabel)
    for (const line of lines) {
      assertNoVaultPrimaryJargon(line)
    }
  })

  it('terminal failure copy has no forbidden jargon', () => {
    assertNoVaultPrimaryJargon(VAULT_TERMINAL_FAILURE_COPY.title)
    for (const line of VAULT_TERMINAL_FAILURE_COPY.lines) {
      assertNoVaultPrimaryJargon(line)
    }
  })

  it('result success strings have no forbidden jargon', () => {
    for (const line of collectVaultResultPrimaryStrings()) {
      assertNoVaultPrimaryJargon(line)
    }
    assertNoVaultPrimaryJargon(VAULT_FLOW_UI.processingTitle)
    assertNoVaultPrimaryJargon(
      VAULT_FLOW_UI.processingLeadDeposit(ctx.amountLabel, ctx.vaultLabel),
    )
  })
})
