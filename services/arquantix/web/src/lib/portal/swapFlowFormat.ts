import { assetPrecisionDisplay } from '@/lib/portal/cryptoWalletFormat'
import { isPortalEuroFeaturesEnabled } from '@/lib/portal/portalEuroVisibility'
import {
  SWAP_V1_PILOT_CHAINS,
  SWAP_V1_SAME_CHAIN_ONLY,
  type SwapCatalogAsset,
} from '@/lib/portal/swapFlowTypes'
import type { PortalCryptoPosition } from '@/lib/portal/cryptoWalletTypes'
import { resolveSpendableSwapBalance } from '@/lib/portal/swapAmountValidation'

/** Décimales d'affichage swap — catalogue API si dispo, sinon précision produit par ticker. */
export function resolveSwapAssetDecimals(asset: string, catalog?: SwapCatalogAsset[]): number {
  const symbol = asset.trim().toUpperCase()
  const fromCatalog = catalog?.find((row) => row.symbol.toUpperCase() === symbol)?.decimals
  if (fromCatalog != null && fromCatalog > 0) return Math.min(fromCatalog, 18)
  return assetPrecisionDisplay(symbol)
}

/**
 * Montant crypto lisible (jamais en notation scientifique).
 * Pour les petits montants (< 1), conserve les zéros initiaux jusqu'à la précision de l'actif.
 */
export function formatSwapCryptoAmount(
  value: number | string,
  asset?: string,
  catalog?: SwapCatalogAsset[],
): string {
  const n = typeof value === 'string' ? Number(value.replace(',', '.')) : value
  if (!Number.isFinite(n) || n === 0) return '0'

  const maxDecimals = asset ? resolveSwapAssetDecimals(asset, catalog) : 8

  if (n >= 1) {
    return trimTrailingZeros(n.toFixed(Math.min(maxDecimals, 6)))
  }

  return trimTrailingZeros(n.toFixed(maxDecimals))
}

function trimTrailingZeros(raw: string): string {
  if (!raw.includes('.')) return raw
  return raw.replace(/0+$/, '').replace(/\.$/, '') || '0'
}

export function defaultChainForAsset(
  asset: string,
  chains: string[],
): string {
  if (chains.length === 0) return ''
  if (SWAP_V1_SAME_CHAIN_ONLY) {
    const pilot = SWAP_V1_PILOT_CHAINS.find((chain) => chains.includes(chain))
    if (pilot) return pilot
  }
  const sym = asset.toUpperCase()
  const preferred: Record<string, string> = {
    USDC: 'base',
    EURC: 'base',
    ETH: 'base',
    CBETH: 'base',
    CBBTC: 'base',
    LINK: 'base',
    AAVE: 'base',
    UNI: 'base',
  }
  const pick = preferred[sym]
  if (pick && chains.includes(pick)) return pick
  return chains[0]!
}

/** Chaîne source alignée sur la destination en mode same-chain. */
export function resolveSwapSourceChain(
  asset: string,
  chains: string[],
  destinationChain: string,
): string {
  if (SWAP_V1_SAME_CHAIN_ONLY && destinationChain && chains.includes(destinationChain)) {
    return destinationChain
  }
  return defaultChainForAsset(asset, chains)
}

export type SwapFromOption = {
  asset: string
  name: string
  chain: string
  balance: number
  logoUrl?: string | null
  position?: PortalCryptoPosition
}

export type SwapToOption = {
  asset: string
  name: string
  chain: string
}

export type SwapAssetChipMeta = {
  key: string
  name: string
  short: string
  unit: string
  desc: string
  glyph: string
  bg: string
  color: string
}

