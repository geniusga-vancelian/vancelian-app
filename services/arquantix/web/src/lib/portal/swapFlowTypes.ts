import {
  BASE_SWAP_TRADE_ASSETS,
  isBaseSwapTradeAsset,
  type BaseSwapTradeAsset,
} from '@/lib/portal/baseAllowedAssets'
import type { SwapQuotePayload, SwapSupportedAssetsPayload } from '@/lib/portal/swapClient'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'

export type PortalSwapFlowStep = 'to' | 'from' | 'amount' | 'confirm'

export type SwapCatalogAsset = SwapSupportedAssetsPayload['assets'][number]

export type SwapExecutionPhase =
  | 'idle'
  | 'preparing'
  | 'approving'
  | 'signing'
  | 'submitting'
  | 'bridging'
  | 'completed'
  | 'failed'

export type PortalSwapFlowState = {
  step: PortalSwapFlowStep
  toAsset: string
  toChain: string
  fromAsset: string
  fromChain: string
  amount: string
  quote: SwapQuotePayload | null
  sourcePosition: PortalCryptoPosition | null
  executionPhase: SwapExecutionPhase
  executionError: string | null
}

export const INITIAL_SWAP_FLOW_STATE: PortalSwapFlowState = {
  step: 'to',
  toAsset: '',
  toChain: '',
  fromAsset: '',
  fromChain: '',
  amount: '',
  quote: null,
  sourcePosition: null,
  executionPhase: 'idle',
  executionError: null,
}

export const SWAP_V1_EVM_CHAINS = ['base'] as const

/** Pilote produit — swaps same-chain sur Base uniquement (Li.FI, voir API). */
export const SWAP_V1_SAME_CHAIN_ONLY = true
export const SWAP_V1_PILOT_CHAINS = ['base'] as const
export type SwapV1PilotChain = (typeof SWAP_V1_PILOT_CHAINS)[number]

export const SWAP_V1_TOKENS = ['USDC', 'EURC', 'ETH'] as const

/** Actifs échangeables via le flow swap portail (Base / Li.FI). */
export const PORTAL_SWAP_TRADE_ASSETS = BASE_SWAP_TRADE_ASSETS

export type SwapV1Token = (typeof SWAP_V1_TOKENS)[number]

export type PortalSwapTradeAsset = BaseSwapTradeAsset

export function isSwapV1Token(symbol: string): symbol is SwapV1Token {
  return SWAP_V1_TOKENS.includes(symbol.toUpperCase() as SwapV1Token)
}

export function isPortalSwapTradeAsset(symbol: string): symbol is PortalSwapTradeAsset {
  return isBaseSwapTradeAsset(symbol)
}

export type PortalSwapUrlIntent =
  | { mode: 'buy'; toAsset: string; toChain: string }
  | { mode: 'sell'; fromAsset: string; fromChain: string }
  | { mode: 'full' }

/** Lit `?to=` (buy) ou `?from=` (sell) — ne dépend pas du catalogue API. */
export function parsePortalSwapUrlIntent(
  params: URLSearchParams | null,
  activeSwapChain: string | null,
): PortalSwapUrlIntent {
  if (!params) return { mode: 'full' }

  const resolveChain = (paramKey: 'fromChain' | 'toChain'): string | null => {
    const fromUrl = params.get(paramKey)?.trim().toLowerCase()
    if (fromUrl && isSwapV1PilotChain(fromUrl)) return fromUrl
    if (activeSwapChain && isSwapV1PilotChain(activeSwapChain)) return activeSwapChain
    return null
  }

  const fromParam = params.get('from')?.trim().toUpperCase() ?? ''
  if (fromParam && isPortalSwapTradeAsset(fromParam)) {
    const fromChain = resolveChain('fromChain')
    if (fromChain) return { mode: 'sell', fromAsset: fromParam, fromChain }
  }

  const toParam = params.get('to')?.trim().toUpperCase() ?? ''
  if (toParam && isPortalSwapTradeAsset(toParam)) {
    const toChain = resolveChain('toChain')
    if (toChain) return { mode: 'buy', toAsset: toParam, toChain }
  }

  return { mode: 'full' }
}

export function isSwapV1EvmChain(chain: string): boolean {
  return SWAP_V1_EVM_CHAINS.includes(chain.toLowerCase() as (typeof SWAP_V1_EVM_CHAINS)[number])
}

export function isSwapV1PilotChain(chain: string): boolean {
  return SWAP_V1_PILOT_CHAINS.includes(chain.toLowerCase() as SwapV1PilotChain)
}

export function filterSwapV1Assets(assets: SwapCatalogAsset[]): SwapCatalogAsset[] {
  return assets
    .filter((a) => isPortalSwapTradeAsset(a.symbol))
    .map((a) => ({
      ...a,
      chains: a.chains.filter((c) => isSwapV1EvmChain(c)),
    }))
    .filter((a) => a.chains.length > 0)
}

export function pickSwapCatalogLists(catalog: SwapSupportedAssetsPayload) {
  const source = filterSwapV1Assets(catalog.source_assets ?? catalog.assets)
  const destination = filterSwapV1Assets(catalog.destination_assets ?? catalog.assets)
  return { source, destination }
}

/** Filtre le catalogue pour le réseau navbar actif (chaînes déjà restreintes côté API). */
export function pickSwapCatalogListsForChain(
  catalog: SwapSupportedAssetsPayload,
  chainKey: string | null,
) {
  const { source, destination } = pickSwapCatalogLists(catalog)
  if (!chainKey) {
    return { source: [], destination: [] }
  }

  const onChain = (assets: SwapCatalogAsset[]) =>
    assets
      .map((asset) => ({
        ...asset,
        chains: asset.chains.filter((chain) => chain === chainKey),
      }))
      .filter((asset) => asset.chains.length > 0)

  return {
    source: onChain(source),
    destination: onChain(destination),
  }
}

export const SWAP_CHAIN_LABELS: Record<string, string> = {
  base: 'Base',
}
