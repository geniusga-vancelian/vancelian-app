import { describe, expect, it } from 'vitest'

import {
  resolveBundleInvestRecovery,
  resolveBundleWithdrawRecovery,
} from './bundleStateFormat'

describe('resolveBundleInvestRecovery', () => {
  it('marks failed allocation as recoverable when cash leg remains', () => {
    const r = resolveBundleInvestRecovery({
      status: 'failed',
      cashLegRemaining: 75,
      legsFailed: 2,
      legsSucceeded: 0,
    })
    expect(r.investPhase).toBe('allocation_failed_recoverable')
    expect(r.isBlocking).toBe(false)
    expect(r.recoverableMessage).toMatch(/cash leg/)
    expect(r.cashLegLabel).toMatch(/75/)
  })

  it('shows partial allocation as non-blocking', () => {
    const r = resolveBundleInvestRecovery({
      status: 'partial',
      cashLegRemaining: 30,
      legsFailed: 1,
      legsSucceeded: 2,
      legsPending: 0,
    })
    expect(r.investPhase).toBe('partial_allocation')
    expect(r.isBlocking).toBe(false)
  })

  it('blocks only while legs are pending', () => {
    const r = resolveBundleInvestRecovery({
      lockStatus: 'partial_pending',
      legsPending: 1,
      cashLegRemaining: 50,
    })
    expect(r.investPhase).toBe('allocating')
    expect(r.isBlocking).toBe(true)
  })
})

describe('resolveBundleWithdrawRecovery', () => {
  it('ready to release is not blocking', () => {
    const r = resolveBundleWithdrawRecovery({
      withdrawPhase: 'READY_TO_RELEASE',
      cashLegBefore: 100,
    })
    expect(r.withdrawPhase).toBe('ready_to_release')
    expect(r.isBlocking).toBe(false)
  })

  it('failed partial remains recoverable with cash', () => {
    const r = resolveBundleWithdrawRecovery({
      withdrawPhase: 'FAILED_PARTIAL',
      cashLegBefore: 40,
    })
    expect(r.withdrawPhase).toBe('failed_partial_recoverable')
    expect(r.isBlocking).toBe(false)
    expect(r.recoverableMessage).toMatch(/partiel/)
  })
})
