/**
 * Mapper Bundle invest / withdraw → Transaction UX Framework V1 (R4.5-E).
 */
import type { BundleFinalizePayload, BundleInvestPayload } from '@/lib/portal/bundleClient'
import type { BundleInvestSession } from '@/lib/portal/bundleInvestSession'
import type { PortalBundleInvestResultVariant } from '@/lib/portal/bundleFlowTypes'
import {
  mapTerminalStatusToResultVariant,
  type BundleInvestTerminalStatus,
} from '@/lib/portal/bundleInvestOrchestration'
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

export const BUNDLE_INVEST_REVIEW_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: BundleProcessingContext) => string
}> = [
  {
    label: 'Autorisation du paiement',
    defaultSub: (ctx) =>
      `Débit de ${ctx.amountLabel} depuis votre compte et préparation de l’opération.`,
  },
  {
    label: 'Transfert des fonds',
    defaultSub: (ctx) => `Transfert vers le portefeuille ${ctx.bundleLabel}.`,
  },
  {
    label: 'Allocation du portefeuille',
    defaultSub: () => 'Répartition de votre investissement sur les actifs cibles.',
  },
  {
    label: 'Mise à jour du portefeuille',
    defaultSub: () => 'Votre position dans le panier est mise à jour.',
  },
]

export function buildBundleReviewPreviewSteps(
  ctx: BundleProcessingContext,
): TransactionStep[] {
  return BUNDLE_INVEST_REVIEW_STEP_DEFS.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
}

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

/** Progression invest processing — monotone (pas les phases LI.FI par leg). */
export type BundleInvestProcessingStage =
  | 'preparing'
  | 'entry_transfer'
  | 'allocating'
  | 'finalizing'
  | 'completed'

export type BundleInvestProcessingProgress = {
  stage: BundleInvestProcessingStage
  entryAsset?: string
  /** Ordre d’exécution des legs (pending API). */
  allocationAssets?: string[]
  allocationLegCurrent?: number
  allocationLegTotal?: number
  activeAsset?: string | null
}

const EMPTY_PROCESSING_CTX: BundleProcessingContext = {
  amountLabel: '',
  bundleLabel: '',
  activeAllocationAsset: null,
}

/** Stepper invest dynamique : préparation → transfert entrée → 1 step / actif → finalisation. */
export function buildBundleInvestProcessingStepsDynamic(params: {
  bundleLabel: string
  entryAsset: string
  allocationAssets: string[]
}): TransactionStep[] {
  const { bundleLabel, entryAsset, allocationAssets } = params
  const prep = BUNDLE_INVEST_PROCESSING_STEP_DEFS[0]!
  const finalize = BUNDLE_INVEST_PROCESSING_STEP_DEFS[3]!

  return [
    {
      label: prep.label,
      subtext: prep.defaultSub(EMPTY_PROCESSING_CTX),
    },
    {
      label: BUNDLE_INVEST_PROCESSING_STEP_DEFS[1]!.label,
      subtext: `Transfert ${entryAsset} vers le portefeuille ${bundleLabel}.`,
    },
    ...allocationAssets.map((asset) => {
      const label = displayBundleAssetLabel(asset)
      return {
        label: `Allocation · ${label}`,
        subtext: `Investissement sur ${label}.`,
      }
    }),
    {
      label: finalize.label,
      subtext: finalize.defaultSub(EMPTY_PROCESSING_CTX),
    },
  ]
}

/** Index stepper monotone — ne recule pas quand une leg repasse en signing. */
export function bundleInvestDynamicProcessingProgressIndex(
  progress: BundleInvestProcessingProgress,
  stepCount: number,
): number {
  const n = Math.max(0, progress.allocationLegTotal ?? progress.allocationAssets?.length ?? 0)
  const lastIndex = Math.max(0, stepCount - 1)

  switch (progress.stage) {
    case 'preparing':
      return 0
    case 'entry_transfer':
      return Math.min(1, lastIndex)
    case 'allocating': {
      const leg = Math.max(1, progress.allocationLegCurrent ?? 1)
      return Math.min(1 + leg, Math.max(2 + n - 1, 1))
    }
    case 'finalizing':
      return Math.min(2 + n, lastIndex)
    case 'completed':
      return stepCount
    default:
      return 0
  }
}

