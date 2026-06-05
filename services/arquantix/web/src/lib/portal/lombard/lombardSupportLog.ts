export type LombardSupportEventCode =
  | 'lombard.beta_limit_exceeded'
  | 'lombard.reconciliation_delta'
  | 'lombard.pre_borrow_warning'
  | 'lombard.quote_prepare_drift'
  | 'lombard.tx_failed'
  | 'lombard.base_rpc_error'

export type LombardSupportEventLevel = 'info' | 'warning' | 'critical'

export type LombardSupportEvent = {
  code: LombardSupportEventCode
  level: LombardSupportEventLevel
  message: string
  personId?: string | null
  walletAddress?: string | null
  marketId?: string | null
  ledgerEntryId?: string | null
  metadata?: Record<string, unknown>
}

export function logLombardSupportEvent(event: LombardSupportEvent): void {
  const payload = {
    ts: new Date().toISOString(),
    service: 'arquantix-web',
    component: 'lombard_v1',
    ...event,
  }
  const line = JSON.stringify(payload)
  if (event.level === 'critical') {
    console.error('[lombard:support]', line)
    return
  }
  if (event.level === 'warning') {
    console.warn('[lombard:support]', line)
    return
  }
  console.info('[lombard:support]', line)
}
