/**
 * Read model bundle invest partiel — R4.5-E.2-A (aligné API).
 */
export type BundleReconciliationAllocationRow = {
  swap_id: string
  asset: string
  status: string
  amount_usdc: number
  tx_hash?: string | null
}

export type BundleReconciliationLockAssessment = {
  present: boolean
  status: string | null
  age_minutes: number | null
  ttl_minutes: number
  zombie: boolean
  stale_progress_minutes: number
}

export type BundleReconciliationState = {
  read_only: true
  batch_id: string
  portfolio_id: string
  person_id: string
  status:
    | 'reconciliation_required'
    | 'partial_in_progress'
    | 'completed'
    | 'completed_with_cash_residual'
    | 'impossible'
    | 'not_found'
  intent_status: string | null
  cash_residual_usdc: number
  confirmed_allocations: BundleReconciliationAllocationRow[]
  pending_allocations: BundleReconciliationAllocationRow[]
  failed_allocations: BundleReconciliationAllocationRow[]
  available_actions: Array<'retry_missing_leg' | 'complete_with_cash_residual'>
  lock: BundleReconciliationLockAssessment
  reconciliation_reason: string | null
  inspected_at: string
}

export async function fetchBundleReconciliationState(params: {
  portfolioId: string
  batchId: string
}): Promise<BundleReconciliationState> {
  const qs = new URLSearchParams({
    portfolio_id: params.portfolioId,
    batch_id: params.batchId,
  })
  const res = await fetch(`/api/portal/bundles/reconciliation-state?${qs.toString()}`, {
    cache: 'no-store',
  })
  const data = (await res.json()) as BundleReconciliationState & { detail?: string }
  if (!res.ok) {
    throw new Error(
      typeof data.detail === 'string' ? data.detail : 'Impossible de charger l’état de réconciliation',
    )
  }
  return data
}