export const BUNDLE_WITHDRAW_REVIEW_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: BundleProcessingContext) => string
}> = [
  {
    label: 'Autorisation du retrait',
    defaultSub: (ctx) => `Retrait de ${ctx.amountLabel} depuis ${ctx.bundleLabel}.`,
  },
  {
    label: 'Désallocation du portefeuille',
    defaultSub: () => 'Vente des positions du panier si nécessaire.',
  },
  {
    label: 'Transfert des fonds',
    defaultSub: (ctx) => `Transfert des USDC vers Mon Trading.`,
  },
  {
    label: 'Mise à jour du portefeuille',
    defaultSub: () => 'Synchronisation de votre solde Mon Trading.',
  },
]

export function buildBundleWithdrawReviewPreviewSteps(
  ctx: BundleProcessingContext,
): TransactionStep[] {
  return BUNDLE_WITHDRAW_REVIEW_STEP_DEFS.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
}

export type BundleWithdrawProcessingStage =
  | 'preparing'
  | 'deallocating'
  | 'transferring'
  | 'finalizing'
  | 'completed'

export type BundleWithdrawProcessingProgress = {
  stage: BundleWithdrawProcessingStage
  entryAsset?: string
  unwindAssets?: string[]
  unwindLegCurrent?: number
  unwindLegTotal?: number
  activeAsset?: string | null
}

/** Stepper retrait : préparation → désallocation (1 step / actif) → transfert USDC → finalisation. */
export function buildBundleWithdrawProcessingStepsDynamic(params: {
  entryAsset: string
  unwindAssets: string[]
}): TransactionStep[] {
  const prep = BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS[0]!
  const transfer = BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS[2]!
  const finalize = BUNDLE_WITHDRAW_PROCESSING_STEP_DEFS[3]!

  const steps: TransactionStep[] = [
    {
      label: prep.label,
      subtext: prep.defaultSub(EMPTY_PROCESSING_CTX),
    },
    ...params.unwindAssets.map((asset) => {
      const label = displayBundleAssetLabel(asset)
      return {
        label: `Désallocation · ${label}`,
        subtext: `Vente de la position ${label} du panier.`,
      }
    }),
    {
      label: transfer.label,
      subtext: `Transfert ${params.entryAsset} vers Mon Trading.`,
    },
    {
      label: finalize.label,
      subtext: finalize.defaultSub(EMPTY_PROCESSING_CTX),
    },
  ]
  return steps
}

export function bundleWithdrawDynamicProcessingProgressIndex(
  progress: BundleWithdrawProcessingProgress,
  stepCount: number,
): number {
  const n = Math.max(0, progress.unwindLegTotal ?? progress.unwindAssets?.length ?? 0)
  const lastIndex = Math.max(0, stepCount - 1)

  switch (progress.stage) {
    case 'preparing':
      return 0
    case 'deallocating': {
      const leg = Math.max(1, progress.unwindLegCurrent ?? 1)
      return Math.min(leg, Math.max(n, 1))
    }
    case 'transferring':
      return Math.min(1 + n, lastIndex)
    case 'finalizing':
      return Math.min(2 + n, lastIndex)
    case 'completed':
      return stepCount
    default:
      return 0
  }
}

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

/**
 * Variante UI résultat invest.
 * Si `terminalStatus` est fourni (orchestration E.2-B), il prime sur la détection legacy.
 */
export function resolveBundleInvestResultVariant(
  invest?: BundleInvestPayload,
  finalize?: BundleFinalizePayload,
  terminalStatus?: BundleInvestTerminalStatus,
): PortalBundleInvestResultVariant {
  if (terminalStatus) {
    return mapTerminalStatusToResultVariant(terminalStatus)
  }
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
