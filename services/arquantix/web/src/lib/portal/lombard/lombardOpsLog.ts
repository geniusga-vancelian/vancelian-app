/** Structured Lombard V1 flow logs for beta QA / ops (stdout JSON). */

export type LombardOpsEventCode =
  | 'lombard.quote_requested'
  | 'lombard.quote_blocked'
  | 'lombard.prepare_requested'
  | 'lombard.prepare_blocked'
  | 'lombard.prepare_succeeded'
  | 'lombard.prepare_step_slow'
  | 'lombard.quote_prepare_drift'
  | 'lombard.tx_submitted'
  | 'lombard.confirm_success'
  | 'lombard.confirm_failed'
  | 'lombard.reconciliation_delta'
  | 'lombard.mock_usdc_ledger_credited'

export type LombardOpsEventLevel = 'info' | 'warning' | 'error'

export type LombardOpsEvent = {
  code: LombardOpsEventCode
  level: LombardOpsEventLevel
  message: string
  personId?: string | null
  walletAddress?: string | null
  marketId?: string | null
  groupKey?: string | null
  ledgerEntryId?: string | null
  txHash?: string | null
  blockCode?: string | null
  metadata?: Record<string, unknown>
}

export function logLombardOpsEvent(event: LombardOpsEvent): void {
  const payload = {
    ts: new Date().toISOString(),
    service: 'arquantix-web',
    component: 'lombard_v1',
    ...event,
  }
  const line = JSON.stringify(payload)
  if (event.level === 'error') {
    console.error('[lombard:ops]', line)
    return
  }
  if (event.level === 'warning') {
    console.warn('[lombard:ops]', line)
    return
  }
  console.info('[lombard:ops]', line)
}

export function logLombardQuoteBlocked(args: {
  personId: string
  walletAddress: string
  collateral: string
  borrowAmount: string
  error: { code: string; message: string }
}): void {
  logLombardOpsEvent({
    code: 'lombard.quote_blocked',
    level: 'warning',
    message: args.error.message,
    personId: args.personId,
    walletAddress: args.walletAddress,
    blockCode: args.error.code,
    metadata: {
      collateral: args.collateral,
      borrowAmount: args.borrowAmount,
    },
  })
}

export function logLombardPrepareBlocked(args: {
  personId: string
  walletAddress: string
  collateral: string
  borrowAmount: string
  idempotencyKey: string
  error: { code: string; message: string }
}): void {
  logLombardOpsEvent({
    code: 'lombard.prepare_blocked',
    level: 'warning',
    message: args.error.message,
    personId: args.personId,
    walletAddress: args.walletAddress,
    groupKey: args.idempotencyKey,
    blockCode: args.error.code,
    metadata: {
      collateral: args.collateral,
      borrowAmount: args.borrowAmount,
    },
  })
}

export function logLombardQuotePrepareDrift(args: {
  personId: string
  walletAddress: string
  collateral: string
  borrowAmount: string
  idempotencyKey: string
  errorCode: string
  driftReason: 'prepare_missing_portal_balance' | 'quote_prepare_capacity_mismatch'
  portalWalletCollateralBalance?: string | null
}): void {
  logLombardOpsEvent({
    code: 'lombard.quote_prepare_drift',
    level: 'warning',
    message: 'Quote/prepare capacity mismatch detected.',
    personId: args.personId,
    walletAddress: args.walletAddress,
    groupKey: args.idempotencyKey,
    blockCode: args.errorCode,
    metadata: {
      collateral: args.collateral,
      borrowAmount: args.borrowAmount,
      driftReason: args.driftReason,
      portalBalanceSent: Boolean(args.portalWalletCollateralBalance?.trim()),
      portalWalletCollateralBalance: args.portalWalletCollateralBalance ?? null,
    },
  })
}

export function logLombardPrepareSucceeded(args: {
  personId: string
  walletAddress: string
  collateral: string
  borrowAmount: string
  idempotencyKey: string
  durationMs: number
  txCount: number
}): void {
  logLombardOpsEvent({
    code: 'lombard.prepare_succeeded',
    level: 'info',
    message: 'Lombard prepare succeeded.',
    personId: args.personId,
    walletAddress: args.walletAddress,
    groupKey: args.idempotencyKey,
    metadata: {
      collateral: args.collateral,
      borrowAmount: args.borrowAmount,
      durationMs: args.durationMs,
      txCount: args.txCount,
    },
  })
}

export function logLombardPrepareStepSlow(args: {
  personId: string
  walletAddress: string
  idempotencyKey: string
  step: string
  durationMs: number
}): void {
  logLombardOpsEvent({
    code: 'lombard.prepare_step_slow',
    level: 'warning',
    message: `Lombard prepare step slow: ${args.step}`,
    personId: args.personId,
    walletAddress: args.walletAddress,
    groupKey: args.idempotencyKey,
    metadata: {
      step: args.step,
      durationMs: args.durationMs,
    },
  })
}
