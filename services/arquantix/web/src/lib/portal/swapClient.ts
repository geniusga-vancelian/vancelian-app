export type SwapSupportedAssetsPayload = {
  assets: Array<{
    symbol: string
    display_name: string
    kind?: string
    chains: string[]
    decimals: number
    min_amount: string
    max_amount: string
  }>
  source_assets?: SwapSupportedAssetsPayload['assets']
  destination_assets?: SwapSupportedAssetsPayload['assets']
  chains: Array<{ key: string; display_name: string; evm: boolean }>
  swap_fee_bps: number
  default_slippage_bps: number
  max_slippage_bps: number
  mock_mode?: boolean
}

export type SwapQuotePayload = {
  swap_id: string
  status: string
  from_asset: string
  to_asset: string
  from_chain: string
  to_chain: string
  amount_in: string
  vancelian_fee: string
  vancelian_fee_bps: number
  network_fee: string
  network_fee_asset?: string | null
  network_fee_usd?: string | null
  estimated_receive: string
  estimated_receive_min: string
  exchange_rate?: string | null
  estimated_duration_seconds?: number | null
  route_steps: Array<{ label: string; kind: string; chain: string }>
  expires_at: string
  slippage_bps: number
  signing_wallet_mode?: 'privy_embedded' | 'external_evm' | null
  signing_wallet_address?: string | null
}

export type SwapConfirmExecutePayload = {
  freshness: string
  quote: SwapQuotePayload
  execute: SwapExecutePayload
}

export type SwapPriceChangedPayload = {
  code: string
  message: string
  quote: SwapQuotePayload
  delta_bps: number
  slippage_bps: number
}

export class SwapPriceChangedError extends Error {
  readonly code = 'swap.price_changed'
  readonly freshQuote: SwapQuotePayload
  readonly deltaBps: number
  readonly slippageBps: number

  constructor(detail: SwapPriceChangedPayload) {
    super(detail.message)
    this.name = 'SwapPriceChangedError'
    this.freshQuote = detail.quote
    this.deltaBps = detail.delta_bps
    this.slippageBps = detail.slippage_bps
  }
}

export type SwapExecutePayload = {
  swap_id: string
  status: string
  lifecycle_message: string
  transaction?: {
    chain_id: number | string
    to: string
    data: string
    value: string
    gas_limit?: string | null
    gas_price?: string | null
  } | null
  lifi_tool?: string | null
  signing_wallet_mode?: 'privy_embedded' | 'external_evm' | null
  signing_wallet_address?: string | null
  token_approval?: {
    required: boolean
    token_address?: string | null
    spender_address?: string | null
    amount_atomic?: string | null
  } | null
}

const RETRYABLE_HTTP_STATUS = new Set([502, 503, 504])

export type SwapStatusPayload = {
  swap_id: string
  status: string
  lifecycle_message: string
  from_asset: string
  to_asset: string
  from_chain: string
  to_chain: string
  amount_in: string
  estimated_receive?: string | null
  tx_hash?: string | null
  error_message?: string | null
}

async function parseJson<T>(res: Response): Promise<T> {
  const data = (await res.json()) as T & {
    detail?: { message?: string; code?: string } | SwapPriceChangedPayload
  }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    if (res.status === 409) {
      const detail = data.detail
      if (
        detail &&
        typeof detail === 'object' &&
        'code' in detail &&
        detail.code === 'swap.price_changed'
      ) {
        throw new SwapPriceChangedError(detail as SwapPriceChangedPayload)
      }
    }
    const detail = data.detail
    const message =
      (typeof detail === 'object' && detail && 'message' in detail
        ? detail.message
        : undefined) ??
      (data as { message?: string }).message ??
      'Swap request failed'
    const err = new Error(message)
    if (RETRYABLE_HTTP_STATUS.has(res.status)) {
      ;(err as Error & { retryable?: boolean }).retryable = true
    }
    throw err
  }
  return data
}

export async function fetchSupportedSwapAssets(): Promise<SwapSupportedAssetsPayload> {
  const res = await fetch('/api/portal/swaps/supported-assets', { cache: 'no-store' })
  return parseJson(res)
}

export async function requestSwapQuote(body: {
  from_asset: string
  to_asset: string
  amount: string
  from_chain: string
  to_chain: string
  slippage_bps?: number
  signing_wallet_mode?: 'privy_embedded' | 'external_evm'
  signing_wallet_address?: string
}): Promise<SwapQuotePayload> {
  const res = await fetch('/api/portal/swaps/quote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson(res)
}

export async function confirmSwapExecution(body: {
  swap_id: string
  review_estimated_receive: string
  review_amount_in?: string
}): Promise<SwapConfirmExecutePayload> {
  const res = await fetch('/api/portal/swaps/confirm-execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(25_000),
  })
  return parseJson(res)
}

/** @deprecated Préférer confirmSwapExecution (refresh + slippage). */
export async function executeSwap(swapId: string): Promise<SwapExecutePayload> {
  const res = await fetch('/api/portal/swaps/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ swap_id: swapId }),
  })
  return parseJson(res)
}

export async function abandonSwap(swapId: string): Promise<SwapStatusPayload> {
  const res = await fetch(`/api/portal/swaps/${swapId}/abandon`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
    signal: AbortSignal.timeout(10_000),
  })
  return parseJson(res)
}

export async function submitSwapTx(swapId: string, txHash: string): Promise<SwapStatusPayload> {
  const res = await fetch(`/api/portal/swaps/${swapId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tx_hash: txHash }),
  })
  return parseJson(res)
}

export async function submitSwapApproval(
  swapId: string,
  approvalTxHash: string,
): Promise<SwapStatusPayload> {
  const res = await fetch(`/api/portal/swaps/${swapId}/approval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tx_hash: approvalTxHash }),
  })
  return parseJson(res)
}

export async function fetchSwapStatus(swapId: string): Promise<SwapStatusPayload> {
  const res = await fetch(`/api/portal/swaps/${swapId}`, { cache: 'no-store' })
  return parseJson(res)
}
