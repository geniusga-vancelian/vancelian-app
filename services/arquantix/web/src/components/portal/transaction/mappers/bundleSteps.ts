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
  resolveBundleInvestErrorMessage,
} from '@/components/portal/transaction/mappers/bundleUiCopy'
import type {
  TransactionStep,
  TransactionStepMarkerState,
  TransactionTerminalFailureCopy,
} from '@/components/portal/transaction/types'

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

const TERMINAL_V3_STATUSES = new Set([
  'COMPLETED',
  'COMPLETED_WITH_RESIDUAL_CASH',
  'FAILED',
  'NO_ACTION',
])

export function isTerminalBundleV3Status(status: string | undefined | null): boolean {
  if (!status) return false
  return TERMINAL_V3_STATUSES.has(status.toUpperCase())
}

/** Stepper bundle — dépôt V3 / rééquilibrage en cours (reprise page détail). */
export function buildBundleActiveOperationSteps(params: {
  bundleLabel: string
  operationType: string
  allocationAssets: string[]
  includeFundingStep: boolean
}): TransactionStep[] {
  const { bundleLabel, operationType, allocationAssets, includeFundingStep } = params
  const steps: TransactionStep[] = []

  if (includeFundingStep) {
    steps.push({
      label: 'Transfert des fonds',
      subtext: `Crédit du cash leg sur ${bundleLabel}.`,
    })
  }

  steps.push({
    label:
      operationType === 'portfolio_rebalancing'
        ? 'Rééquilibrage du portefeuille'
        : 'Allocation du portefeuille',
    subtext:
      allocationAssets.length > 0
        ? 'Répartition vers les actifs cibles.'
        : 'Préparation du plan de rééquilibrage…',
  })

  for (const asset of allocationAssets) {
    const label = displayBundleAssetLabel(asset)
    steps.push({
      label: `Allocation · ${label}`,
      subtext: `Ajustement de la position ${label}.`,
    })
  }

  steps.push({
    label: 'Mise à jour du portefeuille',
    subtext: 'Synchronisation de votre position.',
  })

  return steps
}

export type BundleRebalancingLeg = {
  asset: string
  action: string
  amount_entry?: string
  entry_asset?: string
}

export type BundleRebalancingProcessingStage =
  | 'preparing'
  | 'executing'
  | 'finalizing'
  | 'completed'

export type BundleRebalancingProcessingProgress = {
  stage: BundleRebalancingProcessingStage
  legCurrent?: number
  legTotal?: number
  activeAsset?: string | null
}

function formatRebalanceLegAmount(amount?: string, entryAsset = 'USDC'): string {
  if (!amount) return ''
  const n = Number(amount)
  if (!Number.isFinite(n)) return ''
  const formatted = new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
  return `${formatted} ${entryAsset}`
}

const REBALANCE_LEG_COMPLETED = ['completed', 'confirmed', 'success'] as const
const REBALANCE_LEG_FAILED = ['failed', 'expired'] as const
const REBALANCE_LEG_IN_PROGRESS = [
  'pending',
  'signing',
  'approving',
  'submitting',
  'running',
] as const

function normalizeRebalanceLegStatus(status: string): string {
  return String(status).toLowerCase()
}

function rebalanceLegMarkerFromStatus(
  status: string,
  isActiveLeg: boolean,
  stage: BundleRebalancingProcessingStage,
  executionPhase: string,
): TransactionStepMarkerState {
  const s = normalizeRebalanceLegStatus(status)
  if (REBALANCE_LEG_COMPLETED.includes(s as (typeof REBALANCE_LEG_COMPLETED)[number])) {
    return 'done'
  }
  if (REBALANCE_LEG_FAILED.includes(s as (typeof REBALANCE_LEG_FAILED)[number])) {
    // Pendant l'exécution, un leg peut être marqué failed côté client avant reprise — ne pas clore en rouge.
    if (executionPhase !== 'failed' && stage === 'executing') {
      return isActiveLeg ? 'loading' : 'pending'
    }
    return 'failed'
  }
  if (REBALANCE_LEG_IN_PROGRESS.includes(s as (typeof REBALANCE_LEG_IN_PROGRESS)[number])) {
    return 'loading'
  }
  if (isActiveLeg && stage === 'executing') {
    return 'loading'
  }
  return 'pending'
}

