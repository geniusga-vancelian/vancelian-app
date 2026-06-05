import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildPrepareBlockedTerminalCopy,
  isLombardQuotePrepareDriftCode,
  LombardPrepareBlockedError,
  resolvePrepareBlockedDriftReason,
} from '@/lib/portal/lombard/lombardPrepareFailure'
import { toLombardTerminalBorrowError } from '@/lib/portal/lombard/lombardOpenLoanExecutionPolicy'

describe('lombardPrepareFailure', () => {
  it('detects quote/prepare drift codes', () => {
    assert.equal(isLombardQuotePrepareDriftCode('lombard.borrow_exceeds_capacity'), true)
    assert.equal(isLombardQuotePrepareDriftCode('lombard.disabled'), false)
  })

  it('classifies missing portal balance drift', () => {
    assert.equal(
      resolvePrepareBlockedDriftReason({
        errorCode: 'lombard.borrow_exceeds_capacity',
        portalWalletCollateralBalance: null,
      }),
      'prepare_missing_portal_balance',
    )
    assert.equal(
      resolvePrepareBlockedDriftReason({
        errorCode: 'lombard.borrow_exceeds_capacity',
        portalWalletCollateralBalance: '0.05',
      }),
      'quote_prepare_capacity_mismatch',
    )
  })

  it('builds prepare-blocked terminal copy without on-chain jargon', () => {
    const copy = buildPrepareBlockedTerminalCopy({
      message: 'Le montant dépasse votre capacité d’emprunt actuelle.',
    })
    assert.match(copy.lines[1] ?? '', /Aucune transaction/i)
    assert.doesNotMatch(copy.lines.join(' '), /revert|0x/i)
  })

  it('maps LombardPrepareBlockedError to terminal copy', () => {
    const err = toLombardTerminalBorrowError(
      new LombardPrepareBlockedError(
        'lombard.borrow_exceeds_capacity',
        'Capacité insuffisante.',
      ),
    )
    assert.match(err.userCopy.lines[0] ?? '', /Capacité/i)
    assert.match(err.userCopy.lines[1] ?? '', /Aucune transaction/i)
  })
})
