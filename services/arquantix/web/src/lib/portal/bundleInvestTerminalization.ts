import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'
import type { BundleFinalizePayload, BundleInvestPayload } from '@/lib/portal/bundleClient'
import type { BundleInvestSession } from '@/lib/portal/bundleInvestSession'
import { pendingBundleLegs } from '@/lib/portal/bundleClient'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import { BundleLegSkippableError } from '@/lib/portal/bundleInvestOrchestration'
import { fetchSwapStatus, type SwapStatusPayload } from '@/lib/portal/swapClient'

export const BUNDLE_LEG_TERMINAL_STATUSES = new Set(['CONFIRMED', 'FAILED', 'EXPIRED'])
export const BUNDLE_LEG_STUCK_STATUSES = new Set([
  'AWAITING_SIGNATURE',
  'SUBMITTED',
  'PENDING',
  'QUOTE_RECEIVED',
])

export const BUNDLE_MAX_LEG_AUTO_RETRIES = 1

const POLL_INTERVAL_MS = 5_000
const POLL_TIMEOUT_MS = 300_000

const STALE_PARTIAL_LOCK_STATUSES = new Set([
  'signature_requested',
  'partial',
  'partial_pending',
  'submitted',
  'pending_confirmation',
])

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export class BundleInvestTerminalError extends Error {
  readonly variant: PortalBundleInvestResultVariant
  readonly technicalDetails?: TransactionTechnicalDetailsRow[]

  constructor(opts: {
    variant: PortalBundleInvestResultVariant
    message?: string
    technicalDetails?: TransactionTechnicalDetailsRow[]
  }) {
    super(opts.message ?? 'Investissement bundle terminé côté interface.')
    this.name = 'BundleInvestTerminalError'
    this.variant = opts.variant
    this.technicalDetails = opts.technicalDetails
  }
}

export function isAllocationLegSettled(status: string): boolean {
  const s = status.trim().toLowerCase()
  return ['completed', 'confirmed', 'succeeded', 'success'].includes(s)
}

export function hasNoBundleInvestProgress(invest: BundleInvestPayload): boolean {
  const received = Number(invest.total_entry_asset_received ?? 0)
  const consumed = Number(invest.total_entry_asset_consumed ?? 0)
  const succeeded = Number(invest.legs_succeeded ?? 0)
  const legs = invest.allocation_details ?? []
  const anySettled = legs.some((leg) => isAllocationLegSettled(leg.status))
  return received === 0 && consumed === 0 && succeeded === 0 && !anySettled
}

/** Au moins une action métier appliquée (funding, leg confirmée, partial batch, cash restant). */
export function detectPartialBundleSuccess(
  invest?: BundleInvestPayload,
  finalize?: BundleFinalizePayload,
  opts?: { lockStatus?: string },
): boolean {
  if (!invest) return false

  const status = String(invest.status ?? '').toLowerCase()
  if (status.includes('partial')) return true

  const received = Number(invest.total_entry_asset_received ?? 0)
  const consumed = Number(invest.total_entry_asset_consumed ?? 0)
  const cashRemaining = Number(invest.cash_leg_remaining ?? 0)
  const succeeded = Number(invest.legs_succeeded ?? 0)
  const failed = Number(invest.legs_failed ?? 0)
  const pending = Number(invest.legs_pending ?? 0)

  const legs = invest.allocation_details ?? []
  const settledCount = legs.filter((leg) => isAllocationLegSettled(leg.status)).length
  const incompleteCount = legs.filter(
    (leg) => !isAllocationLegSettled(leg.status) && leg.status.toLowerCase() !== 'skipped',
  ).length

  if (settledCount > 0 && incompleteCount > 0) return true
  if (succeeded > 0 && (pending > 0 || failed > 0)) return true
  if (consumed > 0 && (pending > 0 || cashRemaining > 0)) return true
  if (received > 0 && cashRemaining > 0 && settledCount === 0) return true
  if (finalize && Number(finalize.recoverable_cash_in_bundle ?? 0) > 0) return true

  const lockStatus = String(opts?.lockStatus ?? '').toLowerCase()
  if (STALE_PARTIAL_LOCK_STATUSES.has(lockStatus)) {
    if (settledCount > 0 || consumed > 0 || succeeded > 0 || received > 0) return true
  }

  return false
}

