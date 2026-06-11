/**
 * Swap wallet virtuel de A à Z (ADR 008) :
 * quote API → confirm LI.FI → signature Privy → poll → comptabilité serveur.
 */
import {
  runPortalSwapLeg,
  type PortalSwapLegDeps,
  type PortalSwapLegResult,
} from '@/lib/portal/runPortalSwapLeg'
import type { BundleLegQuoteSnapshot } from '@/lib/portal/bundleLegQuoteConfirm'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

export type VirtualWalletSwapSide = 'buy' | 'sell'

export type VirtualWalletSwapParams = {
  walletFromId: string
  walletToId: string
  volumeFrom: string
  volumeTo?: string
  side: VirtualWalletSwapSide
  portfolioId: string
  correlationId: string
  legId: string
  batchId: string
  bundleAction?: string
  legAction: string
  chain?: string
  metadata?: Record<string, unknown>
}

export type VirtualWalletSwapQuotePayload = {
  phase: 'awaiting_signature'
  swap_id: string
  from_asset: string
  to_asset: string
  amount_in: string
  estimated_receive?: string | null
  status: string
  requires_client_signature: boolean
  review_snapshot: BundleLegQuoteSnapshot
}

export type VirtualWalletSwapResult = PortalSwapLegResult & {
  fromAsset: string
  toAsset: string
  side: VirtualWalletSwapSide
  amountIn: string
  estimatedReceive: string
}

export type VirtualWalletSwapDeps = PortalSwapLegDeps

/** Swap déjà quoté côté serveur (rééquilibrage) — pas de re-quote API. */
export type QuotedVirtualWalletSwap = {
  swapId: string
  reviewSnapshot: BundleLegQuoteSnapshot
  fromAsset: string
  toAsset?: string
  amountIn?: string
  estimatedReceive?: string
}

export type RunVirtualWalletSwapOptions = {
  quoted?: QuotedVirtualWalletSwap
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!text) {
    throw new Error('Réponse vide du serveur')
  }
  try {
    return JSON.parse(text) as T
  } catch {
    throw new Error(text.slice(0, 300))
  }
}

export async function quoteVirtualWalletSwap(
  params: VirtualWalletSwapParams,
): Promise<VirtualWalletSwapQuotePayload> {
  const res = await fetch('/api/portal/trade/wallet-swap/quote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      wallet_from_id: params.walletFromId,
      wallet_to_id: params.walletToId,
      quantity_from: params.volumeFrom,
      estimated_quantity_to: params.volumeTo ?? null,
      side: params.side,
      portfolio_id: params.portfolioId,
      correlation_id: params.correlationId,
      leg_id: params.legId,
      batch_id: params.batchId,
      bundle_action: params.bundleAction ?? 'rebalance_v3',
      leg_action: params.legAction,
      chain: params.chain ?? 'base',
      metadata: params.metadata ?? {},
    }),
    signal: AbortSignal.timeout(120_000),
  })
  if (!res.ok) {
    const err = (await parseJson<Record<string, string>>(res).catch(() => ({
      detail: res.statusText,
    }))) as Record<string, string | undefined>
    throw new Error(err.detail ?? err.message ?? err.error ?? 'Quote swap impossible')
  }
  return parseJson<VirtualWalletSwapQuotePayload>(res)
}

/**
 * Fonction unique côté portail : quote → sign Privy → poll → settlement comptable.
 * ``deps`` fournit signAndSubmit + pollUntilTerminal (useLifiSwapExecution).
 */
export async function runVirtualWalletSwap(
  params: VirtualWalletSwapParams,
  deps: VirtualWalletSwapDeps,
  options?: RunVirtualWalletSwapOptions,
): Promise<VirtualWalletSwapResult> {
  deps.onPhaseChange?.('preparing')

  const preQuoted = options?.quoted
  const quoted = preQuoted
    ? {
        swap_id: preQuoted.swapId,
        from_asset: preQuoted.fromAsset,
        to_asset: preQuoted.toAsset ?? '',
        amount_in: preQuoted.amountIn ?? params.volumeFrom,
        estimated_receive: preQuoted.estimatedReceive ?? params.volumeTo ?? '0',
        review_snapshot: preQuoted.reviewSnapshot,
      }
    : await quoteVirtualWalletSwap(params)

  const leg = await runPortalSwapLeg(
    quoted.swap_id,
    quoted.review_snapshot,
    quoted.from_asset,
    deps,
  )

  return {
    ...leg,
    swapId: quoted.swap_id,
    fromAsset: quoted.from_asset,
    toAsset: quoted.to_asset,
    side: params.side,
    amountIn: quoted.amount_in,
    estimatedReceive:
      quoted.estimated_receive ?? quoted.review_snapshot.review_estimated_receive ?? '0',
  }
}

export type VirtualWalletSwapPhaseChange = (phase: SwapExecutionPhase) => void
