/** Actifs Base autorisés — aligné sur `api/config/base_allowed_assets.py`. */
import { filterPortalEuroStablecoinSymbols, isPortalEuroFeaturesEnabled } from '@/lib/portal/portalEuroVisibility'

const ALL_BASE_ALLOWED_ASSETS = [
  { symbol: 'ETH', name: 'Ethereum' },
  { symbol: 'CBETH', name: 'Ethereum' },
  { symbol: 'USDC', name: 'USD Coin' },
  { symbol: 'EURC', name: 'Euro Coin' },
  { symbol: 'CBBTC', name: 'Bitcoin' },
  { symbol: 'LINK', name: 'Chainlink' },
  { symbol: 'AAVE', name: 'Aave' },
  { symbol: 'UNI', name: 'Uniswap' },
] as const

export const BASE_ALLOWED_ASSETS = (
  isPortalEuroFeaturesEnabled()
    ? ALL_BASE_ALLOWED_ASSETS
    : ALL_BASE_ALLOWED_ASSETS.filter((asset) => asset.symbol !== 'EURC')
) as typeof ALL_BASE_ALLOWED_ASSETS

export type BaseAllowedSymbol = (typeof BASE_ALLOWED_ASSETS)[number]['symbol']

export const BASE_ALLOWED_SYMBOLS = BASE_ALLOWED_ASSETS.map((a) => a.symbol)

/** Paires Binance pour cotation marché (provider_symbol). */
export const BASE_MARKET_PROVIDER_SYMBOLS = [
  'ETHUSDT',
  'USDCUSDT',
  'EURUSDT',
  'BTCUSDT',
  'LINKUSDT',
  'AAVEUSDT',
  'UNIUSDT',
] as const

/** Actifs éligibles au flow swap Li.FI same-chain sur Base. */
const ALL_BASE_SWAP_TRADE_ASSETS = [
  'ETH',
  'CBETH',
  'USDC',
  'EURC',
  'CBBTC',
  'LINK',
  'AAVE',
  'UNI',
] as const

export const BASE_SWAP_TRADE_ASSETS = filterPortalEuroStablecoinSymbols(
  ALL_BASE_SWAP_TRADE_ASSETS,
) as unknown as typeof ALL_BASE_SWAP_TRADE_ASSETS

export type BaseSwapTradeAsset = (typeof BASE_SWAP_TRADE_ASSETS)[number]

export function isBaseSwapTradeAsset(symbol: string): symbol is BaseSwapTradeAsset {
  return BASE_SWAP_TRADE_ASSETS.includes(symbol.toUpperCase() as BaseSwapTradeAsset)
}

export function isBaseAllowedSymbol(symbol: string): boolean {
  const u = symbol.trim().toUpperCase()
  return BASE_ALLOWED_ASSETS.some((a) => a.symbol.toUpperCase() === u)
}
