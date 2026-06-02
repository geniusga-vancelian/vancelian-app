/** Lombard intent terminal statuses (Phase 3B-R2) — parse-safe for UI/admin. */

export const LOMBARD_TERMINAL_INTENT_STATUSES = [
  'confirmed',
  'failed',
  'failed_final',
  'superseded',
  'reconciliation_required',
  'retryable_failed',
] as const

export type LombardIntentStatus = string

export type LombardIntentMetadata = {
  lombard_status_detail?: string | null
  terminal_outcome?: string | null
  superseded_by_group_key?: string | null
  failed_final_reason?: string | null
  steps?: Array<{ step?: string; status?: string; tx_hash?: string | null }>
}

export function isLombardRetryableFailedIntent(status: string | null | undefined): boolean {
  return (status ?? '').trim().toLowerCase() === 'retryable_failed'
}

export function isLombardTerminalIntentStatus(status: string | null | undefined): boolean {
  const norm = (status ?? '').trim().toLowerCase()
  return (
    norm === 'confirmed' ||
    norm === 'failed' ||
    norm === 'failed_final' ||
    norm === 'superseded' ||
    norm === 'reconciliation_required'
  )
}

export function readLombardIntentDisplayStatus(args: {
  status: string | null | undefined
  metadata?: LombardIntentMetadata | null
}): string {
  const status = (args.status ?? '').trim().toLowerCase()
  const detail = (args.metadata?.lombard_status_detail ?? '').trim().toLowerCase()
  if (status === 'retryable_failed' || detail === 'retryable_failed') {
    return 'retryable_failed'
  }
  if (status === 'failed_final' || detail === 'failed_final') {
    return 'failed_final'
  }
  if (status === 'superseded' || detail === 'superseded') {
    return 'superseded'
  }
  return status || 'unknown'
}
