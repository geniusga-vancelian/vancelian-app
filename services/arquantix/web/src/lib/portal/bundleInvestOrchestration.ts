/**
 * Orchestration bundle invest — R4.5-E.2-B (retry interne, skip leg, terminal obligatoire).
 */
import type { BundleFinalizePayload, BundleInvestPayload } from '@/lib/portal/bundleClient'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import { isAllocationLegSettled } from '@/lib/portal/bundleInvestTerminalization'

export type BundleLegOutcomeStatus = 'confirmed' | 'skipped_failed'

export type BundleLegOutcome = {
  asset: string
  swapId: string
  status: BundleLegOutcomeStatus
  attempts: number
  amountUsdc: number
  txHash?: string | null
  errorCategory?: 'timeout' | 'swap_failed' | 'sign_error' | 'unknown'
}

export type BundleInvestTerminalStatus =
  | 'completed_full_allocation'
  | 'completed_partial_allocation'
  | 'failed_no_allocation'
  | 'reconciliation_required'

/** Erreur leg récupérable par skip — ne termine pas tout le batch. */
export class BundleLegSkippableError extends Error {
  readonly category: 'timeout' | 'swap_failed' | 'sign_error' | 'unknown'
  readonly legStatus?: string

  constructor(category: BundleLegSkippableError['category'], legStatus?: string) {
    super('Leg allocation non finalisée après retry interne.')
    this.name = 'BundleLegSkippableError'
    this.category = category
    this.legStatus = legStatus
  }
}

export function legSkippableFromUnknown(err: unknown): BundleLegSkippableError {
  if (err instanceof BundleLegSkippableError) return err
  const msg = err instanceof Error ? err.message.toLowerCase() : String(err).toLowerCase()
  if (msg.includes('timeout') || msg.includes('délai')) {
    return new BundleLegSkippableError('timeout')
  }
  if (msg.includes('signature') || msg.includes('sign')) {
    return new BundleLegSkippableError('sign_error')
  }
  return new BundleLegSkippableError('unknown')
}

export function isInfraOrchestrationError(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err)
  return (
    /entry_instrument_id/i.test(msg) ||
    /network|fetch failed|internal server/i.test(msg) ||
    /finalize/i.test(msg)
  )
}

export function mergeLegOutcomesIntoInvest(
  invest: BundleInvestPayload,
  outcomes: BundleLegOutcome[],
): BundleInvestPayload {
  const bySwap = new Map(outcomes.map((o) => [o.swapId, o]))
  const details = (invest.allocation_details ?? []).map((leg) => {
    const swapId = leg.swap_id ?? ''
    const outcome = swapId ? bySwap.get(swapId) : undefined
    if (!outcome) return leg
    if (outcome.status === 'confirmed') {
      return { ...leg, status: 'completed' }
    }
    return { ...leg, status: 'skipped_failed' }
  })
  const confirmed = outcomes.filter((o) => o.status === 'confirmed').length
  const skipped = outcomes.filter((o) => o.status === 'skipped_failed').length
  return {
    ...invest,
    allocation_details: details,
    legs_succeeded: confirmed,
    legs_failed: skipped,
    legs_pending: 0,
    status:
      skipped > 0 && confirmed > 0
        ? 'partial_completed'
        : confirmed > 0
          ? 'completed'
          : skipped > 0
            ? 'partial_failed'
            : invest.status,
  }
}

function countSettledLegs(
  invest: BundleInvestPayload,
  outcomes: BundleLegOutcome[],
): { confirmed: number; skipped: number; total: number } {
  const bySwap = new Map(outcomes.map((o) => [o.swapId, o]))
  let confirmed = 0
  let skipped = 0
  const legs = invest.allocation_details ?? []
  for (const leg of legs) {
    const swapId = leg.swap_id ?? ''
    const outcome = swapId ? bySwap.get(swapId) : undefined
    if (outcome?.status === 'confirmed' || (!outcome && isAllocationLegSettled(leg.status))) {
      confirmed += 1
      continue
    }
    if (outcome?.status === 'skipped_failed' || leg.status === 'skipped_failed') {
      skipped += 1
    }
  }
  return { confirmed, skipped, total: legs.length }
}

export function resolveTerminalStatusFromOutcomes(
  outcomes: BundleLegOutcome[],
  invest: BundleInvestPayload,
  opts?: {
    finalize?: BundleFinalizePayload
    finalizeError?: boolean
    infraAmbiguous?: boolean
  },
): BundleInvestTerminalStatus {
  if (opts?.infraAmbiguous || opts?.finalizeError) {
    return 'reconciliation_required'
  }

  const received = Number(invest.total_entry_asset_received ?? 0)
  const consumed = Number(invest.total_entry_asset_consumed ?? 0)
  const cashFromFinalize = Number(opts?.finalize?.recoverable_cash_in_bundle ?? 0)
  const cashRemaining = Number(invest.cash_leg_remaining ?? 0)
  const hasFunding = received > 0 || consumed > 0 || cashFromFinalize > 0 || cashRemaining > 0

  const { confirmed, skipped, total } = countSettledLegs(invest, outcomes)

  if (confirmed === 0 && !hasFunding) {
    return 'failed_no_allocation'
  }

  if (skipped === 0 && confirmed > 0 && (total === 0 || confirmed >= total)) {
    return 'completed_full_allocation'
  }

  if (confirmed > 0 || hasFunding) {
    return 'completed_partial_allocation'
  }

  return 'failed_no_allocation'
}

export function mapTerminalStatusToResultVariant(
  status: BundleInvestTerminalStatus,
): PortalBundleInvestResultVariant {
  switch (status) {
    case 'completed_full_allocation':
      return 'success'
    case 'completed_partial_allocation':
      return 'completed_partial_allocation'
    case 'failed_no_allocation':
      return 'impossible'
    case 'reconciliation_required':
      return 'reconciliation_required'
    default:
      return 'impossible'
  }
}

export function resolveResultVariantFromRun(
  invest: BundleInvestPayload,
  finalize: BundleFinalizePayload | undefined,
  terminalStatus: BundleInvestTerminalStatus,
): PortalBundleInvestResultVariant {
  return mapTerminalStatusToResultVariant(terminalStatus)
}
