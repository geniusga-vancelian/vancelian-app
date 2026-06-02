import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  VAULT_DEPOSIT_PROCESSING_STEP_DEFS,
  VAULT_TERMINAL_FAILURE_COPY,
  VAULT_WITHDRAW_PROCESSING_STEP_DEFS,
  buildVaultProcessingSteps,
  buildVaultTechnicalDetailRows,
  resolveVaultFailureCopy,
  vaultProcessingStepperIndex,
  vaultSuccessCopy,
} from '@/components/portal/transaction/mappers/vaultSteps'
import { VAULT_REVIEW_UI } from '@/components/portal/transaction/mappers/vaultUiCopy'

const ctx = {
  amountLabel: '1 000 USDC',
  vaultLabel: 'Steakhouse Prime',
  assetSymbol: 'USDC',
}

describe('vaultSteps', () => {
  it('deposit mapping exposes 4 product steps', () => {
    assert.equal(VAULT_DEPOSIT_PROCESSING_STEP_DEFS.length, 4)
    const steps = buildVaultProcessingSteps('deposit', ctx)
    assert.equal(steps.length, 4)
    assert.equal(steps[0]!.label, 'Préparation')
    assert.equal(steps[3]!.label, 'Mise à jour du portefeuille')
  })

  it('withdraw mapping exposes 4 product steps', () => {
    assert.equal(VAULT_WITHDRAW_PROCESSING_STEP_DEFS.length, 4)
    const steps = buildVaultProcessingSteps('withdraw', ctx)
    assert.equal(steps.length, 4)
    assert.equal(steps[1]!.label, 'Validation du retrait')
    assert.equal(steps[2]!.label, 'Retrait du coffre')
  })

  it('maps execution phases to stepper index', () => {
    assert.equal(vaultProcessingStepperIndex('preparing'), 0)
    assert.equal(vaultProcessingStepperIndex('approval_pending'), 1)
    assert.equal(vaultProcessingStepperIndex('deposit_pending'), 2)
    assert.equal(vaultProcessingStepperIndex('withdraw_pending'), 2)
    assert.equal(vaultProcessingStepperIndex('confirming'), 3)
    assert.equal(vaultProcessingStepperIndex('confirmed'), 4)
  })

  it('review deposit title has no blocking warning copy', () => {
    assert.match(VAULT_REVIEW_UI.titleDeposit, /Récapitulatif/)
    assert.doesNotMatch(VAULT_REVIEW_UI.confirmDeposit, /I understand|warning/i)
  })

  it('review withdraw title and CTA', () => {
    assert.match(VAULT_REVIEW_UI.titleWithdraw, /retrait/i)
    assert.match(VAULT_REVIEW_UI.confirmWithdraw, /Confirmer/)
  })

  it('success deposit uses TransactionResultPage copy constants', () => {
    const copy = vaultSuccessCopy('deposit')
    assert.equal(copy.title, 'Dépôt effectué')
    assert.match(copy.subtitle, /position/)
  })

  it('success withdraw uses TransactionResultPage copy constants', () => {
    const copy = vaultSuccessCopy('withdraw')
    assert.equal(copy.title, 'Retrait effectué')
    assert.match(copy.subtitle, /disponibles/)
  })

  it('failed uses impossible terminal copy', () => {
    assert.match(VAULT_TERMINAL_FAILURE_COPY.title, /Impossible/)
    assert.match(VAULT_TERMINAL_FAILURE_COPY.lines[0]!, /Aucun mouvement/)
  })

  it('tx hash only appears in technical detail rows', () => {
    const without = buildVaultTechnicalDetailRows({
      vaultAddress: '0xabc',
      providerLabel: 'Morpho',
      integrationLabel: 'Direct vault',
      sourceAsset: 'USDC wallet',
      receivedAsset: 'Vault shares',
    })
    assert.equal(without.filter((r) => r.label === 'Hash de transaction').length, 0)

    const withHash = buildVaultTechnicalDetailRows({
      vaultAddress: '0xabc',
      providerLabel: 'Morpho',
      integrationLabel: 'Direct vault',
      sourceAsset: 'USDC',
      receivedAsset: 'Vault',
      txHash: '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef',
    })
    const hashRows = withHash.filter((r) => r.label === 'Hash de transaction')
    assert.equal(hashRows.length, 1)
    assert.match(hashRows[0]!.value, /^0x/)
    const success = vaultSuccessCopy('deposit')
    assert.doesNotMatch(success.title, /0x/)
    assert.doesNotMatch(success.subtitle, /0x/)
    assert.doesNotMatch(success.title, /tx hash/i)
  })

  it('sanitizes blockchain jargon in failure copy', () => {
    const copy = resolveVaultFailureCopy(new Error('tx reverted on chain'))
    assert.equal(copy.title, VAULT_TERMINAL_FAILURE_COPY.title)
    assert.deepEqual(copy.lines, VAULT_TERMINAL_FAILURE_COPY.lines)
  })
})