export function resolveBundleInvestTerminalVariant(
  invest?: BundleInvestPayload,
  finalize?: BundleFinalizePayload,
  opts?: { lockStatus?: string },
): PortalBundleInvestResultVariant {
  if (!invest) return 'impossible'
  if (hasNoBundleInvestProgress(invest) && !detectPartialBundleSuccess(invest, finalize, opts)) {
    return 'impossible'
  }
  if (detectPartialBundleSuccess(invest, finalize, opts)) {
    return 'reconciliation_required'
  }
  return 'success'
}

export function buildBundleInvestTechnicalDetails(params: {
  batchId?: string
  failedAsset?: string
  legStatus?: string
  lockStatus?: string
}): TransactionTechnicalDetailsRow[] {
  const rows: TransactionTechnicalDetailsRow[] = []
  if (params.batchId) rows.push({ label: 'batch_id', value: params.batchId })
  if (params.failedAsset) rows.push({ label: 'failed asset', value: params.failedAsset })
  if (params.legStatus) rows.push({ label: 'current leg status', value: params.legStatus })
  if (params.lockStatus) rows.push({ label: 'lock status', value: params.lockStatus })
  return rows
}

function swapStatusFailureMessage(status: SwapStatusPayload): string {
  if (status.status === 'EXPIRED') return 'Quote expirée.'
  return status.error_message ?? 'Exécution impossible'
}

export async function pollBundleLegUntilTerminal(
  swapId: string,
  context?: { invest?: BundleInvestPayload; asset?: string; lockStatus?: string },
): Promise<SwapStatusPayload> {
  const started = Date.now()
  while (Date.now() - started < POLL_TIMEOUT_MS) {
    const status = await fetchSwapStatus(swapId)
    if (BUNDLE_LEG_TERMINAL_STATUSES.has(status.status)) {
      if (status.status === 'CONFIRMED') return status
      throw new BundleLegSkippableError('swap_failed', status.status)
    }
    await sleep(POLL_INTERVAL_MS)
  }

  const last = await fetchSwapStatus(swapId)
  if (last.status === 'CONFIRMED') return last
  if (BUNDLE_LEG_TERMINAL_STATUSES.has(last.status)) {
    throw new BundleLegSkippableError('swap_failed', last.status)
  }

  throw new BundleLegSkippableError('timeout', last.status)
}

export function shouldTerminalizeStalePartial(
  lock: { status?: string; batch_id?: string } | undefined,
  session: BundleInvestSession,
): boolean {
  if (detectPartialBundleSuccess(session.invest, undefined, { lockStatus: lock?.status })) {
    const actionable = pendingBundleLegs(session.invest)
    const lockSt = String(lock?.status ?? '').toLowerCase()
    if (actionable.length === 0) return true
    if (STALE_PARTIAL_LOCK_STATUSES.has(lockSt)) return true
  }
  return false
}

export function shouldShowReconciliationForActiveLock(
  lock: { batch_id: string; status: string },
  session: BundleInvestSession | null,
): boolean {
  const lockSt = String(lock.status ?? '').toLowerCase()
  if (session && session.batchId === lock.batch_id) {
    return shouldTerminalizeStalePartial(lock, session)
  }
  if (STALE_PARTIAL_LOCK_STATUSES.has(lockSt)) return true
  return false
}

export function shouldAutoResumeBundleInvest(
  lockStatus: 'none' | 'active',
  lockBatchId: string | undefined,
  session: BundleInvestSession | null,
  lock?: { status?: string; batch_id?: string },
): boolean {
  if (!session?.invest || lockStatus !== 'active' || !lockBatchId || session.batchId !== lockBatchId) {
    return false
  }
  if (shouldTerminalizeStalePartial(lock, session)) return false
  return pendingBundleLegs(session.invest).length > 0
}
