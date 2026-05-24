export type MorphoSupportEventLevel = 'info' | 'warning' | 'critical'

export type MorphoSupportEventCode =
  | 'morpho.tx_failed'
  | 'morpho.tx_reverted'
  | 'morpho.tx_pending_stale'
  | 'morpho.reconciliation_mismatch'
  | 'morpho.withdraw_failed'
  | 'morpho.deposit_failed'
  | 'morpho.beta_limit_exceeded'
  | 'morpho.base_rpc_error'

export type MorphoSupportEvent = {
  code: MorphoSupportEventCode
  level: MorphoSupportEventLevel
  message: string
  personId?: string | null
  vaultAddress?: string | null
  txHash?: string | null
  ledgerEntryId?: string | null
  deltaAssetsRaw?: string | null
  metadata?: Record<string, unknown>
}

/** Log structuré v1 pour support / alerting (stdout JSON). */
export function logMorphoSupportEvent(event: MorphoSupportEvent): void {
  const payload = {
    ts: new Date().toISOString(),
    service: 'arquantix-web',
    component: 'morpho_usdc_volt',
    ...event,
  }
  const line = JSON.stringify(payload)
  if (event.level === 'critical') {
    console.error('[morpho:support]', line)
    return
  }
  if (event.level === 'warning') {
    console.warn('[morpho:support]', line)
    return
  }
  console.info('[morpho:support]', line)
}
