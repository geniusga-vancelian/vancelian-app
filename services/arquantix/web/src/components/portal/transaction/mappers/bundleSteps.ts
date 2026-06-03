/**
 * Mapper Bundle invest / withdraw → Transaction UX Framework V1 (R4.5-E).
 */
import type { BundleFinalizePayload, BundleInvestPayload } from '@/lib/portal/bundleClient'
import type { BundleInvestSession } from '@/lib/portal/bundleInvestSession'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import {
  detectPartialBundleSuccess,
  hasNoBundleInvestProgress,
  shouldAutoResumeBundleInvest as shouldAutoResumeBundleInvestTerminal,
  shouldShowReconciliationForActiveLock,
  shouldTerminalizeStalePartial,
} from '@/lib/portal/bundleInvestTerminalization'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  BUNDLE_TERMINAL_IMPOSSIBLE,
  BUNDLE_TERMINAL_RECONCILIATION,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import type { TransactionStep, TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'

export type BundleOperation = 'invest' | 'withdraw'

export const BUNDLE_INVEST_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: BundleProcessingContext) => string
}> = [
  {
    label: 'Préparation de l’investissement',
    defaultSub: () => 'Vérification du montant et préparation de l’opération.',
  },
  {
    label: 'Transfert des fonds',
    defaultSub: () => 'Transfert vers le portefeuille bundle.',
  },
  {
    label: 'Allocation du portefeuille',
    defaultSub: (ctx) =>
      ctx.activeAllocationAsset
        ? `Allocation en cours : ${ctx.activeAllocationAsset}`
        : 'Répartition de votre investissement sur les actifs cibles.',
  },
  {
    label: 'Mise à jour du portefeuille',
    defaultSub: () => 'Synchronisation de votre position.',
  },
]

export const BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: BundleProcessingContext) => string
}> = [
  {
    label: 'Préparation du retrait',
    defaultSub: () => 'Vérification de votre position et préparation du retrait.',
  },
  {
    label: 'Désallocation du portefeuille',
    defaultSub: (ctx) =>
      ctx.activeAllocationAsset
        ? `Désallocation en cours : ${ctx.activeAllocationAsset}`
        : 'Vente des positions du panier.',
  },
  {
    label: 'Transfert des fonds',
    defaultSub: () => 'Transfert vers votre portefeuille de trading.',
  },
  {
    label: 'Mise à jour du portefeuille',
    defaultSub: () => 'Synchronisation de votre solde.',
  },
]

export type BundleProcessingContext = {
  amountLabel: string
  bundleLabel: string
  activeAllocationAsset?: string | null
}

export const BUNDLE_PROCESSING_COMPLETED_INDEX = 4

const FORBIDDEN_USER_PATTERN =
  /revert|retryable_failed|group_key|idempotency|bundle_internal_swap|tx reverted|0x[a-fA-F0-9]{8,}|\bLI\.FI\b/i

/** Index stepper produit invest (0–3) ; 4 = terminé. */
export function bundleInvestProcessingStepperIndex(phase: SwapExecutionPhase): number {
  switch (phase) {
    case 'preparing':
      return 0
    case 'approving':
    case 'signing':
      return 1
    case 'submitting':
      return 2
    case 'bridging':
      return 3
    case 'completed':
      return 4
    default:
      return 0
  }
}

export function bundleWithdrawProcessingStepperIndex(phase: SwapExecutionPhase): number {
  return bundleInvestProcessingStepperIndex(phase)
}

export function buildBundleProcessingSteps(
  operation: BundleOperation,
  ctx: BundleProcessingContext,
): TransactionStep[] {
  const defs =
    operation === 'invest' ? BUNDLE_INVEST_PROCESSING_STEP_DEFS : BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS
  return defs.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
}

export function formatBundleAllocationProgressLabel(asset: string): string {
  return `Allocation en cours : ${displayBundleAssetLabel(asset)}`
}

export function displayBundleAssetLabel(asset: string): string {
  const trimmed = asset.trim()
  if (!trimmed) return 'actif'
  return trimmed.toUpperCase()
}

export function resolveBundleFailureCopy(error: unknown): TransactionTerminalFailureCopy {
  if (error == null) {
    return BUNDLE_TERMINAL_IMPOSSIBLE
  }
  const msg = error instanceof Error ? error.message : String(error)
  if (FORBIDDEN_USER_PATTERN.test(msg)) {
    return BUNDLE_TERMINAL_IMPOSSIBLE
  }
  return {
    title: BUNDLE_TERMINAL_IMPOSSIBLE.title,
    lines: [msg, BUNDLE_TERMINAL_IMPOSSIBLE.lines[0]!],
  }
}

/** Détection partielle à partir des payloads existants — pas de nouvelle logique backend. */
export function resolveBundleInvestResultVariant(
  invest?: BundleInvestPayload,
  finalize?: BundleFinalizePayload,
): PortalBundleInvestResultVariant {
  if (!invest) return 'impossible'
  if (hasNoBundleInvestProgress(invest) && !detectPartialBundleSuccess(invest, finalize)) {
    return 'impossible'
  }
  if (detectPartialBundleSuccess(invest, finalize)) {
    return 'reconciliation_required'
  }
  return 'success'
}

export {
  shouldShowReconciliationForActiveLock,
  shouldTerminalizeStalePartial,
}

export function shouldAutoResumeBundleInvest(
  lockStatus: 'none' | 'active',
  lockBatchId: string | undefined,
  session: BundleInvestSession | null,
  lock?: { status?: string; batch_id?: string },
): boolean {
  return shouldAutoResumeBundleInvestTerminal(lockStatus, lockBatchId, session, lock)
}
