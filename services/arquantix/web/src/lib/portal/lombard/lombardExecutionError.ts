import type { LombardPreparedTx } from '@/lib/portal/lombard/lombardTypes'

export type LombardExecutionFailureCode = 'reverted' | 'receipt_timeout' | 'failed'

export type LombardExecutionFailureView = {
  code: LombardExecutionFailureCode
  headline: string
  stepLabel: string | null
  operation: LombardPreparedTx['operation'] | null
  txHash: string | null
}

export class LombardExecutionError extends Error {
  readonly code: LombardExecutionFailureCode
  readonly operation: LombardPreparedTx['operation'] | null
  readonly txHash: string | null

  constructor(args: {
    code: LombardExecutionFailureCode
    operation?: LombardPreparedTx['operation'] | null
    txHash?: string | null
    message?: string
  }) {
    super(args.message ?? defaultHeadline(args.code))
    this.name = 'LombardExecutionError'
    this.code = args.code
    this.operation = args.operation ?? null
    this.txHash = args.txHash?.trim() || null
  }
}

function defaultHeadline(code: LombardExecutionFailureCode): string {
  switch (code) {
    case 'receipt_timeout':
      return 'Transaction confirmation timed out.'
    case 'failed':
      return 'Transaction failed.'
    case 'reverted':
      return 'On-chain transaction reverted.'
  }
}

export function lombardExecutionStepLabel(
  operation: LombardPreparedTx['operation'],
): string {
  switch (operation) {
    case 'approve':
      return 'Authorising guarantee (token approval)'
    case 'authorize':
      return 'Authorising Morpho protocol access'
    case 'open_loan':
      return 'Opening loan (lock guarantee and receive USDC)'
    default:
      return operation
  }
}

export function toLombardExecutionFailureView(
  error: LombardExecutionError,
): LombardExecutionFailureView {
  return {
    code: error.code,
    headline: error.message,
    stepLabel: error.operation ? lombardExecutionStepLabel(error.operation) : null,
    operation: error.operation,
    txHash: error.txHash,
  }
}

export function resolveLombardExecutionFailure(error: unknown): LombardExecutionFailureView {
  if (error instanceof LombardExecutionError) {
    return toLombardExecutionFailureView(error)
  }
  if (error instanceof Error) {
    return {
      code: 'failed',
      headline: error.message,
      stepLabel: null,
      operation: null,
      txHash: null,
    }
  }
  return {
    code: 'failed',
    headline: 'Transaction failed.',
    stepLabel: null,
    operation: null,
    txHash: null,
  }
}

export function formatLombardExecutionErrorMessage(error: unknown): string {
  const failure = resolveLombardExecutionFailure(error)
  const lines = [failure.headline]
  if (failure.stepLabel) lines.push(`Step: ${failure.stepLabel}`)
  if (failure.txHash) lines.push(`Transaction: ${failure.txHash}`)
  return lines.join('\n')
}