/** États stepper rééquilibrage — dérivés des statuts réels par leg (pas d'index monotone). */
export function buildBundleRebalancingStepStates(params: {
  legs: BundleRebalancingLeg[]
  assetLines: Array<{ asset: string; status: string }>
  progress: BundleRebalancingProcessingProgress
  executionPhase: string
}): TransactionStepMarkerState[] {
  const { legs, assetLines, progress, executionPhase } = params
  const stepCount = 1 + legs.length + 1
  const states: TransactionStepMarkerState[] = Array.from({ length: stepCount }, () => 'pending')

  const statusByAsset = new Map(
    assetLines.map((line) => [line.asset.toUpperCase(), line.status]),
  )

  const resolveActiveAsset = (): string | null => {
    if (progress.activeAsset) {
      return progress.activeAsset.toUpperCase()
    }
    if (progress.stage !== 'executing') {
      return null
    }
    for (const leg of legs) {
      const status = normalizeRebalanceLegStatus(
        statusByAsset.get(leg.asset.toUpperCase()) ?? 'planned',
      )
      if (
        REBALANCE_LEG_IN_PROGRESS.includes(
          status as (typeof REBALANCE_LEG_IN_PROGRESS)[number],
        )
      ) {
        return leg.asset.toUpperCase()
      }
    }
    for (const leg of legs) {
      const status = normalizeRebalanceLegStatus(
        statusByAsset.get(leg.asset.toUpperCase()) ?? 'planned',
      )
      if (
        !REBALANCE_LEG_COMPLETED.includes(status as (typeof REBALANCE_LEG_COMPLETED)[number]) &&
        !REBALANCE_LEG_FAILED.includes(status as (typeof REBALANCE_LEG_FAILED)[number])
      ) {
        return leg.asset.toUpperCase()
      }
    }
    return null
  }

  const activeAsset = resolveActiveAsset()

  if (executionPhase === 'preparing' && progress.stage === 'preparing') {
    states[0] = 'loading'
  } else {
    states[0] = 'done'
  }

  legs.forEach((leg, index) => {
    const stepIndex = 1 + index
    const status = statusByAsset.get(leg.asset.toUpperCase()) ?? 'planned'
    const isActiveLeg = activeAsset === leg.asset.toUpperCase()
    states[stepIndex] = rebalanceLegMarkerFromStatus(
      status,
      isActiveLeg,
      progress.stage,
      executionPhase,
    )
  })

  const finalIndex = stepCount - 1
  if (progress.stage === 'finalizing') {
    states[finalIndex] = 'loading'
  } else if (progress.stage === 'completed' || executionPhase === 'completed') {
    states[finalIndex] = 'done'
  } else {
    const hasFailedLeg = legs.some((leg) =>
      REBALANCE_LEG_FAILED.includes(
        normalizeRebalanceLegStatus(
          statusByAsset.get(leg.asset.toUpperCase()) ?? '',
        ) as (typeof REBALANCE_LEG_FAILED)[number],
      ),
    )
    const allLegsTerminal = legs.every((leg) => {
      const status = normalizeRebalanceLegStatus(
        statusByAsset.get(leg.asset.toUpperCase()) ?? '',
      )
      return (
        REBALANCE_LEG_COMPLETED.includes(status as (typeof REBALANCE_LEG_COMPLETED)[number]) ||
        REBALANCE_LEG_FAILED.includes(status as (typeof REBALANCE_LEG_FAILED)[number])
      )
    })
    if (executionPhase === 'failed' && allLegsTerminal && hasFailedLeg) {
      states[finalIndex] = 'failed'
    }
  }

  return states
}

/** Stepper rééquilibrage manuel : plan → ventes → achats → finalisation. */
export function buildBundleRebalancingProcessingStepsDynamic(params: {
  bundleLabel: string
  legs: BundleRebalancingLeg[]
}): TransactionStep[] {
  const { bundleLabel, legs } = params
  const steps: TransactionStep[] = [
    {
      label: 'Calcul du plan',
      subtext: `Estimation du rééquilibrage pour ${bundleLabel}.`,
    },
  ]

  for (const leg of legs) {
    const label = displayBundleAssetLabel(leg.asset)
    const amount = formatRebalanceLegAmount(leg.amount_entry, leg.entry_asset ?? 'USDC')
    if (leg.action === 'sell') {
      steps.push({
        label: `Vente · ${label}`,
        subtext: amount ? `Vente de ${label} pour ${amount}.` : `Vente de la position ${label}.`,
      })
    } else {
      steps.push({
        label: `Achat · ${label}`,
        subtext: amount ? `Achat de ${label} pour ${amount}.` : `Achat de ${label}.`,
      })
    }
  }

  steps.push({
    label: 'Mise à jour du portefeuille',
    subtext: 'Synchronisation de votre allocation cible.',
  })

  return steps
}

/** Index stepper rééquilibrage — monotone (ne recule pas en signing). */
export function bundleRebalancingDynamicProcessingProgressIndex(
  progress: BundleRebalancingProcessingProgress,
  stepCount: number,
): number {
  const legTotal = Math.max(0, progress.legTotal ?? 0)
  const lastIndex = Math.max(0, stepCount - 1)

  switch (progress.stage) {
    case 'preparing':
      return 0
    case 'executing': {
      const leg = Math.max(1, progress.legCurrent ?? 1)
      return Math.min(1 + leg, Math.max(1 + legTotal, 1))
    }
    case 'finalizing':
      return Math.min(1 + legTotal + 1, lastIndex)
    case 'completed':
      return stepCount
    default:
      return 0
  }
}

export function bundleActiveOperationProgressIndex(params: {
  v3Status: string | undefined
  assetLines: Array<{ asset: string; status: string }>
  stepCount: number
  includeFundingStep: boolean
}): number {
  const { v3Status, assetLines, stepCount, includeFundingStep } = params
  const lastIndex = Math.max(0, stepCount - 1)
  const fundingOffset = includeFundingStep ? 1 : 0

  if (v3Status === 'QUEUED') {
    return Math.min(fundingOffset, lastIndex)
  }

  if (!assetLines.length) {
    return Math.min(fundingOffset + 1, lastIndex)
  }

  const completed = assetLines.filter((line) =>
    ['completed', 'confirmed', 'success'].includes(String(line.status).toLowerCase()),
  ).length
  const hasPending = assetLines.some((line) =>
    ['pending', 'signing', 'running', 'planned'].includes(String(line.status).toLowerCase()),
  )

  if (isTerminalBundleV3Status(v3Status)) {
    return stepCount
  }

  if (hasPending) {
    return Math.min(fundingOffset + 1 + Math.max(1, completed + 1), lastIndex)
  }

  return Math.min(fundingOffset + 1 + completed, lastIndex)
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
  const raw = error instanceof Error ? error.message : String(error)
  const msg = resolveBundleInvestErrorMessage(raw)
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
