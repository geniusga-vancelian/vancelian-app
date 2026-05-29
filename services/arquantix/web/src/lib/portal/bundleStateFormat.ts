/**
 * États bundle récupérables — cash leg, allocation, retrait.
 * Un état failed/partial ne doit jamais être présenté comme bloquant définitif.
 */

export type BundleInvestRecoveryPhase =
  | 'idle'
  | 'cash_available'
  | 'allocating'
  | 'partial_allocation'
  | 'allocation_failed_recoverable'
  | 'completed'

export type BundleWithdrawRecoveryPhase =
  | 'idle'
  | 'deallocating'
  | 'ready_to_release'
  | 'partially_releasable'
  | 'failed_partial_recoverable'
  | 'released'

export type BundleRecoveryHints = {
  investPhase: BundleInvestRecoveryPhase
  withdrawPhase: BundleWithdrawRecoveryPhase
  cashLegAvailable: number
  cashLegLabel: string | null
  recoverableMessage: string | null
  isBlocking: boolean
}

export function resolveBundleInvestRecovery(input: {
  status?: string
  lockStatus?: string
  cashLegRemaining?: number
  legsPending?: number
  legsFailed?: number
  legsSucceeded?: number
}): Pick<
  BundleRecoveryHints,
  'investPhase' | 'cashLegAvailable' | 'cashLegLabel' | 'recoverableMessage' | 'isBlocking'
> {
  const cash = Math.max(0, input.cashLegRemaining ?? 0)
  const pending = input.legsPending ?? 0
  const failed = input.legsFailed ?? 0
  const succeeded = input.legsSucceeded ?? 0
  const status = (input.lockStatus || input.status || '').toLowerCase()

  if (status === 'completed' || (succeeded > 0 && pending === 0 && failed === 0)) {
    return {
      investPhase: cash > 0 ? 'cash_available' : 'completed',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC disponibles dans le bundle` : null,
      recoverableMessage: null,
      isBlocking: false,
    }
  }

  if (pending > 0 || status.includes('pending') || status === 'submitted') {
    return {
      investPhase: 'allocating',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC en attente d'allocation` : null,
      recoverableMessage: null,
      isBlocking: true,
    }
  }

  if (failed > 0 && succeeded > 0) {
    return {
      investPhase: 'partial_allocation',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC disponibles dans le bundle` : null,
      recoverableMessage:
        'Allocation partielle — les USDC restants sont disponibles dans la cash leg du bundle.',
      isBlocking: false,
    }
  }

  if (failed > 0 || status === 'failed') {
    return {
      investPhase: 'allocation_failed_recoverable',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC disponibles dans le bundle` : null,
      recoverableMessage:
        cash > 0
          ? 'Allocation échouée — vos USDC restent disponibles dans la cash leg du bundle.'
          : 'Allocation échouée — vous pouvez réessayer.',
      isBlocking: false,
    }
  }

  if (cash > 0) {
    return {
      investPhase: 'cash_available',
      cashLegAvailable: cash,
      cashLegLabel: `${cash} USDC disponibles dans le bundle`,
      recoverableMessage: null,
      isBlocking: false,
    }
  }

  return {
    investPhase: 'idle',
    cashLegAvailable: cash,
    cashLegLabel: null,
    recoverableMessage: null,
    isBlocking: false,
  }
}

export function resolveBundleWithdrawRecovery(input: {
  status?: string
  withdrawPhase?: string
  cashLegBefore?: number
  releaseReleased?: boolean
  neededFromSells?: number
}): Pick<
  BundleRecoveryHints,
  'withdrawPhase' | 'cashLegAvailable' | 'cashLegLabel' | 'recoverableMessage' | 'isBlocking'
> {
  const phase = (input.withdrawPhase || input.status || '').toUpperCase()
  const cash = Math.max(0, input.cashLegBefore ?? 0)

  if (input.releaseReleased || phase === 'RELEASED') {
    return {
      withdrawPhase: 'released',
      cashLegAvailable: 0,
      cashLegLabel: null,
      recoverableMessage: null,
      isBlocking: false,
    }
  }

  if (phase === 'READY_TO_RELEASE' || phase === 'ready_to_release') {
    return {
      withdrawPhase: 'ready_to_release',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC prêts à être transférés vers Mon Trading` : null,
      recoverableMessage: 'Finalisez le retrait pour créditer Mon Trading.',
      isBlocking: false,
    }
  }

  if (phase === 'PARTIALLY_UNWOUND' || phase === 'partially_unwound') {
    return {
      withdrawPhase: 'partially_releasable',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC partiellement disponibles dans le bundle` : null,
      recoverableMessage: 'Retrait partiel possible — finalisez pour libérer le cash confirmé.',
      isBlocking: false,
    }
  }

  if (phase === 'FAILED_PARTIAL' || phase === 'failed_partial') {
    return {
      withdrawPhase: 'failed_partial_recoverable',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC disponibles (ventes partielles)` : null,
      recoverableMessage:
        cash > 0
          ? 'Certaines ventes ont échoué — vous pouvez finaliser un retrait partiel du cash disponible.'
          : 'Certaines ventes ont échoué — réessayez ou contactez le support.',
      isBlocking: false,
    }
  }

  if (
    phase === 'UNWINDING' ||
    phase === 'unwinding' ||
    (input.neededFromSells ?? 0) > 0
  ) {
    return {
      withdrawPhase: 'deallocating',
      cashLegAvailable: cash,
      cashLegLabel: cash > 0 ? `${cash} USDC déjà en cash leg` : null,
      recoverableMessage: null,
      isBlocking: true,
    }
  }

  return {
    withdrawPhase: 'idle',
    cashLegAvailable: cash,
    cashLegLabel: cash > 0 ? `${cash} USDC dans la cash leg du bundle` : null,
    recoverableMessage: null,
    isBlocking: false,
  }
}
