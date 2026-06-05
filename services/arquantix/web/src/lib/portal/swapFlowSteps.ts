import type { SwapQuotePayload } from '@/lib/portal/swapClient'
import type { SwapStepState, SwapTransactionStep } from '@/components/portal/swap/PortalSwapTransactionSteps'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { formatSwapCryptoAmount } from '@/lib/portal/swapFlowFormat'
import { SWAP_CHAIN_LABELS } from '@/lib/portal/swapFlowTypes'

export function buildConfirmSteps(
  quote: SwapQuotePayload,
  executionPhase: SwapExecutionPhase,
): SwapTransactionStep[] {
  const routeLabel =
    quote.route_steps.length > 0
      ? quote.route_steps.map((s) => s.label).join(' → ')
      : `Route ${SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain} → ${SWAP_CHAIN_LABELS[quote.to_chain] ?? quote.to_chain}`

  return [
    {
      number: 1,
      title: 'Préparation de la route',
      primary: routeLabel,
      secondary: quote.exchange_rate
        ? `Taux estimé : 1 ${quote.from_asset} ≈ ${formatSwapCryptoAmount(quote.exchange_rate, quote.to_asset)} ${quote.to_asset}`
        : 'Route optimisée',
      state: routeStepState(executionPhase),
    },
    {
      number: 2,
      title: 'Conversion estimée',
      primary: `${formatSwapCryptoAmount(quote.amount_in, quote.from_asset)} ${quote.from_asset} → ≈ ${formatSwapCryptoAmount(quote.estimated_receive, quote.to_asset)} ${quote.to_asset}`,
      secondary: `Minimum garanti : ${formatSwapCryptoAmount(quote.estimated_receive_min, quote.to_asset)} ${quote.to_asset}`,
      approximate: true,
      state: conversionStepState(executionPhase),
    },
  ]
}

function routeStepState(phase: SwapExecutionPhase): SwapStepState {
  if (phase === 'idle' || phase === 'failed') return 'pending'
  if (phase === 'preparing' || phase === 'approving' || phase === 'signing') return 'processing'
  return 'completed'
}

function conversionStepState(phase: SwapExecutionPhase): SwapStepState {
  if (phase === 'idle' || phase === 'failed') return 'pending'
  if (phase === 'preparing' || phase === 'approving' || phase === 'signing') return 'pending'
  if (phase === 'submitting' || phase === 'bridging') return 'processing'
  return 'completed'
}

export function processingPhaseLabel(
  phase: SwapExecutionPhase,
  quote?: Pick<SwapQuotePayload, 'from_chain' | 'from_asset' | 'signing_wallet_mode'> | null,
): string {
  const chainLabel = quote ? (SWAP_CHAIN_LABELS[quote.from_chain] ?? quote.from_chain) : 'the selected network'
  const asset = quote?.from_asset ?? 'token'
  const isExternal = quote?.signing_wallet_mode === 'external_evm'

  switch (phase) {
    case 'preparing':
      return 'Preparing route…'
    case 'approving':
      return isExternal
        ? `Approve ${asset} on ${chainLabel} in MetaMask…`
        : `Approving ${asset} on ${chainLabel}…`
    case 'signing':
      return isExternal
        ? `Sign swap on ${chainLabel} in MetaMask…`
        : `Signing swap on ${chainLabel}…`
    case 'submitting':
      return 'Submitting transaction…'
    case 'bridging':
      return 'Confirming on-chain…'
    case 'completed':
      return 'Swap completed'
    case 'failed':
      return 'Swap failed'
    default:
      return 'Processing…'
  }
}

export function swapConfirmCtaLabel(args: {
  executing: boolean
  executionPhase: SwapExecutionPhase
  amount: string
  fromAsset: string
  quote?: Pick<SwapQuotePayload, 'from_chain' | 'from_asset' | 'signing_wallet_mode'> | null
}): string {
  if (!args.executing || args.executionPhase === 'idle') {
    return `Confirm swap · ${args.amount} ${args.fromAsset}`
  }
  return processingPhaseLabel(args.executionPhase, args.quote)
}

export function formatSwapFeeLine(quote: SwapQuotePayload): string {
  const parts: string[] = []
  if (Number(quote.vancelian_fee) > 0) {
    parts.push(`${formatSwapCryptoAmount(quote.vancelian_fee, quote.from_asset)} ${quote.from_asset} (Vancelian)`)
  }

  const isPrivySponsored = quote.signing_wallet_mode !== 'external_evm'
  if (isPrivySponsored) {
    parts.push('0 (network · sponsored)')
    return parts.join(' · ')
  }

  const networkUsd = quote.network_fee_usd ? Number(quote.network_fee_usd) : 0
  const amountIn = Number(quote.amount_in)
  const maxSaneUsd = Number.isFinite(amountIn) && amountIn > 0 ? Math.max(5, amountIn * 1.5) : 5

  if (networkUsd > 0 && networkUsd <= maxSaneUsd) {
    parts.push(`≈ ${formatSwapFiatAmount(networkUsd)} (network)`)
  } else if (Number(quote.network_fee) > 0 && quote.network_fee_asset === 'USD') {
    const legacyUsd = Number(quote.network_fee)
    if (legacyUsd > 0 && legacyUsd <= maxSaneUsd) {
      parts.push(`≈ ${formatSwapFiatAmount(legacyUsd)} (network)`)
    }
  } else if (Number(quote.network_fee) > 0) {
    const networkFee = Number(quote.network_fee)
    const asset = quote.network_fee_asset ?? quote.from_asset
    const maxSaneToken = Number.isFinite(amountIn) && amountIn > 0 ? amountIn * 2 : networkFee
    if (networkFee <= maxSaneToken) {
      parts.push(`${formatSwapCryptoAmount(quote.network_fee, asset)} (network)`)
    }
  }

  return parts.length > 0 ? parts.join(' · ') : 'None'
}

function formatSwapFiatAmount(value: number): string {
  if (!Number.isFinite(value)) return '$0'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}
