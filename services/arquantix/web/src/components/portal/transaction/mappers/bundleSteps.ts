/**
 * Mapper Bundle invest / withdraw → Transaction UX Framework V1 (R4.5-E).
 */
import type { BundleFinalizePayload, BundleInvestPayload } from '@/lib/portal/bundleClient'
import type { BundleInvestSession } from '@/lib/portal/bundleInvestSession'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
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

  const status = String(invest.status ?? '').toLowerCase()
  if (status.includes('partial')) return 'reconciliation_required'

  const failed = Number(invest.legs_failed ?? 0)
  const succeeded = Number(invest.legs_succeeded ?? 0)
  const pending = Number(invest.legs_pending ?? 0)
  if (pending > 0) return 'reconciliation_required'
  if (failed > 0 && succeeded > 0) return 'reconciliation_required'

  if (finalize && Number(finalize.recoverable_cash_in_bundle ?? 0) > 0) {
    return 'reconciliation_required'
  }

  return 'success'
}

export function shouldAutoResumeBundleInvest(
  lockStatus: 'none' | 'active',
  lockBatchId: string | undefined,
  session: BundleInvestSession | null,
): boolean {
  return Boolean(
    session?.invest &&
      lockStatus === 'active' &&
      lockBatchId &&
      session.batchId === lockBatchId,
  )
}
