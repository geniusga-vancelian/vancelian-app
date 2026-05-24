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
}

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
  const data = (await res.json()) as T & { detail?: { message?: string } }
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('Session expirée — reconnectez-vous pour continuer.')
    }
    const message =
      (data as { detail?: { message?: string } }).detail?.message ??
      (data as { message?: string }).message ??
      'Swap request failed'
    throw new Error(message)
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
}): Promise<SwapQuotePayload> {
  const res = await fetch('/api/portal/swaps/quote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return parseJson(res)
}

export async function executeSwap(swapId: string): Promise<SwapExecutePayload> {
  const res = await fetch('/api/portal/swaps/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ swap_id: swapId }),
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

export async function fetchSwapStatus(swapId: string): Promise<SwapStatusPayload> {
  const res = await fetch(`/api/portal/swaps/${swapId}`, { cache: 'no-store' })
  return parseJson(res)
}
