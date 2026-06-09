import { resolveBundleInvestErrorMessage } from '@/components/portal/transaction/mappers/bundleUiCopy'
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
    asset_display?: string
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

/** Réponse API V3 Deposit Flow — funding OK, rebalance asynchrone via worker. */
export type BundleV3DepositQueuedPayload = {
  status: 'queued'
  flow: 'bundle_v3_deposit'
  deposit_execution_id: string
  batch_id: string
  portfolio_id: string
  intent_id: string
  outbox_id: string
  outbox_created?: boolean
  funding?: {
    amount?: number | string
    funded?: boolean
    [key: string]: unknown
  }
  message?: string
}

export function isBundleV3DepositQueuedPayload(
  data: Record<string, unknown>,
): data is BundleV3DepositQueuedPayload {
  return (
    data.flow === 'bundle_v3_deposit' &&
    String(data.status ?? '').toLowerCase() === 'queued' &&
    typeof data.batch_id === 'string'
  )
}

export function bundleV3QueuedFundingAmount(
  payload: BundleV3DepositQueuedPayload,
  fallback: number,
): number {
  const raw = payload.funding?.amount
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export function bundleV3QueuedToInvestShim(
  payload: BundleV3DepositQueuedPayload,
  options: { fundingAsset: string; fundingAmount: number },
): BundleInvestPayload {
  const { fundingAsset, fundingAmount } = options
  const received = bundleV3QueuedFundingAmount(payload, fundingAmount)
  return {
    status: 'queued',
    batch_id: payload.batch_id,
    portfolio_id: payload.portfolio_id,
    entry_asset: fundingAsset,
    total_entry_asset_received: received,
    total_entry_asset_consumed: 0,
    cash_leg_remaining: received,
    legs_pending: 0,
    legs_succeeded: 0,
    legs_failed: 0,
    allocation_details: [],
  }
}

export type BundleExpiredInvestLegsPayload = {
  status: 'expired_invest_legs'
  error_code: 'expired_invest_legs'
  message: string
  action: 're_quote_required' | 'cash_rebalance_required'
  batch_id: string
  expired_count: number
  expired_assets: string[]
}

export class BundleExpiredInvestLegsError extends Error {
  readonly payload: BundleExpiredInvestLegsPayload

  constructor(payload: BundleExpiredInvestLegsPayload) {
    super(payload.message)
    this.name = 'BundleExpiredInvestLegsError'
    this.payload = payload
  }
}

export type BundleInvestActiveLockPayload = {
  status: 'none' | 'active'
  reconciled?: boolean
  resume_available?: boolean
  lock?: {
    batch_id: string
    status: string
    portfolio_id?: string
    entry_instrument_id?: string
    funding_asset?: string
    funding_amount?: string
  }
}

export type BundleRebalancePreviewPayload = {
  portfolio_id: string
  status: string
  entry_asset?: string
  cash_leg_value_eur?: number
  buy_plan?: Array<Record<string, unknown>>
  sell_plan?: Array<Record<string, unknown>>
  warnings?: string[]
  message?: string
}

export type BundleRebalanceLeg = {
  asset: string
  status: string
  swap_id?: string
  leg_id?: string
  signing?: Record<string, unknown> | null
  error?: string
}

export type BundleRebalancePayload = {
  portfolio_id: string
  status: string
  batch_id?: string
  buy_results?: BundleRebalanceLeg[]
  sell_results?: BundleRebalanceLeg[]
  message?: string
}

export type PortfolioRebalancingAssetLine = {
  asset: string
  action: 'sell' | 'buy' | string
  amount_entry: string
  status: string
  swap_id?: string
}

export type PortfolioRebalancingPayload = BundleRebalancePayload & {
  flow?: string
  intent_id?: string
  asset_lines?: PortfolioRebalancingAssetLine[]
  v3_status?: string
  rebalance_execution_id?: string
  legacy_lock_abandoned?: { abandoned?: boolean; batch_id?: string }
}

export type BundleInvestResult =
  | { kind: 'success'; payload: BundleInvestPayload }
  | { kind: 'already_pending'; payload: BundleInvestAlreadyPendingPayload }
  | { kind: 'v3_queued'; payload: BundleV3DepositQueuedPayload }

export type BundleFinalizePayload = {
  batch_id: string
  cash_leg_credited: number
  cash_leg_remaining?: number
  recoverable_cash_in_bundle?: number
  invariant_g?: Record<string, unknown>
}

export type BundleWithdrawSellLeg = {
  asset: string
  instrument_id?: string
  quantity_sold?: number
  entry_asset_received?: number
  status: string
  swap_id?: string
  leg_id?: string
  signing?: Record<string, unknown> | null
  error?: string
}

export type BundleWithdrawRelease = {
  released?: boolean
  amount?: number
  reason?: string
  release?: Record<string, unknown>
}

export type BundleWithdrawPayload = {
  status: string
  batch_id: string
  portfolio_id: string
  entry_asset: string
  requested_release_amount: number
  full_withdraw: boolean
  cash_leg_before: number
  needed_from_sells: number
  sell_results: BundleWithdrawSellLeg[]
  release?: BundleWithdrawRelease | null
  execution_provider?: string
}

export type BundleWithdrawAlreadyPendingPayload = {
  status: 'already_pending'
  batch_id: string
  lock_status?: string
  message: string
}

export type BundleWithdrawActiveLockPayload = {
  status: 'none' | 'active'
  lock?: {
    batch_id: string
    status: string
    withdraw_phase?: string
    portfolio_id?: string
    entry_instrument_id?: string
    entry_asset?: string
    requested_release_amount?: string
    full_withdraw?: boolean
  }
}

export type BundleWithdrawFinalizePayload = {
  batch_id: string
  released?: boolean
  amount?: number
  reason?: string
  release?: Record<string, unknown>
}

export type BundleWithdrawResult =
  | { kind: 'success'; payload: BundleWithdrawPayload }
  | { kind: 'already_pending'; payload: BundleWithdrawAlreadyPendingPayload }

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
  const data = (await res.json()) as Record<string, unknown>
  if (res.status === 409 && data.status === 'already_pending') {
    return { kind: 'already_pending', payload: data as BundleInvestAlreadyPendingPayload }
  }
  if (res.ok && isBundleV3DepositQueuedPayload(data)) {
    return { kind: 'v3_queued', payload: data as BundleV3DepositQueuedPayload }
  }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    const detail = typeof data.detail === 'string' ? data.detail : null
    const message = resolveBundleInvestErrorMessage(
      detail || (typeof data.message === 'string' ? data.message : null),
    )
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

export async function resumeBundleInvest(portfolioId: string): Promise<BundleInvestPayload> {
  const res = await fetch('/api/portal/bundles/invest/resume', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ portfolio_id: portfolioId }),
  })
  const data = (await res.json()) as BundleInvestPayload &
    BundleExpiredInvestLegsPayload & {
      detail?: string
      message?: string
      error_code?: string
    }
  if (res.status === 409 && data.error_code === 'expired_invest_legs') {
    throw new BundleExpiredInvestLegsError(data)
  }
  if (!res.ok) {
    const detail =
      data.error_code ||
      (typeof data.detail === 'string' ? data.detail : null) ||
      (typeof data.message === 'string' ? data.message : null)
    throw new Error(resolveBundleInvestErrorMessage(detail))
  }
  return data
}

