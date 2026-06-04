/**
 * Mapper Swap LI.FI → Transaction UX Framework V1 (R4.5-C).
 */
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
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

export const SWAP_TERMINAL_FAILURE_COPY: TransactionTerminalFailureCopy = {
  title: "Impossible de finaliser l'échange",
  lines: ['Aucun actif n’a été échangé.'],
}

const FORBIDDEN_USER_PATTERN =
  /revert|retryable_failed|group_key|logical_borrow_id|idempotency|lifi|li\.fi|token approval|tx reverted|0x[a-f0-9]{8,}/i

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
      v: `1 ${ctx.fromAsset} ≈ ${formatSwapCryptoAmount(quote.exchange_rate)} ${ctx.toAsset}`,
    })
  }
  rows.push({ k: 'Frais Vancelian', v: 'Offerts' })
  return rows
}

export function resolveSwapFailureCopy(error: unknown): TransactionTerminalFailureCopy {
  if (error == null) {
    return SWAP_TERMINAL_FAILURE_COPY
  }
  const msg = error instanceof Error ? error.message : String(error)
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
  if (FORBIDDEN_USER_PATTERN.test(msg)) {
    return SWAP_TERMINAL_FAILURE_COPY
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
