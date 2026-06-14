/**
 * Mapper Swap LI.FI → Transaction UX Framework V1 (R4.5-C).
 */
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  SwapExecutionError,
  userMessageForSwapFailureCode,
  type SwapFailureCode,
} from '@/lib/portal/swapFailure'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { SWAP_FLOW_UI } from '@/components/portal/transaction/mappers/swapUiCopy'
import type {
  TransactionResultSuccessStep,
  TransactionResultSummaryRow,
  TransactionStep,
  TransactionTerminalFailureCopy,
} from '@/components/portal/transaction/types'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'

export const SWAP_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: SwapProcessingContext) => string
}> = [
  {
    label: 'Vérification du prix',
    defaultSub: () =>
      'Nous actualisons le dernier prix avant de lancer la signature.',
  },
  {
    label: "Autorisation de l'échange",
    defaultSub: (ctx) =>
      `Vous autorisez l'échange de ${ctx.payLabel} ${ctx.fromAsset}.`,
  },
  {
    label: 'Signature',
    defaultSub: () => 'Confirmez l’opération dans votre wallet.',
  },
  {
    label: 'Exécution de l’échange',
    defaultSub: (ctx) => `Conversion de ${ctx.fromAsset} vers ${ctx.toAsset}.`,
  },
  {
    label: 'Réception dans votre wallet',
    defaultSub: (ctx) => `Crédit de ${ctx.receiveLabel} sur votre portefeuille Vancelian.`,
  },
]

export type SwapProcessingContext = {
  fromAsset: string
  toAsset: string
  payLabel: string
  receiveLabel: string
}

export const SWAP_PROCESSING_COMPLETED_INDEX = 5

/**
 * PR4 / PR4.1 — stepper du mode autoritaire / enqueue-and-wait. Le serveur exécute le swap :
 * pas d'étape d'autorisation/signature côté navigateur. L'étape de file est **dynamique** et
 * distingue deux situations très différentes (vérité backend `queue_state`) :
 *   A. swap accepté, le worker va le préparer → « Préparation de l'échange » (cas nominal,
 *      aucune autre opération — ne JAMAIS afficher « une autre opération en cours ») ;
 *   B. swap qui attend qu'une autre opération financière se termine (un autre intent détient le
 *      slot user) → « En attente dans la file de traitement ».
 */
export type SwapAuthoritativeStepOptions = {
  /** Vrai uniquement si une AUTRE opération financière détient le slot (queue_state=waiting_for_previous). */
  waitingForPrevious?: boolean
}

export const SWAP_AUTHORITATIVE_COMPLETED_INDEX = 5

/** Index stepper autoritaire (0–4) ; 5 = terminé. */
export function swapAuthoritativeStepperIndex(phase: SwapExecutionPhase): number {
  switch (phase) {
    case 'idle':
    case 'verifying_price':
      return 0
    // File d'attente ET préparation partagent la même étape (libellé dynamique) : un swap qui
    // n'attend personne ne doit jamais afficher « une autre opération est en cours ».
    case 'queued':
    case 'preparing':
      return 1
    case 'server_executing':
    case 'signing':
    case 'submitting':
      return 2
    case 'confirming':
    case 'bridging':
      return 3
    case 'completed':
      return 5
    default:
      return 0
  }
}

export function buildSwapAuthoritativeProcessingSteps(
  ctx: SwapProcessingContext,
  opts: SwapAuthoritativeStepOptions = {},
): TransactionStep[] {
  const queueStep: TransactionStep = opts.waitingForPrevious
    ? {
        label: 'En attente dans la file de traitement',
        subtext:
          'Une autre opération financière est en cours. Votre échange démarrera automatiquement ensuite.',
      }
    : {
        label: "Préparation de l'échange",
        subtext: 'Votre demande a été reçue. Nous préparons son exécution.',
      }
  return [
    {
      label: 'Demande reçue',
      subtext: 'Votre échange a été accepté et placé dans la file de traitement.',
    },
    queueStep,
    {
      label: 'Exécution on-chain',
      subtext: `Exécution de l’échange ${ctx.fromAsset} → ${ctx.toAsset} sur la blockchain.`,
    },
    {
      label: 'Confirmation de la transaction',
      subtext: 'Confirmation de la transaction sur la blockchain.',
    },
    {
      label: 'Terminé',
      subtext: `Crédit de ${ctx.receiveLabel} sur votre portefeuille Vancelian.`,
    },
  ]
}

export const SWAP_TERMINAL_FAILURE_COPY: TransactionTerminalFailureCopy = {
  title: "Impossible de finaliser l'échange",
  lines: ['Aucun actif n’a été échangé.'],
}

/** Jargon interne / dumps hex — masqué. Les messages wallet formatés passent. */
const INTERNAL_ERROR_PATTERN =
  /retryable_failed|group_key|logical_borrow_id|idempotency|0x[a-f0-9]{40,}/i

const SWAP_USER_FACING_HINT_PATTERN =
  /approbation|solde .+ insuffisant|wallet vancelian|metamask|refusé sur|transaction refusée|quote expirée|devis a expiré|montant|estimation/i

