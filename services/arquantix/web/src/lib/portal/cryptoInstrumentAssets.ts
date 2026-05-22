/**
 * Logos crypto — aligné sur Flutter `crypto_instrument_svgs.dart` + `CryptoAvatar`.
 * Priorité : SVG packagé → logo API → PNG `/media/crypto_logos/{ticker}.png`.
 */

import { resolveMarketDataLogoUrl, getMarketDataPublicBaseUrl } from '@/lib/portal/marketDataPublic'

const QUOTE_SUFFIXES = ['USDT', 'USDC', 'BUSD', 'DAI', 'EUR', 'USD'] as const

const TICKER_ALIASES: Record<string, string> = {
  TRON: 'TRX',
  POL: 'MATIC',
  LUNA: 'LUNC',
  BSC: 'BNB',
}

/** Tickers présents dans `mobile/assets/crypto_svgs/` (export Figma). */
const BUNDLED_EXPORT_TICKERS = new Set([
  'AAVE', 'ADA', 'AED', 'AGLD', 'AKTIO', 'ALCX', 'ALGO', 'ALPINE', 'AMP', 'ANKR', 'ANT', 'APE',
  'ARB', 'ASI', 'ATOM', 'AUDIO', 'AVAX', 'AXS', 'BAL', 'BAT', 'BCH', 'BNB', 'BOND', 'BTC', 'BUSD',
  'CAKE', 'CELO', 'CHR', 'CHZ', 'CLV', 'COMP', 'CREAM', 'CRV', 'CVX', 'DAI', 'DENT', 'DOGE', 'DOT',
  'DYDX', 'ENJ', 'EOS', 'ETC', 'ETH', 'EUR', 'EURC', 'EURPAR', 'FET', 'FIL', 'FLUX', 'FTM', 'FTT',
  'FTX', 'GRT', 'HBAR', 'IOST', 'IOTEX', 'JTO', 'KAVA', 'KNC', 'KSM', 'LINK', 'LPT', 'LRC', 'LTC',
  'LUNC', 'MANA', 'MATIC', 'MDX', 'MKR', 'NEAR', 'NKN', 'NMR', 'NOT', 'OCEAN', 'OGN', 'OM', 'ONE',
  'OXT', 'PAXG', 'PEPE', 'PERP', 'QNT', 'REEF', 'REN', 'RENDER', 'REQ', 'RLC', 'RSR', 'RUNE', 'SAND',
  'SHIB', 'SKL', 'SKY', 'SNX', 'SOL', 'SONIC', 'SRM', 'STORJ', 'STX', 'SUI', 'SUSHI', 'THETA', 'TON',
  'TRX', 'TUSD', 'UMA',
  'UNI', 'USDC', 'USDT', 'VNC', 'WBTC', 'WLD', 'XEM', 'XLM', 'XRP', 'XTZ', 'YFI', 'YFII', 'YGG',
  'ZIL', 'ZRX',
])

/** Couleurs de fond — Flutter `AppColors.cryptoAssetBrand`. */
export const CRYPTO_ASSET_BRAND: Record<string, string> = {
  EUR: '#2196F3',
  BTC: '#FF9230',
  ETH: '#627EEA',
  USDT: '#26A17B',
  USDC: '#2775CA',
  XRP: '#23292F',
  SOL: '#9945FF',
  BNB: '#F3BA2F',
  ADA: '#0033AD',
  AVAX: '#E84142',
  DOGE: '#C2A633',
  DOT: '#E6007A',
  LINK: '#2A5ADA',
  TRX: '#EF0027',
}

export function normalizeCryptoBaseTicker(raw: string): string {
  let u = raw.trim().toUpperCase()
  if (!u) return u
  for (const suffix of QUOTE_SUFFIXES) {
    if (u.length > suffix.length && u.endsWith(suffix)) {
      const base = u.slice(0, -suffix.length)
      if (base) {
        u = base
        break
      }
    }
  }
  return u
}

export function cryptoBrandColor(ticker: string): string {
  const base = normalizeCryptoBaseTicker(ticker)
  const key = TICKER_ALIASES[base] ?? base
  return CRYPTO_ASSET_BRAND[key] ?? 'rgba(29, 29, 31, 0.15)'
}

/** Chemin public Next (`/crypto_svgs/btc.svg`) ou null si absent du pack. */
export function bundledCryptoSvgPublicPath(rawTicker: string): string | null {
  let key = normalizeCryptoBaseTicker(rawTicker)
  if (!key) return null
  key = TICKER_ALIASES[key] ?? key
  if (!BUNDLED_EXPORT_TICKERS.has(key)) return null
  return `/crypto_svgs/${key.toLowerCase()}.svg`
}

/**
 * Résolution logo réseau — équivalent Flutter `TopCryptoAssetsModule._resolveLogoUrl`.
 */
export function resolveCryptoNetworkLogoUrl(
  ticker: string,
  apiLogoUrl?: string | null,
  logoBaseUrl = getMarketDataPublicBaseUrl(),
): string | null {
  const fromApi = resolveMarketDataLogoUrl(apiLogoUrl, logoBaseUrl)
  if (fromApi) return fromApi
  const slug = normalizeCryptoBaseTicker(ticker).toLowerCase()
  if (!slug) return null
  return resolveMarketDataLogoUrl(`/media/crypto_logos/${slug}.png`, logoBaseUrl)
}

/** Sources dans l’ordre d’affichage (SVG packagé → API → PNG fallback). */
export function resolveCryptoAvatarSources(
  ticker: string,
  apiLogoUrl?: string | null,
  logoBaseUrl = getMarketDataPublicBaseUrl(),
): string[] {
  const sources: string[] = []
  const svg = bundledCryptoSvgPublicPath(ticker)
  if (svg) sources.push(svg)
  const network = resolveCryptoNetworkLogoUrl(ticker, apiLogoUrl, logoBaseUrl)
  if (network && !sources.includes(network)) sources.push(network)
  return sources
}