export async function requoteExpiredBundleInvest(
  portfolioId: string,
): Promise<BundleInvestPayload> {
  const res = await fetch('/api/portal/bundles/invest/requote-expired', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ portfolio_id: portfolioId }),
  })
  const data = (await res.json()) as BundleInvestPayload & { detail?: string; message?: string }
  if (!res.ok) {
    throw new Error(
      (typeof data.detail === 'string' ? data.detail : null) ||
        data.message ||
        'Relance allocation impossible',
    )
  }
  return data
}

export async function previewBundleRebalance(
  portfolioId: string,
): Promise<BundleRebalancePreviewPayload> {
  const res = await fetch(
    `/api/portal/bundles/rebalance/${encodeURIComponent(portfolioId)}/preview`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
  )
  return parseJson(res)
}

export async function executeBundleRebalance(portfolioId: string): Promise<BundleRebalancePayload> {
  const res = await fetch(`/api/portal/bundles/rebalance/${encodeURIComponent(portfolioId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  const data = (await res.json()) as BundleRebalancePayload & { detail?: string; message?: string }
  if (!res.ok) {
    throw new Error(
      (typeof data.detail === 'string' ? data.detail : null) ||
        data.message ||
        'Réallocation impossible',
    )
  }
  return data
}

export async function previewPortfolioRebalancing(
  portfolioId: string,
): Promise<PortfolioRebalancingPayload> {
  const res = await fetch(
    `/api/portal/bundles/rebalancing/${encodeURIComponent(portfolioId)}/preview`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' },
  )
  return parseJson(res)
}

export async function executePortfolioRebalancing(
  portfolioId: string,
): Promise<PortfolioRebalancingPayload> {
  const res = await fetch(
    `/api/portal/bundles/rebalancing/${encodeURIComponent(portfolioId)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal: AbortSignal.timeout(120_000),
    },
  )
  const data = (await res.json()) as PortfolioRebalancingPayload & {
    detail?: string
    message?: string
  }
  if (!res.ok) {
    throw new Error(
      (typeof data.detail === 'string' ? data.detail : null) ||
        data.message ||
        'Rééquilibrage impossible',
    )
  }
  return data
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

const BUNDLE_WITHDRAW_ERROR_MESSAGES: Record<string, string> = {
  invest_lock_active:
    'Un investissement bundle est encore en cours sur ce portefeuille. Attendez la fin des échanges Li.FI ou réessayez dans quelques instants.',
}

export async function withdrawBundle(body: {
  portfolio_id: string
  withdraw_amount?: number
  full_withdraw?: boolean
}): Promise<BundleWithdrawResult> {
  const res = await fetch('/api/portal/bundles/withdraw', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = (await res.json()) as BundleWithdrawPayload &
    BundleWithdrawAlreadyPendingPayload & { detail?: string }
  if (res.status === 409 && data.status === 'already_pending') {
    return { kind: 'already_pending', payload: data as BundleWithdrawAlreadyPendingPayload }
  }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    const detail = typeof data.detail === 'string' ? data.detail : null
    const message =
      (detail && BUNDLE_WITHDRAW_ERROR_MESSAGES[detail]) ||
      detail ||
      data.message ||
      'Requête retrait impossible'
    throw new Error(message)
  }
  return { kind: 'success', payload: data as BundleWithdrawPayload }
}

export async function fetchActiveBundleWithdrawLock(
  portfolioId: string,
): Promise<BundleWithdrawActiveLockPayload> {
  const res = await fetch(
    `/api/portal/bundles/withdraw/active-lock?portfolio_id=${encodeURIComponent(portfolioId)}`,
    { cache: 'no-store' },
  )
  return parseJson(res)
}

export async function finalizeBundleWithdraw(body: {
  portfolio_id: string
  batch_id: string
}): Promise<BundleWithdrawFinalizePayload> {
  const res = await fetch('/api/portal/bundles/withdraw/finalize', {
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

export function pendingWithdrawLegs(withdraw: BundleWithdrawPayload): BundleWithdrawSellLeg[] {
  return (withdraw.sell_results ?? []).filter(
    (leg) => leg.status === 'pending' && Boolean(leg.swap_id),
  )
}