/** Index stepper produit (0–4) ; 5 = terminé. */
export function swapProcessingStepperIndex(phase: SwapExecutionPhase): number {
  switch (phase) {
    case 'verifying_price':
    case 'preparing':
      return 0
    case 'approving':
      return 1
    case 'signing':
      return 2
    case 'submitting':
      return 3
    case 'bridging':
      return 4
    case 'completed':
      return 5
    default:
      return 0
  }
}

export function buildSwapProcessingSteps(ctx: SwapProcessingContext): TransactionStep[] {
  return SWAP_PROCESSING_STEP_DEFS.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
}

/** Preview accordéon sur l’écran Confirmation (même contenu que processing, libellés handoff). */
export function buildSwapReviewPreviewSteps(ctx: SwapProcessingContext): TransactionStep[] {
  return buildSwapProcessingSteps(ctx)
}

export function buildSwapSuccessSteps(ctx: SwapProcessingContext): TransactionResultSuccessStep[] {
  return buildSwapProcessingSteps(ctx).map((step) => ({
    name: step.label,
    body: step.subtext,
  }))
}

export function buildSwapSuccessSummary(
  quote: SwapQuotePayload,
  ctx: SwapProcessingContext,
): TransactionResultSummaryRow[] {
  const rows: TransactionResultSummaryRow[] = [
    { k: 'Vous avez échangé', v: `${ctx.payLabel} ${ctx.fromAsset}` },
    { k: `${ctx.toAsset} reçus`, v: ctx.receiveLabel },
  ]
  if (quote.exchange_rate) {
    rows.push({
      k: 'Taux',
      v: `1 ${ctx.fromAsset} ≈ ${formatSwapCryptoAmount(quote.exchange_rate, ctx.toAsset)} ${ctx.toAsset}`,
    })
  }
  rows.push({ k: 'Frais Vancelian', v: 'Offerts' })
  return rows
}

export function resolveSwapFailureCopy(error: unknown): TransactionTerminalFailureCopy {
  if (error == null) {
    return SWAP_TERMINAL_FAILURE_COPY
  }
  if (error instanceof SwapExecutionError) {
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [error.userMessage, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
    }
  }
  const msg = error instanceof Error ? error.message : String(error)
  const codeMatch = /^(user_rejected_signature|user_rejected_approval|wallet_mismatch|quote_expired|insufficient_funds|wallet_error|rpc_error|lifi_error|unknown_error)$/.exec(
    msg.trim(),
  )
  if (codeMatch) {
    const userLine = userMessageForSwapFailureCode(codeMatch[1] as SwapFailureCode)
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [userLine, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
    }
  }
  if (msg.includes('Quote expirée') || /quote expired/i.test(msg)) {
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [SWAP_FLOW_UI.quoteExpiredLine, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
    }
  }
  if (msg.includes('légèrement changé') || msg.includes('price_changed')) {
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [SWAP_FLOW_UI.priceChangedLine, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
    }
  }
  if (INTERNAL_ERROR_PATTERN.test(msg)) {
    return SWAP_TERMINAL_FAILURE_COPY
  }
  if (SWAP_USER_FACING_HINT_PATTERN.test(msg)) {
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [msg, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
    }
  }
  if (/execution reverted|tx reverted|revert on-chain/i.test(msg)) {
    return {
      title: SWAP_TERMINAL_FAILURE_COPY.title,
      lines: [
        'L’échange n’a pas pu être exécuté on-chain. Refaites une estimation depuis l’étape montant.',
        SWAP_TERMINAL_FAILURE_COPY.lines[0]!,
      ],
    }
  }
  if (
    msg.includes('Swap échoué') ||
    msg.includes('Swap failed') ||
    msg.includes('Swap non confirmé') ||
    msg.includes('Exécution impossible')
  ) {
    return SWAP_TERMINAL_FAILURE_COPY
  }
  return {
    title: SWAP_TERMINAL_FAILURE_COPY.title,
    lines: [msg, SWAP_TERMINAL_FAILURE_COPY.lines[0]!],
  }
}

export function buildSwapTechnicalDetailRows(quote: SwapQuotePayload): TransactionTechnicalDetailsRow[] {
  const routeLabel =
    quote.route_steps.length > 0
      ? quote.route_steps.map((step) => step.label).join(' → ')
      : `${SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain} → ${SWAP_CHAIN_LABELS[quote.to_chain] ?? quote.to_chain}`

  const rows: TransactionTechnicalDetailsRow[] = [
    { label: 'Route', value: routeLabel },
    { label: 'Réseau', value: SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain },
  ]

  if (quote.exchange_rate) {
    rows.push({
      label: 'Taux',
      value: `1 ${quote.from_asset} ≈ ${quote.estimated_receive} ${quote.to_asset}`,
    })
  }

  if (quote.signing_wallet_address) {
    const walletLabel =
      quote.signing_wallet_mode === 'external_evm' ? 'Wallet externe' : 'Wallet Vancelian'
    rows.push({
      label: 'Signataire',
      value: `${walletLabel} · ${quote.signing_wallet_address.slice(0, 6)}…${quote.signing_wallet_address.slice(-4)}`,
    })
  }

  return rows
}
