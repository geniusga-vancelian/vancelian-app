import type { SwapExecutePayload } from '@/lib/portal/swapClient'

export type BundleAllocationLeg = {
  asset: string
  instrument_id?: string
  target_weight?: number | null
  entry_asset_consumed?: number
  crypto_received?: number
  status: string
  swap_id?: string
  leg_id?: string
  signing?: Record<string, unknown> | null
  error?: string
}

export type BundleInvestPreviewPayload = {
  preview_status: string
  bundle_id: string
  bundle_name?: string
  funding_asset: string
  funding_amount: string
  entry_asset_used?: string
  estimated_entry_asset_amount?: string
  estimated_remaining_entry_asset?: string
  allocations?: Array<{
    asset: string
    target_weight: string
    estimated_input_amount: string
    estimated_output_quantity: string
    status: string
  }>
  warnings?: string[]
}

export type BundleInvestPayload = {
  status: string
  batch_id: string
  portfolio_id: string
  entry_asset: string
  entry_instrument_id?: string
  total_entry_asset_received: number
  total_entry_asset_consumed: number
  cash_leg_remaining?: number
  legs_pending?: number
  legs_succeeded?: number
  legs_failed?: number
  allocation_details: BundleAllocationLeg[]
  execution_provider?: string
  invariant_g?: Record<string, unknown>
}

export type BundleInvestAlreadyPendingPayload = {
  status: 'already_pending'
  batch_id: string
  lock_status?: string
  message: string
}

export type BundleInvestActiveLockPayload = {
  status: 'none' | 'active'
  lock?: {
    batch_id: string
    status: string
    portfolio_id?: string
    entry_instrument_id?: string
    funding_asset?: string
    funding_amount?: string
  }
}

export type BundleInvestResult =
  | { kind: 'success'; payload: BundleInvestPayload }
  | { kind: 'already_pending'; payload: BundleInvestAlreadyPendingPayload }

export type BundleFinalizePayload = {
  batch_id: string
  cash_leg_credited: number
  invariant_g?: Record<string, unknown>
}

async function parseJson<T>(res: Response): Promise<T> {
  const data = (await res.json()) as T & { detail?: string | { message?: string } }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    const detail = data.detail
    const message =
      (typeof detail === 'object' && detail?.message) ||
      (typeof detail === 'string' ? detail : null) ||
      (data as { message?: string }).message ||
      'Requête bundle impossible'
    throw new Error(message)
  }
  return data
}

export async function previewBundleInvest(body: {
  portfolio_id: string
  funding_asset: string
  funding_amount: number
}): Promise<BundleInvestPreviewPayload> {
  const res = await fetch('/api/portal/bundles/invest/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson(res)
}

export async function investBundle(body: {
  portfolio_id: string
  funding_asset: string
  funding_amount: number
}): Promise<BundleInvestResult> {
  const res = await fetch('/api/portal/bundles/invest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = (await res.json()) as BundleInvestPayload &
    BundleInvestAlreadyPendingPayload & { detail?: string }
  if (res.status === 409 && data.status === 'already_pending') {
    return { kind: 'already_pending', payload: data as BundleInvestAlreadyPendingPayload }
  }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    const message =
      (typeof data.detail === 'string' ? data.detail : null) ||
      data.message ||
      'Requête bundle impossible'
    throw new Error(message)
  }
  return { kind: 'success', payload: data as BundleInvestPayload }
}

export async function fetchActiveBundleInvestLock(
  portfolioId: string,
): Promise<BundleInvestActiveLockPayload> {
  const res = await fetch(
    `/api/portal/bundles/invest/active-lock?portfolio_id=${encodeURIComponent(portfolioId)}`,
    { cache: 'no-store' },
  )
  return parseJson(res)
}

export async function bundleLegPrepareSign(swapId: string): Promise<SwapExecutePayload> {
  const res = await fetch(`/api/portal/bundles/leg/${encodeURIComponent(swapId)}/prepare-sign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  return parseJson(res)
}

export async function submitBundleLegTx(swapId: string, txHash: string): Promise<{
  leg_id: string
  status: string
  swap_id: string
  tx_hash?: string | null
  amount_to?: string | null
}> {
  const res = await fetch(`/api/portal/bundles/leg/${encodeURIComponent(swapId)}/submit-tx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tx_hash: txHash }),
  })
  return parseJson(res)
}

export async function finalizeBundleBatch(body: {
  portfolio_id: string
  batch_id: string
  entry_instrument_id: string
  planned_entry_total: number
  entry_consumed: number
}): Promise<BundleFinalizePayload> {
  const res = await fetch('/api/portal/bundles/batch/finalize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson(res)
}

export function mapBundleSigningToExecute(
  signing: Record<string, unknown> | null | undefined,
  swapId: string,
): SwapExecutePayload | null {
  if (!signing || typeof signing !== 'object') return null
  const swap_id = String(signing.swap_id ?? swapId)
  if (!swap_id) return null
  return {
    swap_id,
    status: String(signing.status ?? 'pending_signature'),
    lifecycle_message: String(signing.lifecycle_message ?? ''),
    transaction: (signing.transaction as SwapExecutePayload['transaction']) ?? null,
    lifi_tool: (signing.lifi_tool as string | null) ?? null,
    signing_wallet_mode:
      (signing.signing_wallet_mode as SwapExecutePayload['signing_wallet_mode']) ?? null,
    signing_wallet_address:
      (signing.signing_wallet_address as string | null) ?? null,
    token_approval: (signing.token_approval as SwapExecutePayload['token_approval']) ?? null,
  }
}

export function pendingBundleLegs(invest: BundleInvestPayload): BundleAllocationLeg[] {
  return (invest.allocation_details ?? []).filter(
    (leg) => leg.status === 'pending' && Boolean(leg.swap_id),
  )
}
