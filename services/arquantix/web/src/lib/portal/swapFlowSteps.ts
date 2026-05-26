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
        ? `Taux estimé : 1 ${quote.from_asset} ≈ ${formatSwapCryptoAmount(quote.exchange_rate)} ${quote.to_asset}`
        : 'Route optimisée via LI.FI',
      state: routeStepState(executionPhase),
    },
    {
      number: 2,
      title: 'Conversion estimée',
      primary: `${formatSwapCryptoAmount(quote.amount_in)} ${quote.from_asset} → ≈ ${formatSwapCryptoAmount(quote.estimated_receive)} ${quote.to_asset}`,
      secondary: `Minimum garanti : ${formatSwapCryptoAmount(quote.estimated_receive_min)} ${quote.to_asset}`,
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

export function processingPhaseLabel(phase: SwapExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Préparation de la route...'
    case 'approving':
      return 'Basculez sur Ethereum si demandé, puis signez l’approbation USDT dans MetaMask…'
    case 'signing':
      return 'Signature du swap dans votre wallet...'
    case 'submitting':
      return 'Envoi de la transaction...'
    case 'bridging':
      return 'Finalisation sur la blockchain...'
    case 'completed':
      return 'Conversion effectuée'
    case 'failed':
      return 'Échec de la conversion'
    default:
      return 'Traitement en cours...'
  }
}

export function formatSwapFeeLine(quote: SwapQuotePayload): string {
  const parts: string[] = []
  if (Number(quote.vancelian_fee) > 0) {
    parts.push(`${formatSwapCryptoAmount(quote.vancelian_fee)} ${quote.from_asset} (Vancelian)`)
  }

  const isPrivySponsored = quote.signing_wallet_mode !== 'external_evm'
  if (isPrivySponsored) {
    parts.push('0 (réseau · sponsorisé)')
    return parts.join(' · ')
  }

  const networkUsd = quote.network_fee_usd ? Number(quote.network_fee_usd) : 0
  const amountIn = Number(quote.amount_in)
  const maxSaneUsd = Number.isFinite(amountIn) && amountIn > 0 ? Math.max(5, amountIn * 1.5) : 5

  if (networkUsd > 0 && networkUsd <= maxSaneUsd) {
    parts.push(`≈ ${formatSwapFiatAmount(networkUsd)} (réseau)`)
  } else if (Number(quote.network_fee) > 0 && quote.network_fee_asset === 'USD') {
    const legacyUsd = Number(quote.network_fee)
    if (legacyUsd > 0 && legacyUsd <= maxSaneUsd) {
      parts.push(`≈ ${formatSwapFiatAmount(legacyUsd)} (réseau)`)
    }
  } else if (Number(quote.network_fee) > 0) {
    const networkFee = Number(quote.network_fee)
    const asset = quote.network_fee_asset ?? quote.from_asset
    const maxSaneToken = Number.isFinite(amountIn) && amountIn > 0 ? amountIn * 2 : networkFee
    if (networkFee <= maxSaneToken) {
      parts.push(`${formatSwapCryptoAmount(quote.network_fee)} ${asset} (réseau)`)
    }
  }

  return parts.length > 0 ? parts.join(' · ') : 'Aucun'
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