/** Visual chip metadata for swap asset pickers (invest-flow pattern). */
export function swapAssetChipMeta(symbol: string, displayName?: string): SwapAssetChipMeta {
  const sym = symbol.trim().toUpperCase()
  const short = sym
  const name = displayName?.trim() || sym

  const presets: Record<string, Omit<SwapAssetChipMeta, 'key' | 'name'>> = {
    USDC: {
      short: 'USDC',
      unit: 'Stablecoin · USD',
      desc: 'Circle USD stablecoin',
      glyph: '$',
      bg: '#2775CA',
      color: '#FFFFFF',
    },
    EURC: {
      short: 'EURC',
      unit: 'Stablecoin · EUR',
      desc: 'Circle euro stablecoin',
      glyph: '€',
      bg: 'var(--v-fg)',
      color: '#FFFFFF',
    },
    ETH: {
      short: 'ETH',
      unit: 'Native · Base',
      desc: 'Ether on Base',
      glyph: 'Ξ',
      bg: '#627EEA',
      color: '#FFFFFF',
    },
    CBBTC: {
      short: 'cbBTC',
      unit: 'Wrapped · BTC',
      desc: 'Coinbase wrapped Bitcoin',
      glyph: '₿',
      bg: '#F7931A',
      color: '#FFFFFF',
    },
    CBETH: {
      short: 'cbETH',
      unit: 'Wrapped · ETH',
      desc: 'Coinbase wrapped Ether',
      glyph: 'Ξ',
      bg: '#2E3192',
      color: '#FFFFFF',
    },
  }

  const preset = presets[sym]
  if (preset) {
    return { key: sym.toLowerCase(), name, ...preset }
  }

  return {
    key: sym.toLowerCase(),
    name,
    short: sym.length > 6 ? sym.slice(0, 6) : sym,
    unit: sym,
    desc: name,
    glyph: sym.charAt(0),
    bg: '#6e665c',
    color: '#FFFFFF',
  }
}

export function buildSwapFromOptions(
  catalog: SwapCatalogAsset[],
  positions: PortalCryptoPosition[],
  toAsset: string,
  toChain: string,
): SwapFromOption[] {
  const catalogBySymbol = new Map(catalog.map((a) => [a.symbol.toUpperCase(), a]))
  const out: SwapFromOption[] = []

  for (const pos of positions) {
    const sym = pos.asset.toUpperCase()
    const meta = catalogBySymbol.get(sym)
    if (!meta) continue
    const balance = resolveSpendableSwapBalance(pos)
    if (balance <= 0) continue
    const chain = resolveSwapSourceChain(sym, meta.chains, toChain)
    if (SWAP_V1_SAME_CHAIN_ONLY && chain !== toChain) continue
    if (sym === toAsset.toUpperCase() && chain === toChain) continue
    out.push({
      asset: sym,
      name: pos.name || sym,
      chain,
      balance,
      logoUrl: pos.logoUrl,
      position: pos,
    })
  }

  if (out.length === 0) {
    for (const meta of catalog) {
      const chain = resolveSwapSourceChain(meta.symbol, meta.chains, toChain)
      if (SWAP_V1_SAME_CHAIN_ONLY && chain !== toChain) continue
      if (meta.symbol === toAsset && chain === toChain) continue
      out.push({
        asset: meta.symbol,
        name: meta.display_name,
        chain,
        balance: 0,
      })
    }
  }

  return out
}

export function buildSwapToOptions(
  catalog: SwapCatalogAsset[],
  fromAsset: string,
  chain: string,
): SwapToOption[] {
  const from = fromAsset.trim().toUpperCase()
  return catalog
    .filter((row) => row.symbol.toUpperCase() !== from)
    .map((row) => ({
      asset: row.symbol,
      name: row.display_name,
      chain,
    }))
}

/** Stablecoin par défaut — achat, vente et swap générique. */
export const SWAP_DEFAULT_STABLE_ASSET = 'USDC'

/** Paire swap générique par défaut (from USDC). */
export const SWAP_DEFAULT_GENERIC_TARGET_ASSET = 'CBBTC'

export function pickDefaultSwapFromOption(
  catalog: SwapCatalogAsset[],
  positions: PortalCryptoPosition[],
  toAsset: string,
  toChain: string,
  preferredSymbol: string = SWAP_DEFAULT_STABLE_ASSET,
): SwapFromOption | null {
  const options = buildSwapFromOptions(catalog, positions, toAsset, toChain)
  const preferred = preferredSymbol.trim().toUpperCase()
  return (
    options.find((row) => row.asset.toUpperCase() === preferred) ??
    options.find((row) => isSwapV1Stable(row.asset)) ??
    options[0] ??
    null
  )
}

export function pickDefaultSwapToOption(
  catalog: SwapCatalogAsset[],
  fromAsset: string,
  chain: string,
  preferredSymbol: string = SWAP_DEFAULT_STABLE_ASSET,
): SwapToOption | null {
  const options = buildSwapToOptions(catalog, fromAsset, chain)
  const preferred = preferredSymbol.trim().toUpperCase()
  return (
    options.find((row) => row.asset.toUpperCase() === preferred) ??
    options.find((row) => isSwapV1Stable(row.asset)) ??
    options[0] ??
    null
  )
}

function isSwapV1Stable(symbol: string): boolean {
  const sym = symbol.toUpperCase()
  if (sym === 'USDC') return true
  return sym === 'EURC' && isPortalEuroFeaturesEnabled()
}
