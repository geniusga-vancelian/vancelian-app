/**
 * Mapper Swap LI.FI → Transaction UX Framework V1 (R4.5-C).
 */
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'
import type { SwapQuotePayload } from '@/lib/portal/swapClient'
import { SWAP_FLOW_UI } from '@/components/portal/transaction/mappers/swapUiCopy'
import type { TransactionStep, TransactionTerminalFailureCopy } from '@/components/portal/transaction/types'
import type { TransactionTechnicalDetailsRow } from '@/components/portal/transaction/types'

export const SWAP_PROCESSING_STEP_DEFS: Array<{
  label: string
  defaultSub: (ctx: SwapProcessingContext) => string
}> = [
  {
    label: 'Preparing exchange',
    defaultSub: (ctx) =>
      `Checking your balance and preparing your ${ctx.fromAsset} → ${ctx.toAsset} exchange.`,
  },
  {
    label: 'Signature',
    defaultSub: () => 'Confirm the operation in your wallet.',
  },
  {
    label: 'Executing exchange',
    defaultSub: (ctx) => `Converting your ${ctx.fromAsset} to ${ctx.toAsset}.`,
  },
  {
    label: 'Receiving assets',
    defaultSub: (ctx) => `Crediting ${ctx.receiveLabel} to your wallet.`,
  },
]

export type SwapProcessingContext = {
  fromAsset: string
  toAsset: string
  payLabel: string
  receiveLabel: string
}

export const SWAP_PROCESSING_COMPLETED_INDEX = 4

export const SWAP_TERMINAL_FAILURE_COPY: TransactionTerminalFailureCopy = {
  title: 'Unable to complete exchange',
  lines: ['No assets were exchanged.'],
}

const FORBIDDEN_USER_PATTERN =
  /revert|retryable_failed|group_key|logical_borrow_id|idempotency|lifi|li\.fi|token approval|tx reverted|0x[a-f0-9]{8,}/i

/** Index stepper produit (0–3) ; 4 = terminé. */
export function swapProcessingStepperIndex(phase: SwapExecutionPhase): number {
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

export function buildSwapProcessingSteps(ctx: SwapProcessingContext): TransactionStep[] {
  return SWAP_PROCESSING_STEP_DEFS.map((step) => ({
    label: step.label,
    subtext: step.defaultSub(ctx),
  }))
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
    { label: 'Network', value: SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain },
  ]

  if (quote.exchange_rate) {
    rows.push({
      label: 'Rate',
      value: `1 ${quote.from_asset} ≈ ${quote.estimated_receive} ${quote.to_asset}`,
    })
  }

  if (quote.signing_wallet_address) {
    const walletLabel =
      quote.signing_wallet_mode === 'external_evm' ? 'External wallet' : 'Vancelian wallet'
    rows.push({
      label: 'Signer',
      value: `${walletLabel} · ${quote.signing_wallet_address.slice(0, 6)}…${quote.signing_wallet_address.slice(-4)}`,
    })
  }

  return rows
}
